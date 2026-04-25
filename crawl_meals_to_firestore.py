import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup
import json
import os
import sys

def crawl_meals():
    print("Starting meal crawler...")
    
    # 1. Firebase 인증
    key_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    if not key_json:
        print("ERROR: FIREBASE_SERVICE_ACCOUNT_KEY missing!")
        sys.exit(1)
        
    try:
        key_dict = json.loads(key_json)
        cred = credentials.Certificate(key_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"ERROR: Firebase init failed: {e}")
        sys.exit(1)

    # 2. 아주대 식단 크롤링 (학생식당 기준)
    url = "https://www.ajou.ac.kr/kr/life/food.do"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 식단 표 분석 (보통 요일별로 구성됨)
        # 아주대 사이트 구조에 맞춰 파싱 로직 구현
        days = ['월', '화', '수', '목', '금']
        meal_data = {}
        
        # 실제 사이트의 테이블 구조를 파싱 (예시 로직)
        rows = soup.select('.food_list tr')
        for i, day in enumerate(days):
            # 실제 파싱 결과에 따라 이 부분을 조정
            # 여기서는 구조화된 데이터를 생성하여 저장하는 방식을 제안
            meal_data[day] = {
                'breakfast': '정보 없음',
                'lunch': '식단 정보를 확인 중입니다.',
                'dinner': '정보 없음'
            }

        # Firestore의 'meals' 컬렉션에 저장 (오늘 날짜나 요일 기준)
        # 'current_meals' 문서 하나에 전체 주간 식단을 업데이트하는 방식
        db.collection('meals').document('weekly').set({
            'last_updated': firestore.SERVER_TIMESTAMP,
            'data': meal_data
        })
        
        print("Successfully updated weekly meals to Firestore.")
    except Exception as e:
        print(f"ERROR: Meal crawling failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    crawl_meals()
