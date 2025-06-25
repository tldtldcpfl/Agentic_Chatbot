from ftplib import error_temp
import streamlit as st
import json
from openai import AzureOpenAI
import re
import time
from datetime import datetime
from src.tools import (
    search_news,
    process_news_response,
    send_checkout_request,
    recommend_tour_plan,
    request_order_history,
    request_available_service,
)  # Replace with the specific functions you need
from src.tools import service_list

from src.get_api_info import (
    # 사용자 정보 로드
    name,
    address,
)

from create_tools import create_tools_list
from openai import OpenAIError
from util import handle_cookie_refresh
from api_setting.ois_api_info import get_service_data, service_list_url
from src.db.db_util import ChatSessionManager


auth_info = handle_cookie_refresh()
env = auth_info["environment"]
cookie = auth_info["cookies"]

# Debug info (can be removed in production)
with st.expander("🔧 Debug Info", expanded=False):  # false:페이지 로드 시 섹션 접기
    st.write("Environment:", env)
    st.write("Cookies:", cookie)


# openai api key 및 endpoint (gpt-4o-mini)
gpt4o_mini_key = st.secrets["aoai"]["OPENAI_API_KEY_USEA"]
gpt4o_mini_endpoint = st.secrets["aoai"]["OPENAI_AZURE_ENDPOINT_USEA"]


# Initialize chat manager after tunnel is established
chat_manager = ChatSessionManager()


@st.cache_data(show_spinner=False)
def get_filtered_article(service_name: str) -> str:
    # 이용 서비스 관련 최신 웹정보 제공
    from src.agent.web_agent import WebSearchAgent

    web_agent = WebSearchAgent(search_query=service_name, client=client)
    return web_agent.run()


# --- chatbot dialog session lifecycle ---


# TODO: 이전 대화의 주요 내용은 user_id별 db에서 로드
def initialize_tools():
    """
    Initialize tools list:
    - Tools are initialized only once per session
    - Same tools list maintained until browser refresh/close
    - So, Cookie used at initialization remains throughout session
    """
    try:
        # Get tools list with current cookie
        if "tools" not in st.session_state:
            # st.session_state로 tools 캐싱
            # tools lives until browser tab is closed
            # = storing tools list that needs to stay consistent during session
            # = New browser session → st.session_state is empty
            st.session_state.tools = create_tools_list(cookie)
            print("[DEBUG] Tools initialized with refreshed cookie")
        return st.session_state.tools

    except Exception as e:
        print(f"[ERROR] Failed to initialize tools due to 쿠키 만료: {e}")
        raise


# tools 초기화
tools = initialize_tools()


if not tools:
    st.error("Failed to initialize tools")
    st.stop()


# Function Call 처리 및 결과 생성
def handle_function_call(
    function_name: str,
    arguments: dict,
) -> dict:

    # Function Call 처리 및 결과 생성
    if function_name == "search_news":
        response = search_news(arguments["keyword"])
        try:
            response = process_news_response(response)[0]

        except Exception:
            response = "뉴스를 찾을 수 없습니다."

    # replace the existing order form code with the redirect logic
    elif function_name.startswith("request_service_"):
        try:
            print(f"[DEBUG] 👉🏻 Entering service request handler for {function_name}")
            from src.api_setting.ois_api_info import get_service_url

            # Get service URL and info
            service_info = get_service_url(function_name, cookie)
            print("[DEBUG] 👉🏻 서비스 정보:", service_info["service_type"])

            response = {
                "message": f"👉🏻 {service_info['service_type']} 서비스 신청 페이지로 이동하시겠습니까?",
                "url": service_info["url"],
                "service_type": service_info["service_type"],
            }

            return {
                "function_name": function_name,
                "args": arguments,
                "status": "success" if "error" not in service_info else "error",
                "response": response,
            }

        except Exception as e:
            print(f"[ERROR] Service redirect failed: {str(e)}")
            return {
                "function_name": function_name,
                "args": arguments,
                "status": "error",
                "response": f"서비스 페이지 연결에 실패했습니다: {str(e)}",
            }

    # 관광지 추천
    elif function_name == "recommend_tour_plan":
        # response = recommend_tour_plan(arguments["place_list"])

        with st.status("🚩관광지 추천 중...") as status:
            status.write("요청하신 지역 인근 관광지를 찾고있습니다...")

            map_obj, text = recommend_tour_plan(arguments["place_list"])

            # Save map to temporary file
            import tempfile

            # Display tour route map
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as m:
                map_obj.save(m.name)
                st.components.v1.html(
                    open(m.name, "r", encoding="utf-8").read(),
                    height=400,
                    scrolling=True,
                )

            status.update(label="✅ 관광지 추천 완료!", state="complete")

            # Return text response for chat history
            response = text

    # 주문 내역 조회 함수
    elif function_name == "request_order_history":
        # arguments[var]: 함수 입력 변수
        print(f"[debug] 사용자 서비스 주문 내역 조회: {function_name} 함수 호출")
        response = request_order_history()

    # 신청가능 서비스 안내
    elif function_name == "request_available_service":
        print("[debug] 사용자 요청에 의한 request_available_service 함수 호출")
        response = request_available_service(name, address, service_list)

    else:
        response = "[ERROR] 사용자 요청 함수 호출 실패"

    return {
        "function name": function_name,  # 호출 함수명 DB 저장
        "args": arguments,
        "status": "성공",
        "response": response,
    }


def extract_json_objects(texts: str) -> list:
    pattern = r"\{.*?\}"
    json_strings = re.findall(pattern, texts)
    json_objects = [json.loads(json_string) for json_string in json_strings]
    return json_objects


def stream_data(words):
    for word in words:
        yield word
        time.sleep(0.02)


def click_toggle():
    st.session_state.toggle = not st.session_state.toggle


# ------------------ Streamlit App 실행 ------------------------

# st.title("Concierge Connect Chatbot")
# st.subheader("🤵🏻 컨시어지 AI 챗봇")  # 챗봇 타이틀 제거
# st.info("모두를 위한 AI 리빙 솔루션, 커넥트파이클라우드의 챗봇입니다.🤗")

if "button" not in st.session_state:
    st.session_state.toggle = False


toggle = st.checkbox("Enable Web Search", on_change=click_toggle)

if toggle:
    # The message and nested widget wi   ll remain on the page
    with st.chat_message(
        "assistant",
        avatar="static/bell_boy.png",
    ):
        st.write("Web Search Agent is on!")

# gpt api client 정의
if "openai_client" not in st.session_state:
    st.session_state["openai_client"] = AzureOpenAI(
        api_key=gpt4o_mini_key,
        azure_endpoint=gpt4o_mini_endpoint,
        api_version="2024-08-01-preview",
    )

# openai client
client = st.session_state["openai_client"]


# set default model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"

# 채팅 메시지 상태 초기화
# set empty list for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# (Important) In this loop, we will display the chat messages continuously.
for message in st.session_state.messages:
    with st.chat_message(
        message["role"],
        avatar=(
            "static/user.png" if message["role"] == "user" else "static/bell_boy.png"
        ),
    ):
        st.markdown(message["content"])


# 유저 초기 진입
if "first_entry" not in st.session_state:
    st.session_state.first_entry = True

# 과거 구매 서비스 관련 정보 제공
if "past_service_info" not in st.session_state:
    st.session_state.past_service_info = False


# -------- Here, Streamlit Chatbot Main Loop ------------


# user_id = name
service_data = get_service_data(service_list_url, cookie)

# 컨시어지 서비스 리스트
valid_services = list(service_data.keys())
# print("[DEBUG] 컨시어지 서비스명 추출:", valid_services)

if st.session_state.first_entry and not st.session_state.past_service_info:
    from src.db.db_util import get_latest_function_name

    # DB에서 user_id별 최근 호출 함수명 조회
    latest_service_list = get_latest_function_name(name)
    if latest_service_list is None:
        raise ValueError("로컬에서 DB 접속 시 SSH 터널링 필요")

    print("[DEBUG] 최근 호출 함수명 리스트:", latest_service_list)
    # latest_service = latest_service_list[-1]

    # Find most recent valid service (컨시어지 서비스)
    latest_service = None
    for service in reversed(latest_service_list):
        if service in valid_services:
            latest_service = service
            # print(f"[DEBUG] Found latest valid service: {latest_service}")
            break

    if latest_service and latest_service in valid_services:

        with st.expander(
            f"🔍 {name} 고객님, 이전에 이용하신 '{latest_service}' 서비스 관련 유용한 정보를 확인해보세요!",
            expanded=False,
        ):

            with st.spinner("서비스 관련 유용한 정보를 검색중입니다..."):
                filtered_article = get_filtered_article(latest_service)
                if filtered_article:

                    st.write(
                        f"이용하신 {latest_service} 서비스 관련 정보입니다:\n"
                        f"{filtered_article}"
                    )

                else:
                    st.write(
                        f"죄송합니다. {latest_service} 관련 정보를 찾을 수 없습니다."
                    )

            st.session_state.past_service_info = True


# Initialize button state
if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False
if "button_prompt" not in st.session_state:
    st.session_state.button_prompt = ""


# ----------- 사용자 입력 처리 전 FAQ 버튼 ---------------


# FAQ 키워드 버튼
st.markdown("##### 💬 자주하는 질문")


# 버튼 정보 리스트 (버튼 이름, 아이콘, 프롬프트)
buttons_str = [
    ("신청 가능 서비스", None, "신청 가능한 컨시어지 서비스 종류를 안내해주세요"),
    ("가사도우미 신청", None, "가사도우미 서비스를 신청하고 싶어요"),
    ("세탁 & 수선 서비스", None, "세탁 서비스를 신청하고 싶습니다"),
    ("주문 이력 조회", "🛒", "과거 주문 이력을 알려주세요"),
]

# 4개의 컬럼 생성
cols = st.columns(len(buttons_str))

# 버튼 생성 및 이벤트 처리
for col, (label, icon, button_prompt) in zip(cols, buttons_str):
    with col:
        if st.button(label, icon=icon, use_container_width=True):
            st.session_state.button_clicked = True
            st.session_state.button_prompt = button_prompt
            # session_state.messages에 기존 prompt처럼 button_prompt 추가
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": button_prompt,
                }
            )
            st.rerun()


# ----------- 사용자 입력 처리 ---------------
if prompt := st.chat_input("무엇을 도와드릴까요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="static/user.png"):
        st.markdown(prompt)


# 챗 버튼 처리
if st.session_state.messages and (prompt or st.session_state.button_clicked):
    prompt = st.session_state.button_prompt

    # ----------- tools 함수 호출 --------------
    # Stream the assistant or function response
    with st.chat_message(
        "assistant",
        avatar="static/bell_boy.png",
    ):
        # OpenAI 유해 contents 에러 예외 처리
        try:
            # chat stream 생성
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {
                        "role": "system",
                        "content": f"Current time: {datetime.now()}",
                    }
                ]
                + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
                temperature=0.3,
                top_p=0.8,
                tools=tools,
                tool_choice="auto",
            )

            # -- Handle function calls --
            # Once the stream is consumed, it will be gone,
            # so we need to recreate it.
            chunk_list_temp = []
            # 함수 호출 목록
            function_list = []

            args = ""

            # -- Stream processing block --
            # for idx, chunk in enumerate(stream):
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    print(f"[DEBUG] Delta content: {delta}")

                    # tool_calls: 함수 호출 정보
                    if delta.tool_calls is not None:

                        function_call = delta.tool_calls[0]

                        # if function_call.function.name:
                        if function_call.function.name:
                            function_name = function_call.function.name
                            print("[debug] ✅ 호출 함수명:", function_name)

                            if function_name.startswith("request_service_"):
                                print("[DEBUG] 🎯 Detected service request function")
                                # No need to collect arguments for service requests
                                # -> 유저 입력 없이 바로 서비스 신청 페이지로 redirect
                                args = "{}"
                                print("[DEBUG] Setting empty args for service request")

                            else:
                                # For other functions (news, history etc), collect arguments
                                args += delta.tool_calls[0].function.arguments
                                print(f"[DEBUG] Arguments: {args}")  # Debug log

                            function_list.append(function_name)
                            print(f"[DEBUG] 📝 Function list updated: {function_list}")

                    else:
                        if delta.content:
                            chunk_list_temp.append(delta.content)

            # After stream processing
            if len(chunk_list_temp) != 0:
                response = "".join(chunk_list_temp)

                st.write(response)
                # 맥락을 유지하기 위해 assistant 메시지 추가
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

                current_function = function_list[-1] if function_list else None

                # function_name -> request_service_2
                print(f"[INFO] Chat message saved: {name}")
                print(f"[DEBUG] Current function: {current_function}")

            # elif args != "":
            elif args != "" or function_list[-1] in [
                "request_order_history",
                "request_available_service",
            ]:
                if args != "":
                    # JSON 파싱 처리
                    args_list = extract_json_objects(args)
                    if args_list:  # JSON 파싱 결과가 있을 때만
                        args = args_list[-1]

                else:
                    args = "{}"  # 없으면 빈 json 처리

                # ...function call handling...

                # 함수 호출
                function_result = handle_function_call(function_list[-1], args)
                print("[DEBUG] ✨ Function result:", function_result)

                if function_result["response"]:

                    # -- args 없이 바로 실행되는 함수 --

                    # 주문 내역 조회
                    if function_list[-1] == "request_order_history":
                        chunk_list_temp = []
                        args = ""
                        print("[DEBUG] 주문 내역 조회: ", function_result)

                        # st.write(function_result["response"])

                        result = function_result["response"]
                        st.markdown(result["content"], unsafe_allow_html=True)

                        if (
                            result["services"]["recent"]["url"]
                            or result["services"]["frequent"]["url"]
                        ):

                            # 서비스 재신청 버튼 - 공통 스타일 정의
                            from style_config import (
                                reorder_button_style,
                                quick_reorder_title_style,
                            )

                            st.markdown(
                                quick_reorder_title_style, unsafe_allow_html=True
                            )

                            col1, col2 = st.columns(2)

                            # 최근 이용 서비스 버튼
                            if result["services"]["recent"]["url"]:
                                # 최근 이용 서비스 버튼
                                with col1:
                                    st.markdown(
                                        f"""
                                        <a href="{result['services']['recent']['url']}" target="_self" style="text-decoration: none;">
                                            <div style="{reorder_button_style}">
                                                {result['services']['recent']['name']} 서비스 신청하기
                                            </div>
                                        </a>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                            # 고빈도 이용 서비스 버튼
                            if result["services"]["frequent"]["url"]:
                                with col2:
                                    st.markdown(
                                        f"""
                                        <a href="{result['services']['frequent']['url']}" target="_self" style="text-decoration: none;">
                                            <div style="{reorder_button_style}">
                                                {result['services']['frequent']['name']} 서비스 신청하기
                                            </div>
                                        </a>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                    elif function_list[-1] == "request_available_service":
                        result = function_result["response"]

                        # 서비스 소개 메시지
                        st.markdown(f"{result['message']}")

                        col1, col2 = st.columns(2)

                        # Display services in a grid layout
                        for idx, service in enumerate(result["services"]):

                            # Alternate between columns
                            with col1 if idx % 2 == 0 else col2:

                                st.markdown(
                                    f"""
                                    <div style='display: inline-flex; align-items: center; gap: 6px;'>
                                        <img src='{service["icon_url"]}' height='20px'>
                                        <span style='font-weight: bold;'>{service['name']}</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                                # Expander 내부 구성
                                with st.expander(
                                    label=f"{service['name']} 서비스 안내 보기",
                                    expanded=False,
                                ):

                                    st.markdown(f"""👉🏻 {service['description']}""")

                                    from style_config import (
                                        available_service_button_style,
                                    )

                                    # 서비스 신청 버튼
                                    st.markdown(
                                        f"""
                                        <a href="{service['action']['url']}" target="_self" style="text-decoration: none;">
                                            <div style="{available_service_button_style}">
                                                {service['name']} 서비스 신청하기 →
                                            </div>
                                        </a>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                    # 관광지 추천
                    elif function_list[-1] == "recommend_tour_plan":
                        chunk_list_temp = []
                        args = ""
                        st.write(function_result["response"])

                    # 뉴스 검색
                    elif function_list[-1] == "search_news":
                        chunk_list_temp = []
                        args = ""
                        st.markdown(
                            f'[{function_result["response"]["title"]}]'
                            f'({function_result["response"]["link"]})'
                        )
                        st.image(
                            function_result["response"]["thumbnail_url"],
                            width=180,
                        )

                    # 컨시어지 주문서 작성 페이지로 redirect
                    elif function_list[-1].startswith("request_service_"):
                        if isinstance(function_result["response"], dict):
                            print("[DEBUG] Function result:", function_result)

                            # CSS 스타일 변경
                            # (스타일 1)
                            st.markdown(
                                f"""
                                <a href="{function_result['response']['url']}" target="_self" style="text-decoration: none;">
                                    <div style="
                                        display: inline-block;
                                        padding: 8px 16px;
                                        background-color: #E8F5E9;
                                        color: #2E7D32;
                                        border-radius: 20px;
                                        font-size: 14px;
                                        font-weight: 600;
                                        cursor: pointer;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                        text-align: center;
                                        transition: all 0.2s;
                                    ">
                                        {function_result['response']['service_type']} 서비스 신청하기 →
                                    </div>
                                </a>
                                """,
                                # streamlit에서 html 렌더링 허용
                                unsafe_allow_html=True,
                            )

                            # Add to chat history
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": f"💡 {function_result['response']['service_type']} 서비스를 신청하실 수 있습니다.",
                                }
                            )

                            # Save chat message
                            chat_manager.save_chat_message(
                                user_id=name,
                                user_message=None,
                                assistant_message=None,
                                function_name=function_list[-1],
                                cookie=cookie,
                                all_messages=st.session_state.messages,
                            )

                            chunk_list_temp = []
                            args = ""

                        else:
                            st.error(function_result["response"])

                    # 일반 응답 처리
                    else:
                        st.write(function_result)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": f"{function_result['response']}",
                            }
                        )

                    chunk_list_temp = []
                    args = ""

                    # Save chat message once for all function types
                    # at the end of all function handling
                    chat_manager.save_chat_message(
                        user_id=name,
                        user_message=None,
                        assistant_message=None,
                        function_name=function_list[-1],
                        cookie=cookie,
                        all_messages=st.session_state.messages,
                    )

        # OpenAI Contents 에러 처리
        except OpenAIError as e:
            # 마지막 사용자 입력
            last_prompt = st.session_state.messages[-1]["content"]

            # Only try rephrasing for OpenAI content policy violations
            # if "content_policy_violation" in error_type:
            try:
                from util import rephrase_question

                # 질문 변환
                with st.status(
                    "컨텐츠 정책에 따라 응답을 생성하고 있습니다..."
                ) as status:
                    status.write("질문을 다시 작성하고 있습니다...")
                    modified = rephrase_question(last_prompt, client)
                    if modified != last_prompt:

                        st.session_state.messages[-1]["content"] = modified
                        # Restart chat flow with rephrased question
                        st.rerun()

            # 버튼 입력 표시
            except Exception as rephrase_error:
                print(f"[DEBUG] Rephrasing error: {str(rephrase_error)}")
                error_message = "죄송합니다. 해당 요청에 대해서는 저희 챗봇에서 응답드릴 수 없습니다."
                st.error(error_message)

                # ... show alternative options ...
                st.markdown(
                    """
                ##### 다음 기능들을 이용해보세요


                1️⃣ **컨시어지 서비스 신청**
                - 컨시어지 서비스를 안내해드려요!
                """
                )

                # Add available services button
                # UI 컴포넌트(st.markdown, st.button 등)
                if st.button("🔍 신청 가능 서비스", key="available_services"):
                    st.session_state.button_clicked = True
                    st.session_state.button_prompt = (
                        "신청 가능한 서비스 종류를 알려주세요"
                    )
                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "content": st.session_state.button_prompt,
                        }
                    )
                    st.rerun()

                # Add order history section with button
                st.markdown(
                    """
                    2️⃣ **주문 정보 조회**
                    """
                )
                if st.button("📋 주문 내역 확인", key="check_orders"):
                    st.session_state.button_clicked = True
                    st.session_state.button_prompt = "과거 주문 이력을 알려주세요"
                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "content": st.session_state.button_prompt,
                        }
                    )
                    st.rerun()

                # Add the help section
                st.markdown(
                    """
                    3️⃣ **도움말**
                    - FAQ 버튼으로 자주 묻는 질문 확인
                    """
                )

                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )

        # OpenAI 컨텐츠 필터링 에러가 아닌 경우
        # else:
        #     st.error("응답 생성 에러 발생")
