import requests
from bs4 import BeautifulSoup
import json
import os

def crawl_notices():
    print("Crawling notices...")
    url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('tbody tr')
        notices = []
        for row in rows:
            title_elem = row.select_one('.b-title-box a')
            date_elem = row.select_one('.b-date')
            if title_elem and date_elem:
                title = title_elem.get_text(strip=True)
                link = f"https://www.ajou.ac.kr/kr/ajou/notice.do{title_elem['href']}"
                date_str = date_elem.get_text(strip=True)
                notices.append({'title': title, 'link': link, 'date': date_str})
        return notices
    except Exception as e:
        print(f"Notice crawl error: {e}")
        return []

def crawl_meals():
    print("Crawling meals...")
    url = "https://www.ajou.ac.kr/kr/life/food.do"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        days = ['월', '화', '수', '목', '금']
        meal_data = {day: {'breakfast': '정보 없음', 'lunch': '정보 없음', 'dinner': '정보 없음'} for day in days}
        
        # 아주대 식단표는 보통 .b-board-table 또는 table 내의 tbody tr 구조입니다.
        table = soup.select_one('table')
        if not table:
            print("No meal table found.")
            return meal_data

        rows = table.select('tbody tr')
        for row in rows:
            header = row.select_one('th')
            if not header: continue
            
            meal_type = header.get_text(strip=True)
            cells = row.select('td')
            
            for i, cell in enumerate(cells):
                if i < len(days):
                    day = days[i]
                    # 메뉴 텍스트를 줄바꿈을 유지하며 가져옵니다.
                    menu = cell.get_text(separator="\n", strip=True)
                    if not menu: menu = "정보 없음"
                    
                    if "조식" in meal_type:
                        meal_data[day]['breakfast'] = menu
                    elif "중식" in meal_type:
                        meal_data[day]['lunch'] = menu
                    elif "석식" in meal_type:
                        meal_data[day]['dinner'] = menu
        
        return meal_data
    except Exception as e:
        print(f"Meal crawl error: {e}")
        return {day: {'breakfast': '오류 발생', 'lunch': '오류 발생', 'dinner': '오류 발생'} for day in days}

if __name__ == "__main__":
    # 폴더 생성
    os.makedirs('assets/data', exist_ok=True)
    
    # 공지사항 저장
    notices = crawl_notices()
    with open('assets/data/notices.json', 'w', encoding='utf-8') as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved {len(notices)} notices.")
        
    # 식단 저장
    meals = crawl_meals()
    with open('assets/data/meals.json', 'w', encoding='utf-8') as f:
        json.dump(meals, f, ensure_ascii=False, indent=2)
    print("Successfully saved meals.")
