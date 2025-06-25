from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests


app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    message: str

# 외부 서버(ois,이룸)에서 HTTP 요청(requests.get("챗봇서버주소"))으로 챗봇 API를 호출하여 결과를 받음 
@app.post("/chatbot/ask")
async def ask_chatbot(req: ChatRequest):
    # ...챗봇 응답 생성 로직...
    answer = f"'{req.message}'에 대한 답변입니다."
    return {"answer": answer}

# 외부 서버 - 챗봇 서버 호출 예시 
user_id = "김은수"
resp = requests.get(f"http://챗봇서버주소:포트/api/latest-function/{user_id}")
print(resp.json())   