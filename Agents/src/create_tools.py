from typing import List, Dict
import json
from get_api_info import get_service_fields
from api_setting.ois_api_info import get_service_data, service_list_url

# 컨시어지 api와 무관한 함수는 fixed_func에서 로드
from fixed_func import additional_functions

from util import handle_cookie_refresh

auth_info = handle_cookie_refresh()
env = auth_info["environment"]
cookie = auth_info["cookies"]
# print(cookie)


def create_dynamic_openai_function_payload(service_fields, service_info=None):
    """
    get_service_fields의 결과를 기반으로 OpenAI API Function Calling용 payload를 동적으로 생성합니다.

    조건:
      - result 내의 "title"을 함수 이름으로 사용합니다.
      - itemEstimateTemplateList 내의 각 항목을 순회하면서, 각 항목의 "name"을 파라미터 key로 사용합니다.
      - 각 파라미터의 스키마는 오직 "type"과 "description"만을 가집니다.
      - RADIO 타입의 경우, itemList 정보를 "description"에 (선택 옵션: ...) 형식으로 포함시킵니다.
      - DATE 타입인 경우, 날짜 포맷 정보를 "description"에 추가합니다.
      - isRequire가 True인 필드는 required 리스트에 포함합니다.

    입력:
      service_fields (dict): get_service_fields 함수의 JSON 결과

    반환:
      OpenAI API Function Calling에 사용할 payload (dict)
    """
    result = service_fields.get("result", {})
    # function_name (한글)
    function_name = result.get("title", "Unnamed Service")

    # # Use short service description if available
    if service_info and service_info.get("description"):
        function_description = f"{service_info['description']} 서비스 신청을 돕는 Assistant입니다. 사용자가 {service_info['description']} 서비스 신청을 요청했을 경우 이 함수를 호출하세요."

    else:
        function_description = f"{function_name} 신청을 돕는 Assistant입니다. 사용자가 {function_name} 신청을 요청했을 경우 이 함수를 호출하세요."

    properties = {}
    required_fields = []

    for field in result.get("itemEstimateTemplateList", []):
        field_name = field.get("name", "Unknown Field")
        # 스키마에는 오직 "type"과 "description"만 포함합니다.
        field_schema = {"type": "string"}

        description = field_name  # 기본 설명

        field_type = field.get("type")
        if field_type == "RADIO":
            # RADIO 타입의 경우, itemList 내 옵션을 description에 포함 (콤마로 구분)
            options = ", ".join(
                opt.get("name", "") for opt in field.get("itemList", [])
            )
            description += f" (선택 옵션: {options})"
        elif field_type == "DATE":
            description += " (형식: YYYY-MM-DD)"
        # TEXT_FIELD, TIME 등은 별도의 추가 설명 없이 기본 문자열로 처리

        field_schema["description"] = description
        properties[field_name] = field_schema

        if field.get("isRequire", False):
            required_fields.append(field_name)

    payload = {
        "type": "function",
        "strict": True,
        "function": {
            "name": function_name,
            "description": function_description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_fields,
                "additionalProperties": False,
            },
        },
    }

    return payload


# def create_tools_list(cookie: dict) -> List[Dict]:
#     """Create complete tools list for OpenAI function calling"""
#     tools = []

#     # Get service data directly from API
#     service_data = get_service_data(service_list_url, cookie)

#     # Add service functions
#     # idx: 한글 서비스명 (title)을 대체할 구분자 인덱스
#     # service_name_ko (한글)
#     # service_info: ois api 호출에 필요한 정보 (seq, endpoint, description)
#     for idx, (service_name_ko, service_info) in enumerate(service_data.items(), 1):
#         try:
#             # Use index-based function name
#             function_name = f"request_service_{idx}"

#             # Get service fields using Korean service name
#             field_name_list, field_options, field_types = get_service_fields(
#                 service_name_ko  # Use Korean service name from API
#             )

#             # Create function payload
#             function_payload = create_dynamic_openai_function_payload(
#                 {
#                     "result": {
#                         "title": function_name,  # Use indexed name for OpenAI
#                         "itemEstimateTemplateList": [
#                             {
#                                 "name": field_name,
#                                 "type": field_types[field_name],
#                                 "isRequire": True,
#                                 "itemList": (
#                                     [
#                                         {"name": option}
#                                         for option in field_options.get(field_name, [])
#                                     ]
#                                     if field_types[field_name] == "RADIO"
#                                     else []
#                                 ),
#                             }
#                             for field_name in field_name_list
#                         ],
#                     }
#                 },
#                 service_info=service_info,
#             )

#             tools.append(function_payload)
#             print(
#                 f"[SUCCESS] Added {function_name} 서비스 신청 function ({service_name_ko}) to tools list"
#             )

#         except Exception as e:
#             print(f"[ERROR] Failed to create function for {service_name_ko}: {e}")

#     tools.extend(additional_functions)

#     # Save to JSON file
#     with open("src/tools_updated.json", "w", encoding="UTF-8") as f:
#         json.dump(tools, f, ensure_ascii=False, indent=2)

#     print(f"\n[SUCCESS] Created tools list with {len(tools)} functions")
#     return tools


# create_tools.py script 파일 실행
# if __name__ == "__main__":
#     tools = create_tools_list(cookie)


# simplify create_tools_list 함수 since we're only redirecting now
def create_tools_list(cookie: dict) -> List[Dict]:
    """Create simplified tools list for service redirects"""
    tools = []

    # Get service data from API
    service_data = get_service_data(service_list_url, cookie)

    # Create simplified service functions
    for idx, (service_name_ko, service_info) in enumerate(service_data.items(), 1):
        try:
            function_name = f"request_service_{idx}"

            # Simplified function payload - no fields needed
            function_payload = {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": f"{service_info['description']} 서비스 신청 페이지로 이동합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {},  # No parameters needed for redirect
                        "required": [],
                    },
                },
            }

            tools.append(function_payload)
            print(f"[SUCCESS] Added redirect function for {service_name_ko}")

        except Exception as e:
            print(f"[ERROR] Failed to create function for {service_name_ko}: {e}")

    # Add other functions (news, history etc)
    tools.extend(additional_functions)

    # Save to JSON
    with open("src/tools_updated.json", "w", encoding="UTF-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Created tools list with {len(tools)} functions")
    return tools


if __name__ == "__main__":
    tools = create_tools_list(cookie)
