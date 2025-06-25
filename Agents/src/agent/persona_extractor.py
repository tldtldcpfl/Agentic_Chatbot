import os
from pathlib import Path
import toml
import streamlit as st
from openai import AzureOpenAI

os.environ["User_Persona"] = "user_attribute_extractor"

# Secrets 파일 로드
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRETS_PATH = os.path.join(ROOT_DIR, ".streamlit", "secrets.toml")
secrets = toml.load(SECRETS_PATH)

gpt4o_mini_key = st.secrets["aoai"]["OPENAI_API_KEY_USEA"]
gpt4o_mini_endpoint = st.secrets["aoai"]["OPENAI_AZURE_ENDPOINT_USEA"]

# AzureOpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=gpt4o_mini_key,
    azure_endpoint=gpt4o_mini_endpoint,
    api_version="2024-08-01-preview",
)
print(client)

system_role = "당신은 유저 응답으로부터 유저의 속성을 한국어로 추출하는 역할을 수행합니다.\
    유저 메시지에서 유저 속성을 추출하세요. 제품 및 서비스에 대한 선호도를 추출하세요. 소비 성향에 대한 특징을 추출하세요.\
    유저 속성 중 성별, 연령, 직업은 제외하세요.\
    유저 속성을 구조화된 포맷으로 추출하세요.\
    유저 속성: -제품 선호도: , -소비 성향: "


def persona_extractor(user_msg_list):
    """
    A Collaborative multi-agent
    framework that leverages LLM-based agents with
    diverse functionalities to effectively navigate
    customer preferences in a multi-turn conversational
    system
    """
    # user_msg_list를 하나의 문자열로 결합하여 하나의 user 메시지로 처리
    user_msg_content = " ".join(user_msg_list)

    messages = [
        {
            "role": "system",
            "content": system_role,
        },
        {
            "role": "user",
            "content": user_msg_content,
        },
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=800,
        temperature=0.5,
    )

    user_persona = response.choices[0].message.content.strip()
    # print(user_persona)
    return user_persona


# 다중 유저 메시지 리스트 from chatbot.db
user_msg_list = [
    "날씨가 요즘 너무 추워서 따뜻한 음식이 땡겨요. 국물 요리 중에 반찬 서비스에서 뭐가 많이 나가나요",
    "요즘 다이어트중인대 단백질로만 구성된 반찬 식품도 판매하나요?",
    "저는 주로 온라인 쇼핑을 통해 식품을 구매합니다.",
    "가격보다는 품질을 더 중요하게 생각합니다.",
]


persona_result = persona_extractor(user_msg_list)
print(persona_result)
