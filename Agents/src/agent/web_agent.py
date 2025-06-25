from langchain_community.document_loaders import WebBaseLoader
import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from tqdm.notebook import tqdm
import platform
import toml
import streamlit as st
from openai import AzureOpenAI
import os


try:
    # Local development (Windows)
    if platform.system() == "Windows":
        secrets_path = os.path.join(
            os.path.dirname(__file__), "..", "..", ".streamlit", "secrets.toml"
        )
        with open(secrets_path, "r") as f:
            secrets = toml.load(f)
        gpt4o_mini_key = secrets["aoai"]["OPENAI_API_KEY_USEA"]
        gpt4o_mini_endpoint = secrets["aoai"]["OPENAI_AZURE_ENDPOINT_USEA"]
    # Deployment (Linux)
    else:
        gpt4o_mini_key = st.secrets["aoai"]["OPENAI_API_KEY_USEA"]
        gpt4o_mini_endpoint = st.secrets["aoai"]["OPENAI_AZURE_ENDPOINT_USEA"]

except Exception as e:
    print(f"Error loading OpenAI credentials: {e}")
    gpt4o_mini_key = None
    gpt4o_mini_endpoint = None

client = AzureOpenAI(
    api_key=gpt4o_mini_key,
    azure_endpoint=gpt4o_mini_endpoint,
    api_version="2024-08-01-preview",
)


class WebSearchAgent:
    """
    검색 쿼리에 대해 기사를 검색하고 필터링된 기사를 반환하는 에이전트
    """

    def __init__(self, search_query, client, model="gpt-4o"):
        self.search_query = search_query
        self.client = client
        self.model = model
        self.headers = {
            "User-Agent": os.getenv(
                "USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            )
        }

    def search_naver_news(self):
        """
        네이버 뉴스에서 검색 쿼리에 맞는 기사를 검색
        """
        # print("네이버 뉴스 검색 시작...")
        url = f"https://search.naver.com/search.naver?where=news&query={self.search_query}&sm=tab_pge&sort=0&photo=0&field=0&reporter_article=&pd=0&ds=&de=&docid=&nso=so:r,p:all,a:all&mynews=1&refresh_start=0&related=0"
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = []
        for item in soup.select("a.news_tit"):
            title = item.get("title")
            link = item.get("href")
            articles.append((title, link))

        # print(f"네이버 뉴스 검색 완료: {len(articles)}개의 기사 발견")
        return articles

    def get_news(self, link):
        """
        주어진 기사 링크에서 뉴스 원문 크롤링
        """
        try:
            # print(f"기사 크롤링 시작: {link}")
            web_loader = WebBaseLoader([link])
            data = web_loader.load()

            if not data:
                print(f"No content found for URL: {link}")
                return f"No content found for URL: {link}"

            news_dict = data[0].model_dump()
            content = news_dict.get("page_content", "")

            # print(f"기사 크롤링 완료: {link}")
            return content

        except requests.exceptions.RequestException as e:
            print(f"기사 크롤링 중 오류 발생: {e}")
            return None

    def filter_article(self, link):
        """
        단일 기사를 필터링하여 반환
        """
        content = self.get_news(link)
        if content:
            try:
                # print(f"기사 필터링 시작: {link}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"""
                        {content}에서 자사 컨시어지 {self.search_query} 서비스의 재이용에 도움이 되는 정보를 제공하세요.
                        - 우리 서비스 이용에 도움이 되는 실용 정보와 다시 신청할만한 꿀팁을 제공하세요.
                        - 정부 정책 안내, 제도 설명은 제외하세요. 
                        - 서비스 구매 관점의 정보만 요약 정리하세요.
                        - 핵심 문장은 한글로 강조해 제공하세요.
                        """,
                        },
                    ],
                    max_tokens=800,
                    temperature=0.5,
                )

                filtered_content = response.choices[0].message.content.strip()
                # print(f"기사 필터링 완료: {link}")
                return filtered_content

            except Exception as e:
                print(f"필터링 중 오류 발생: {e}")
                return None

    def run(self):
        """
        WebSearchAgent 실행 메인 함수
        """
        # print("[debug] 서비스 관련 웹 기사 검색 중... 사용자 초기 입력시 제공")
        articles = self.search_naver_news()
        if not articles:
            print("관련 기사를 찾을 수 없습니다.")
            return "관련 기사를 찾을 수 없습니다."

        # 첫 번째 기사만 처리
        first_article_link = articles[0][1]

        # print("검색된 기사 필터링 중...")
        filtered_article = self.filter_article(first_article_link)

        if filtered_article:
            # print("기사 필터링 완료")
            return filtered_article
        else:
            print("필터링된 기사가 없습니다.")
            return "필터링된 기사가 없습니다."


class HealthInfoAgent:
    """
    필터링된 기사에서 건강 키워드를 추출하고 관련 정보를 요약하는 에이전트
    """

    def __init__(self, client, model="gpt-4o"):
        self.client = client
        self.model = model

    def find_health_keyword(self, filtered_article):
        """
        필터링된 기사에서 건강 키워드를 추출
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "주어진 기사에서 건강 관련 키워드를 3개 추출하세요.",
                    },
                    {"role": "user", "content": filtered_article},
                ],
                max_tokens=100,
                temperature=0.3,
            )
            health_keywords = response.choices[0].message.content.strip()
            return health_keywords
        except Exception as e:
            return f"키워드 추출 중 오류 발생: {e}"

    def summarize_health_info(self, health_links, health_keywords, search_query):
        """
        건강 정보를 요약
        """
        summarized_health_info = []

        for link in tqdm(health_links, desc="Processing health articles"):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"{search_query} 서비스 이용률을 높일 수 있는 {health_keywords}와 관련된 건강 정보를 요약하세요.",
                        },
                        {"role": "user", "content": link},
                    ],
                    max_tokens=500,
                    temperature=0.7,
                )
                summarized_content = response.choices[0].message.content.strip()
                summarized_health_info.append(summarized_content)
            except Exception as e:
                print(f"요약 중 오류 발생: {e}")
                continue

        return summarized_health_info


# 테스트
# service_name = "강아지 돌봄"
# web_agent = WebSearchAgent(search_query=service_name, client=client)
# test = web_agent.run()
# print(test)
