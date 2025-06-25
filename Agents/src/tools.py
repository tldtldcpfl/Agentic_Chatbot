import requests
import streamlit as st
from geopy.geocoders import Nominatim
import folium
import xyzservices
import toml
import platform
import os
import json
from collections import Counter
from datetime import datetime
import sys
from pathlib import Path

# Dir config
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
sys.path.append(ROOT_DIR)


from get_api_info import name
from util import handle_cookie_refresh

auth_info = handle_cookie_refresh()
env = auth_info["environment"]
cookie = auth_info["cookies"]
# print("[debug] util-cookie 확인\n", cookie)


from api_setting.ois_api_info import (
    # service_url_map_dict,
    checkout_url,
    order_history_url,
    order_confirm_url,
    service_list_url,
)


def load_mapbox_token():
    """Mapbox Access Token 로드"""
    try:
        if platform.system() == "Windows":  # 로컬 개발 환경 (Windows)
            secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
            with secrets_path.open("r") as f:
                secrets = toml.load(f)
            return secrets["mapbox"]["token"]

        # 배포 환경 (Linux 등)
        return st.secrets["mapbox"]["token"]

    except (FileNotFoundError, KeyError) as e:
        print(f"⚠️ Mapbox Token 로드 실패: {e}")
        return None


# set tile layers
map_name = "Mapbox.Streets"
# access_token = st.secrets["mapbox"]["token"]
access_token = load_mapbox_token()
# print(access_token == access_token_test)

tile_layer = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/{z}/{x}/{y}?access_token="
attribution = '&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> \
&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
tiles = xyzservices.TileProvider(
    url=tile_layer + access_token,
    name=map_name,
    attribution=attribution,
)


# set gcp credentials for search_news 함수
gcp_search_key = st.secrets["gcp"]["search_key"]
gcp_engine_id = st.secrets["gcp"]["search_engine_id"]
gcp_url = "https://www.googleapis.com/customsearch/v1/"


from api_setting.ois_api_info import (
    service_list_url,
    checkout_url,
    order_confirm_url,
    get_service_data,
)
from typing import Dict, Any


# common  pattern function for service request (서비스 신청)
def create_service_request_function(service_name: str):
    """기존의 하드코딩된 request_housekeeper_service 등등 함수 대체"""
    """Create a service request function for given service name"""

    def request_service(field_list: list[str], **field_values: dict) -> dict:
        # print(f"[DEBUG] {service_name} 서비스 주문서 작성")
        # Use Korean service name from API directly (ex. request_세탁_service)
        return get_checkout_payload(service_name, field_list, **field_values)

    return request_service


# Get available services from OIS API
service_data = get_service_data(service_list_url, cookie)
# print(service_data)


# 서비스 신청 함수 동적 생성
# Create functions with index-based names instead of 한글 서비스명
# using indexed function (ex. request_service_1)
for idx, (service_name_ko, service_info) in enumerate(service_data.items(), 1):
    print(f"request_service_{idx}", "-> 한글함수명: ", service_name_ko)
    # padded = str(idx).zfill(2)
    function_name = f"request_service_{idx}"  # zfill추가
    globals()[function_name] = create_service_request_function(service_name_ko)
    print(
        f"[DEBUG] Created function: {function_name} for {service_name_ko}",
        type(function_name),
    )


# 주문서 작성 공통 함수
def get_checkout_payload(
    service_type: str, field_list: list[str], **field_values: dict
) -> dict:
    """Create checkout payload without depending on service_data"""
    try:
        # 기존 service_url_map_dict 인자 대체
        # checkout_payload를 만드는대 필요한 인자를 service_list_url에서 받아옴
        # Get service data directly (service_data(ko): 소파클리닝, 에어컨 클리닝)
        service_data = get_service_data(service_list_url, cookie)

        if service_type not in service_data:
            raise ValueError(f"서비스 타입 식별 불가: {service_type}")

        # Create condition from field names
        condition = {field: field_values.get(field) for field in field_list}

        # Create payload
        checkout_payload = {
            "itemSeq": service_data[service_type]["seq"],
            "condition": condition,
        }
        return checkout_payload

    except Exception as e:
        # print(f"[ERROR] Failed to create payload: {e}")
        raise f"[ERROR] Failed to create payload: {e}"


# 주문 확정 post 요청
def send_checkout_request(checkout_payload: dict) -> str:
    """
    Sends checkout payload to checkout URL and returns checkoutId
    """
    print("[debug] checkoutId 인자 받기")

    try:
        # Step 1: Step 1: checkout_url 서버에 checkout_payload를 보내고 checkoutId를 받음
        response = requests.post(
            url=checkout_url, json=checkout_payload, cookies=cookie
        )
        data = json.loads(response.text)

        if "result" not in data:
            print("Missing 'result' key in response: 빈 리스트")
            raise KeyError(
                "서비스 신청에 필요한 항목 중 누락된 항목이 없는지 확인 후 재입력해주세요."
            )

        # checkoutId 인자 받기
        checkout_id = data["result"]["checkoutId"]
        # print("[debug] checkoutId:", checkout_id)

        # Step 2: Send order request (주문확정)
        # order_payload에 checkout_id 담기
        # in: checkout_id를 서버, out: 서버가 뱉은 response를 받음
        order_payload = {"checkoutId": checkout_id}
        order_response = requests.post(
            url=order_confirm_url, json=order_payload, cookies=cookie
        )
        order_response.raise_for_status()
        order_confirmed = order_response.json()

        # 주문 확정 성공일 경우 success_msg 리턴 (주문 내역 출력)
        if order_confirmed["code"] == 200:
            condition_str = "\n".join(
                f"{k}: {v}" for k, v in checkout_payload["condition"].items()
            )
            success_msg = (
                f"✅ 서비스 견적 신청이 완료됐습니다.\n" f"- 주문 내역: {condition_str}"
            )
            return success_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"[error] 서비스 신청 확정 실패: {e}"
        print(error_msg)
        return {"error": error_msg}


# [test] 133: 세탁서비스 주문 확정 테스트
# test_payload = {
#     "itemSeq": 133,
#     "condition": {
#         "수거요청 일자": "2025-03-20",
#         "수거요청 시간": "09:00 이후",
#         "맡기는 의류의 개수 (숫자만 입력)": "3",
#         "고가제품 포함 여부 (20만원 이상)": "있음",
#         "얼룩제거 요청 여부": "있음",
#         "수선 요청 여부": "없음",
#         "공동현관 비밀번호": "0808*",
#         "기타요청사항": "고가 제품 조심히 다뤄주세요!",
#     },
# }

# order_confirmed = send_checkout_request(test_payload)
# print(order_confirmed)


def recommend_tour_plan(place_list: list) -> tuple:
    """
    Create tour map and return both map object and formatted text
    Args:
        place_list (list): List of tourist places
    Returns:
        tuple: (folium map object, formatted response text)
    """
    # Create base map centered on Seoul
    m = folium.Map(location=[37.5665, 126.978], zoom_start=12, tiles="CartoDB positron")

    # Initialize geocoder
    geolocator = Nominatim(user_agent="concierge_chatbot")
    valid_places = []
    coordinates = []

    # Add markers for each place
    for idx, place in enumerate(place_list, 1):
        try:
            location = geolocator.geocode(f"{place}, 서울")
            if location:
                valid_places.append(place)
                coord = (location.latitude, location.longitude)
                coordinates.append(coord)

                folium.Marker(
                    location=coord,
                    popup=place,
                    tooltip=f"#{idx} {place}",
                    icon=folium.Icon(color="red", icon="info-sign"),
                ).add_to(m)
        except Exception as e:
            print(f"[ERROR] Failed to geocode {place}: {e}")

    # Add path between locations
    if len(coordinates) > 1:
        folium.PolyLine(coordinates, weight=2, color="blue", opacity=0.8).add_to(m)

    # Add location list
    places_text = "\n".join(
        [f"📍 {i+1}. {place}" for i, place in enumerate(valid_places)]
    )
    response_text = f"추천 관광 경로에 포함된 장소들입니다:\n{places_text}"

    return m, response_text


# 일반 뉴스 검색
def search_news(query):
    key = gcp_search_key
    cx = gcp_engine_id
    url = gcp_url
    params = {
        "key": key,
        "cx": cx,
        "q": query,
    }
    response = requests.get(url, params=params)
    return response.json()


def process_news_response(response_json):
    """
    JSON 응답에서 'items' 리스트를 파싱하여 기사 정보를 추출합니다.
    """
    try:
        items = response_json.get("items", [])
        processed_items = []

        for item in items:
            title = item.get("title", "제목 없음")
            link = item.get("link", "#")
            snippet = item.get("snippet", "요약 정보 없음")
            # 썸네일 추출
            pagemap = item.get("pagemap", {})
            cse_thumbnail = pagemap.get("cse_thumbnail", [])
            thumbnail_url = cse_thumbnail[0].get("src") if cse_thumbnail else None

            if title == "Google 뉴스":
                title = snippet

            processed_items.append(
                {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "thumbnail_url": thumbnail_url,
                }
            )

        return processed_items

    except Exception as e:
        print(f"Error processing response: {e}")
        return []


# 주문 데이터 조회
def get_order_history_data():
    """Fetch order history data with fresh cookies"""
    auth_info = handle_cookie_refresh()
    current_cookies = auth_info["cookies"]
    # print("[DEBUG] Current cookies:", current_cookies)

    try:
        # print("[DEBUG] Current cookies:", cookie)
        response = requests.get(url=order_history_url, cookies=current_cookies)
        response.raise_for_status()  # Raises HTTPError for bad responses

    except requests.HTTPError as http_err:
        print(f"[ERROR] HTTP error: {http_err}")
        if response.status_code == 401:
            error_msg = "로그인 쿠키 세션이 만료되었습니다."
            return error_msg, error_msg

    data = json.loads(response.text)
    order_list = data["result"]["list"]
    if not order_list:
        return "주문 내역이 없습니다.", None

    # 가장 최근에 신청한 서비스명
    most_recent_service = order_list[0]["itemTitle"]
    # 가장 많이 신청한 서비스명 (고빈도 서비스명)
    service_titles = [order["itemTitle"] for order in order_list]
    most_frequent_service = Counter(service_titles).most_common(1)[0][0]

    return most_recent_service, most_frequent_service


# [test] 주문 데이터 조회
# most_recent_item, most_frequent_item = get_order_history_data()
# print(most_recent_item, most_frequent_item)


def extract_base_service_type(full_title: str, service_data: dict) -> str:
    """Extract base service type from full service title"""
    # Get list of base service types from service_data
    base_services = list(service_data.keys())

    # Find matching base service
    for base_service in base_services:
        if base_service in full_title:
            return base_service

    return None


def request_order_history():
    """Process and format order history for user display with reorder links"""
    most_recent_item, most_frequent_item = get_order_history_data()
    print(
        "[DEBUG] most_recent_item, most_frequent_item: ",
        most_recent_item,
        most_frequent_item,
    )

    if not most_recent_item and most_frequent_item:
        return "주문 내역을 불러올 수 없습니다. 잠시 후 다시 시도해주세요."

    # Get service data for URLs
    service_data = get_service_data(service_list_url, cookie)
    print("[DEBUG] Available services:", list(service_data.keys()))

    recent_service = extract_base_service_type(most_recent_item, service_data)
    frequent_service = extract_base_service_type(most_frequent_item, service_data)
    print(f"[DEBUG] Mapped - Recent: {recent_service}, Frequent: {frequent_service}")

    result = {
        "content": (
            f"##### 📋 {name}님의 주문 내역 요약\n\n"
            f"##### 🔹 최근 신청한 서비스\n"
            f"👉🏻 **{most_recent_item}**\n\n"
            f"##### 🔹 가장 많이 이용한 서비스\n"
            f"👉🏻 **{most_frequent_item}**"
        ),
        "services": {
            "recent": {
                "name": recent_service,
                "base_type": recent_service,
                "url": (
                    f"https://dev.conciergeconnect.io/estimate/{service_data[recent_service]['seq']}"
                    if recent_service
                    else None
                ),
            },
            "frequent": {
                "name": frequent_service,
                "base_type": frequent_service,
                "url": (
                    f"https://dev.conciergeconnect.io/estimate/{service_data[frequent_service]['seq']}"
                    if frequent_service
                    else None
                ),
            },
        },
    }

    return result


# [test] 주문 내역 조회 함수
# order_history = request_order_history()
# print(order_history)


# 사용자 주소 기반 신청 가능 서비스 리스트
# @st.cache_data(ttl=600)  # 자주 호출되는 함수 10분 캐싱
def available_service_list(service_list_url):
    response = requests.get(url=service_list_url, cookies=cookie)
    data = json.loads(response.text)
    # 신청 가능한 서비스 구분자: seq (active= not none)
    active_service = [
        item for item in data.get("result", []) if item.get("seq") is not None
    ]
    category_names = [item["categoryName"] for item in active_service]

    return category_names


# 신청 가능한 컨시어지 서비스 리스트 -> tools.py 모듈 로드시 호출 when app.py 실행
service_list = available_service_list(service_list_url)


def request_available_service(name: str, address: str, service_list: list) -> dict:
    """신청 가능 서비스 조회 및 상세 정보 제공"""
    from src.api_setting.ois_api_info import get_service_url

    # Get active services and their details from ois API
    response = requests.get(url=service_list_url, cookies=cookie)
    data = json.loads(response.text)

    # 활성화된 서비스만 필터링 (seq가 있는 서비스)
    service_items = [
        item for item in data.get("result", []) if item.get("seq") is not None
    ]

    intro = f"{name}님, 현재 거주하고 계신 {address} 지역에서 신청 가능한 컨시어지 서비스를 안내해드립니다."

    services = []
    for item in service_items:
        service_detail = {
            "name": item["categoryName"],  # 한글 서비스명
            "description": item.get("categoryShortDesc", "상세 설명 준비중입니다."),
            "icon_url": item.get("categoryIconUrl", ""),  # 아이콘 URL
            "action": {
                "type": "service_request",
                "service": item["categoryName"],
                # "seq": item["seq"],  # 서비스 구분자
                "url": f"https://dev.conciergeconnect.io/estimate/{item['seq']}",
            },
        }
        services.append(service_detail)

    return {"message": intro, "services": services}


# Test code
# if __name__ == "__main__":
#     test_address = "강남구"
#     result = request_available_service(name, test_address, service_list)
#     print("\n[DEBUG] -- Available Services: -- \n", result)

#     print(f"Message: {result['message']}")
#     print("\nServices:")
#     for idx, service in enumerate(result["services"], 1):
#         print(f"\n{idx}. {service['name']}")
#         print(f"Description: {service['description']}")
#         print(f"Action: {service['action']}")


# 고빈도 서비스명 추출
def get_most_frequent_service():
    response = requests.get(url=order_history_url, cookies=cookie)

    # JSON 데이터 파싱
    data = json.loads(response.text)

    # 주문 내역 리스트 추출
    try:
        order_list = data["result"]["list"]

        # 가장 많이 신청한 서비스명 (고빈도 서비스명)
        service_titles = [order["itemTitle"] for order in order_list]
        most_frequent_service = Counter(service_titles).most_common(1)[0][0]
        return most_frequent_service

    except Exception as e:
        result = f"고빈도 서비스명 추출 실패: {e}"

        return result


# print("고빈도 서비스명 추출:\n", get_most_frequent_service())


def get_most_frequent_service(name: str):
    """
    사용자의 서비스 주문 이력을 조회하여 가장 많이 신청한 서비스명을 반환합니다.
    Args:
        name (str): 사용자 이름
    """
    # 주문 내역 url
    response = requests.get(url=order_history_url, cookies=cookie)

    # JSON 데이터 파싱
    data = json.loads(response.text)

    # 주문 내역 리스트 추출
    try:
        order_list = data["result"]["list"]

        # 가장 많이 신청한 서비스명 (고빈도 서비스명)
        service_titles = [order["itemTitle"] for order in order_list]
        most_frequent_service = Counter(service_titles).most_common(1)[0][0]
        result = most_frequent_service

        # result = (
        #     f"{name}님의 가장 많이 신청한 서비스명은 {most_frequent_service}입니다."
        # )

    except Exception as e:
        result = f"주문 내역을 불러오는 중 오류가 발생했습니다. {e}"

    return result


# print(get_most_frequent_service(name))
