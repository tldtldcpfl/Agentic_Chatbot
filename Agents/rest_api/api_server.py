from fastapi import FastAPI
from src.db.db_util import get_order_history, get_latest_function_name  # 예시 함수 import

app = FastAPI()

# 엔드포인트에서 get_latest_function_name을 호출하여 결과를 반환
# - 챗봇 서버에 REST API 엔드포인트를 만들고, 그 엔드포인트에서 해당 함수를 호출
# - 외부 서버는 HTTP로 챗봇 서버의 API를 호출해서 DB 데이터를 조회 가능 
@app.get("/api/order-history/{user_id}")
def order_history(user_id: str):
    # DB에서 주문 이력 조회
    result = get_order_history(user_id)
    return {"order_history": result}

# 데이터 조회 엔드포인트 
@app.get("/api/latest-function/{user_id}")
def latest_function(user_id: str):
    """
    외부 서버에서 호출: 특정 user_id의 최신 함수명(들) 반환
    """
    result = get_latest_function_name(user_id)
    return {"user_id": user_id, "latest_function": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
