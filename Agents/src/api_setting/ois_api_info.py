import os
import toml
import requests
from typing import Dict, Any
import sys

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get project root (two levels up from script)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.append(PROJECT_ROOT)

# print(PROJECT_ROOT)


def load_secrets():
    """Load secrets.toml file"""
    # .streamlit/secrets.toml 파일 경로 확인
    secret_dir = f"{PROJECT_ROOT}/.streamlit/secrets.toml"

    secrets = toml.load(secret_dir)
    # ois api 도메인 (sub-domain = "api.dev.conciergeconnect.io")
    base_url = secrets["base_url"]["server_domain"]
    return base_url


base_url = load_secrets()
# server_domain 확인
# print(base_url)


# 챗봇 sub 도메인: api.dev.chat.conciergeconnect.io
# ois 백엔드 api sub 도메인
# base_url -> api.dev.conciergeconnect.io

# 서버 엔드포인트
# 주문 확정 이전 checkbox url
checkout_url = f"https://{base_url}/api/v1/checkout"

# 주문 내역 url
order_history_url = f"https://{base_url}/api/v1/orders?searchPeriod=30&page=1&limit=20"

# 사용자 정보 url
user_info_url = f"https://{base_url}/api/v1/accounts/me"

# 주문 확정 url
order_confirm_url = f"https://{base_url}/api/v1/orders"

# 신청 가능 서비스 리스트 url
service_list_url = f"https://{base_url}/api/v1/items"


def get_service_data(service_list_url: str, cookie: dict) -> Dict[str, Dict[str, Any]]:
    """Get service data directly from API"""
    try:
        response = requests.get(url=service_list_url, cookies=cookie)

        # Handle expired cookie session
        if response.status_code == 401:
            # print("[DEBUG] 쿠키 세션이 만료되었습니다. 쿠키 refresh 필요")
            return "[DEBUG] 쿠키 세션이 만료되었습니다. 쿠키 refresh 필요 - util.py"

        response.raise_for_status()
        data = response.json().get("result", [])

        service_data = {}
        for item in data:
            if item.get("seq") is not None:  # Only active services
                service_data[item["categoryName"]] = {
                    "seq": item["seq"],
                    "endpoint": f"items/{item['seq']}",
                    "description": item.get("categoryShortDesc", ""),
                }
        # print(f"[DEBUG] Loaded {len(service_data)} active services")
        return service_data

    except Exception as e:
        print(f"[ERROR] Failed to get service data: {e}")
        return f"[ERROR] Failed to get service data: {e}"


# print(get_service_data(service_list_url), cookie)


# def get_estimate_info(service_seq: int, cookie: dict) -> Dict[str, str]:
#     """Get estimate ID and RSC value for a service"""
#     try:
#         estimate_url = f"https://{base_url}/api/v1/items/{service_seq}/estimate"
#         response = requests.get(url=estimate_url, cookies=cookie)

#         if response.status_code == 401:
#             return {"error": "쿠키 세션이 만료되었습니다."}

#         response.raise_for_status()
#         data = response.json().get("result", {})

#         return {
#             "estimate_id": str(data.get("estimateId", "")),
#             "rsc": data.get("rsc", ""),
#         }
#     except Exception as e:
#         print(f"[ERROR] Failed to get estimate info: {e}")
#         return {"error": f"견적 정보를 가져오는데 실패했습니다: {str(e)}"}


# tools_updated.json 파일을 활용해서 유저 의도에 맞는 service type 매핑
# def get_service_url(function_name: str, cookie: dict) -> str:
#     """Get service URL based on function name"""
#     try:
#         # 함수명이 컨시어지 주문 함수이면
#         if function_name.startswith("request_service_"):
#             idx = int(function_name.split("_")[-1])

#             # Get service data using existing function
#             service_data = get_service_data(service_list_url, cookie)
#             if isinstance(service_data, str) and "ERROR" in service_data:
#                 return "서비스 정보를 가져오는데 실패했습니다."

#             # Get service type from index
#             service_type = list(service_data.keys())[idx - 1]
#             service_seq = service_data[service_type]["seq"]

#             # Construct service URL using seq
#             service_url = f"https://{base_url}/services/{service_seq}/order"
#             print(
#                 f"[DEBUG] Mapped {function_name} to {service_type} (seq: {service_seq})"
#             )
#             return {
#                 "url": service_url,
#                 "service_type": service_type,
#                 "seq": service_seq,
#             }

#         return {"error": "올바른 서비스 함수명이 아닙니다."}

#     except Exception as e:
#         print(f"[ERROR] Failed to get service URL: {e}")
#         return f"[ERROR] 서비스 URL을 가져오는데 실패했습니다: {e}"


def get_service_url(function_name: str, cookie: dict) -> Dict[str, Any]:
    """Get service URL based on function name"""
    try:
        if function_name.startswith("request_service_"):
            # Get service info
            service_data = get_service_data(service_list_url, cookie)
            if isinstance(service_data, str) and "ERROR" in service_data:
                return {"error": "서비스 정보를 가져오는데 실패했습니다."}

            # Get service type and sequence
            idx = int(function_name.split("_")[-1])
            service_type = list(service_data.keys())[idx - 1]
            service_seq = service_data[service_type]["seq"]

            # Simplified URL construction - just use service_seq
            service_url = f"https://dev.conciergeconnect.io/estimate/{service_seq}"

            print(
                f"[DEBUG] Mapped {function_name} to {service_type} (seq: {service_seq})"
            )
            print(f"[DEBUG] Redirect URL: {service_url}")

            return {
                "url": service_url,
                "service_type": service_type,
                "seq": service_seq,
            }

        return {"error": "올바른 서비스 함수명이 아닙니다."}

    except Exception as e:
        print(f"[ERROR] Failed to get service URL: {e}")
        return {"error": f"서비스 URL을 가져오는데 실패했습니다: {str(e)}"}


# def test_service_url_redirect():
#     """Test if service URLs are accessible and redirect correctly"""
#     from util import get_cookie_from_context
#     import requests

#     cookie = get_cookie_from_context()

#     # Known working service mappings
#     test_services = {
#         "request_service_1": "가사도우미",  # seq=2
#         "request_service_2": "세탁",  # seq=133
#         "request_service_3": "동행",  # seq=303
#     }

#     print("\nTesting service URL redirects:")
#     print("-" * 50)

#     for function_name, service_name in test_services.items():
#         print(f"\n🔍 Testing {service_name} service:")

#         # Get URL from function
#         result = get_service_url(function_name, cookie)
#         url = result["url"]
#         print(f"URL: {url}")

#         # Test URL accessibility
#         try:
#             response = requests.get(url)
#             print(f"Status Code: {response.status_code}")
#             print(f"Redirect URL: {response.url}")

#             if response.status_code == 200:
#                 print(f"✅ Success: URL accessible")
#             else:
#                 print(f"❌ Error: Status {response.status_code}")

#         except requests.RequestException as e:
#             print(f"❌ Error accessing URL: {str(e)}")


# if __name__ == "__main__":
#     test_service_url_redirect()
