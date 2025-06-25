import time
import difflib  # 문장 유사도 비교를 위한 라이브러리


def measure_latency(func, *args, **kwargs):
    """
    특정 함수(예: LLM 응답 생성)의 실행 시간을 측정하는 함수
    """
    start_time = time.time()  # 시작 시간 기록
    response = func(*args, **kwargs)  # 실행할 함수 호출
    end_time = time.time()  # 종료 시간 기록

    latency = end_time - start_time  # 실행 시간 계산
    print(f"🔍 응답 지연 시간: {latency:.4f} 초")

    return response, latency


def evaluate_accuracy(generated_response, expected_response):
    """
    챗봇 응답의 정확도를 평가하는 함수 (문장 유사도 기반)
    """
    # nli embedder를 사용하여 유사도 계산하는 방식으로 변경 예정
    similarity = difflib.SequenceMatcher(
        None, generated_response, expected_response
    ).ratio()
    accuracy_score = round(similarity * 100, 2)  # 백분율 변환
    print(f"✅ 응답 정확도: {accuracy_score}%")

    return accuracy_score
