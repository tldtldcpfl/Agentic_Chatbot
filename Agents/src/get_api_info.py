import requests
import json
import re
import toml
import os
import sys
from pathlib import Path
from typing import Dict, List

# 현재 스크립트 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# print(SCRIPT_DIR)
sys.path.append(SCRIPT_DIR)

# 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from api_setting.ois_api_info import (
    load_secrets,
    user_info_url,
    get_service_data,
    service_list_url,
)
from util import handle_cookie_refresh


# Get auth info and cookies at module level
auth_info = handle_cookie_refresh()  # st 메서드 사용
env = auth_info["environment"]
cookie = auth_info["cookies"]
# print("[DEBUG] cookies:\n", cookie)


# dev sub-도메인 -> api.dev.conciergeconnect.io
base_url = load_secrets()
# print(base_url)


def get_user_info():
    """사용자 이름, 주소, 폰번호"""
    try:
        response = requests.get(url=user_info_url, cookies=cookie)
        data = json.loads(response.text)
        # print("[debug]", data)
        result = data.get("result", {})

        name = result.get("name", "")
        phone_number = result.get("phone", "")
        address = result.get("address", "")

        return name, phone_number, address

    except Exception as e:
        return f"[error] 사용자 정보 로드 실패: {e}"


# 사용자 정보 로드 - 사용자 이름, 주소, 폰번호
name, phone_number, address = get_user_info()
# print(name, address)


def get_service_fields(service_type: str):

    service_data = get_service_data(service_list_url, cookie)
    if not isinstance(service_data, dict):
        print(service_data)
        raise TypeError(f"Expected dict, got {type(service_data)}")

    if service_type not in service_data:
        raise ValueError(f"서비스 타입 식별 불가: {service_type}")

    service_info = service_data[service_type]
    endpoint = service_info["endpoint"]

    endpoint = service_data[service_type]["endpoint"]
    common_url = f"https://{base_url}/api/v1/{endpoint}"
    # print(common_url)

    # Get field details
    response = requests.get(url=common_url, cookies=cookie)
    data = json.loads(response.text)

    field_name_list = []
    field_options = {}
    field_types = {}

    if "result" in data and "itemEstimateTemplateList" in data["result"]:
        for item in data["result"]["itemEstimateTemplateList"]:
            field_name = item["name"]
            field_type = item["type"]

            field_name_list.append(field_name)
            field_types[field_name] = field_type

            # Only add options for RADIO type fields
            if field_type == "RADIO" and "itemList" in item:
                field_options[field_name] = [opt["name"] for opt in item["itemList"]]

    return field_name_list, field_options, field_types


# 함수명 인덱스 처리와 동일하게 서비스 필드명도 인덱스 처리
def create_service_fields() -> Dict[str, List[str]]:
    """
    Create indexed service field variables (e.g. service_1_fields, service_2_fields)
    """
    # Get service data directly from API
    service_data = get_service_data(service_list_url, cookie)

    # Create mapping between index and Korean service names
    service_field_map = {}
    field_variables = {}

    try:
        # TODO: 한글 서비스명(service_name_ko) -> 인덱스 함수명 대신 db에 저장
        for idx, (service_name_ko, _) in enumerate(service_data.items(), 1):
            # print('한글 서비스명: ', service_name_ko)
            # Create indexed field name (e.g. service_1_fields)
            field_name = f"service_{idx}_fields"

            # Store mapping for later use
            service_field_map[field_name] = service_name_ko

            # Get fields using Korean name
            field_variables[field_name] = get_service_fields(service_name_ko)[0]
            print(f"[DEBUG] Created {field_name} for {service_name_ko}")

        # Store mapping for use in other modules
        globals()["service_field_map"] = service_field_map

        return field_variables

    except Exception as e:
        print(f"[ERROR] 로컬 쿠키 refresh 필요: {e}")


def global_field_variables(service_fields: Dict[str, List[str]]) -> None:
    """
    Register service fields as global variables.
    Args:
        service_fields: Dictionary of service field mappings
    """

    for field_name, field_list in service_fields.items():
        # # globals()는 현재 실행 중인 전역 스코프의 변수들을 딕셔너리 형태로 반환하는 내장 함수
        globals()[field_name] = field_list
        # print(f"[DEBUG] Registered global variable: {field_name}")


# Initialize service fields
service_fields = create_service_fields()
# print(service_fields)

# globally registered variables
global_field_variables(service_fields)
# print("[DEBUG] Finished get_api_info.py initialization")


# print(service_3_fields)
