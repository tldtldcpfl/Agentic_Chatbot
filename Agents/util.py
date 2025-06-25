from typing import Dict
import streamlit as st
from openai import OpenAIError, AzureOpenAI


#  로컬에서 실행한 경우 하드코딩된 테스트 쿠키 값을 반환
def get_local_cookies() -> Dict[str, str]:
    """Return test cookie values for local testing"""
    return {
        "ois_customer_access_token_dev": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJPSVMtQ1VTVE9NRVIiLCJzdWIiOiIxIiwiYXVkIjoiT0lTLUNVU1RPTUVSIiwidHlwZSI6IkFDQ0VTUyIsImlhdCI6MTc0MTMzNzkzOSwiZXhwIjoxNzQxMzM5NzM5LCJhZGRyZXNzU2VxIjoxfQ.70pGSs6o_7V0TbsmGC4NWqQG4cLGflfRXjiZOZFgGIA",
        "ois_customer_web_theme_dev": "cc-airm",
        # 로컬에서 streamlit 서버 실행 시 쿠키 업데이트 필요
        "ois_customer_refresh_token_dev": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJPSVMtQ1VTVE9NRVIiLCJzdWIiOiIxIiwiYXVkIjoiT0lTLUNVU1RPTUVSIiwidHlwZSI6IlJFRlJFU0giLCJpYXQiOjE3NDUyODQ0NDcsImV4cCI6MTc0NTQ1NzI0NywiYWRkcmVzc1NlcSI6MX0.p7M5uosazzCBx6OAIu-l4_6DguRtqdYlyX6ZdYU_caw",
    }


def get_cookie_from_context() -> Dict[str, str]:
    """
    Get cookie values based on environment (local/dev/prod)
    Returns:
        Dict[str, str]: Cookie dictionary with environment-specific suffixes
    """
    try:
        # secrets.toml 환경 변수 확인
        # toml 파일 gitlab 업로드X, gitlab ci/cd variables에서 환경변수 설정
        env = st.secrets["environment"]["ENVIRONMENT"]  # local
        print("[debug] 실행 환경 확인:", env)

        # env가 local or dev일 때 _dev가 붙은 토큰 사용
        suffix = "_dev" if env in ["local", "dev"] else ""  # prod는 suffix 없음
        print(f"[DEBUG] Current environment: {env}, using suffix: {suffix}")

        # cookies = getattr(st.context, "cookies", "st.context.cookies로 쿠키 받기 실패")
        # print("[debug] cookies:", cookies)

        # environment check
        # 실행 환경이 dev 서버이면 st.context.cookies로 쿠키 받기
        if env == "dev":
            # Try to get cookies from st.context
            cookies = getattr(st.context, "cookies", "dev 서버 쿠키 받기 실패")

            # st.context.cookies로 쿠키를 못받은 경우
            if not cookies:
                error_msg = "[WARNING] `st.context.cookies`로 쿠키 로드 실패. 테스트 쿠키를 반환합니다."
                print(error_msg)
                # dev 서버에 쿠키없을 경우 로컬에 정의한 쿠키 반환
                return get_local_cookies()

            token_key = f"ois_customer_access_token{suffix}"

            if cookies.get(token_key):
                # 로그인 인증에 필요한 키값만 dict에 담기
                cookie_dict = {
                    token_key: cookies.get(token_key),
                    f"ois_customer_web_theme{suffix}": cookies.get(
                        f"ois_customer_web_theme{suffix}"
                    ),
                    f"ois_customer_refresh_token{suffix}": cookies.get(
                        f"ois_customer_refresh_token{suffix}"
                    ),
                }
                print(f"[INFO] Using {env} server cookies")
                return cookie_dict

        # 실행 환경이 로컬이면 하드코딩된 테스트 쿠키 반환
        return get_local_cookies()

    except Exception as e:
        print(f"[ERROR] Cookie retrieval failed: {e}")
        return get_local_cookies()


# cookie = get_cookie_from_context()
# print(cookie)


def handle_cookie_refresh() -> Dict[str, str]:
    """
    Handle cookie refresh and return environment info and cookies
    Returns:
        Dict[str, str]: Environment and cookie information
    """
    print(
        f"[DEBUG] cookies_refreshed before check: {st.session_state.get('cookies_refreshed')}"
    )

    # 초기 state
    if "cookies_refreshed" not in st.session_state:  # uses Streamlit features
        st.session_state.cookies_refreshed = False

    # Get environment
    env = st.secrets["environment"]["ENVIRONMENT"]

    # Handle cookie refresh
    if not st.session_state.cookies_refreshed:

        # 무한 rerun 방지 위해 True로 설정
        # 브라우저를 완전히 닫으면 session state가 cleared 됨
        # 단순 새로고침(F5)으로는 session state가 유지됨 (웹소켓 연결이 유지)
        st.session_state.cookies_refreshed = True  # Must set True before rerun
        print("[DEBUG] Set cookies_refreshed to True")
        print("[DEBUG] Triggering rerun for cookie refresh")

        st.rerun()

    print("[DEBUG] After rerun, getting fresh cookies")
    # Get cookies
    cookies = get_cookie_from_context()
    return {"environment": env, "cookies": cookies}


# OpenAI 컨텐츠 정책 준수를 위한 우회 질문 생성 함수
def rephrase_question(question: str, client: AzureOpenAI) -> str:
    """
    GPT API를 활용하여 차단된 질문을 보다 중립적이고 안전한 방식으로 변환
    Args:
        question: 원래 질문
    Returns:
        str: 변환된 질문 또는 원래 질문
    """
    print(f"[DEBUG] Attempting to rephrase: {question}")

    rephrase_prompt = f"""
    다음 질문은 AI의 정책상 차단될 가능성이 있습니다. 
    하지만 질문의 의미를 유지한 채, 보다 일반적이고 안전한 표현으로 다시 작성해 주세요.
    
    원래 질문: "{question}"
    변환된 질문:
    """

    try:
        response = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {
                    "role": "system",
                    "content": "질문을 보다 안전한 표현으로 변환해 주세요.",
                }
            ]
            + [{"role": "user", "content": rephrase_prompt}],
            stream=False,
            temperature=0.3,
            top_p=0.8,
            max_tokens=50,
        )

        if response.choices:
            rephrased = response.choices[0].message.content.strip()
            print(f"[DEBUG] Successfully rephrased to: {rephrased}")
            return rephrased

        print("[DEBUG] No choices in response, returning original")
        return question

    except OpenAIError as e:
        print(f"[ERROR] OpenAI error during rephrasing: {str(e)}")
        return question


# [test] rephrase_question 함수 테스트
# test_questions = [
#     "고양이 물로 씻겨도돼?",
#     "강아지 목욕 어떻게 시키나요?",
#     "강아지 털에 흙탕물이 왕창 묻었는대 박박 때 벗기고싶어요",
# ]
# for question in test_questions:
#     # print(f"\nOriginal: {question}")
#     result = rephrase_question(question)
#     st.write(f"Rephrased: {result}")


# ---- ssh 터널링 (로컬 실행 시 수동 입력, dev x) ----
# .ssh 디렉토리
# ssh -i id_ed25519 \
#     -L 5433:dev-ai-db.cluster-cd0wwldwqjdn.ap-northeast-2.rds.amazonaws.com:5432 \
#     ec2-user@43.202.26.252

# 사용중인 pid 확인
# netstat -aon | findstr :5433
# cmd 터미널 pid 종료
# taskkill /PID 28708 /F
