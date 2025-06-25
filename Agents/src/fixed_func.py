# 고정 함수
# 컨시어지 API 호출과 무관한 함수 리스트

additional_functions = [
    {
        "type": "function",
        "strict": True,
        "function": {
            "name": "search_news",
            "description": "당신은 사용자의 뉴스 검색을 도와주는 Assistant입니다. 사용자가 검색하고자 하는 뉴스 키워드를 입력받습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 뉴스 키워드",
                    }
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "strict": True,
        "function": {
            "name": "recommend_tour_plan",
            "description": "당신은 사용자의 대한민국 수도 서울의 관광지를 추천해주는 Assistant입니다. 사용자가 가고자 하는 관광지의 대략적인 숫자를 입력받아 사용자에게 3곳 이상 추천하는 관광지 리스트를 알려줍니다. 이때, 답변은 array(list) 형태로 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "사용자에게 추천하는 관광지 리스트",
                    }
                },
                "required": ["place_list"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_order_history",
            "description": "당신은 유저의 서비스 이용 내역을 조회를 검색해서 알려주는 Assistant입니다. 유저가 지난 서비스 신청 내역을 물었을 경우 이 함수를 호출하세요.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_available_service",
            "description": "당신은 유저의 거주지역에서 신청 가능한 컨시어지 서비스 종류를 안내해주는 Assistant입니다. 유저가 신청 가능한 서비스 종류를 물었을 경우 이 함수를 호출하세요.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
