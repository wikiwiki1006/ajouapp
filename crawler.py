import requests
from bs4 import BeautifulSoup
import json
import datetime
import os

def crawl_notices():
    print("Crawling notices...")
    url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    response = requests.get(url)
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

def crawl_meals():
    print("Crawling meals...")
    url = "https://www.ajou.ac.kr/kr/life/food.do"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    days = ['월', '화', '수', '목', '금']
    meal_data = {}
    table = soup.select_one('table')
    if table:
        rows = table.select('tbody tr')
        for row in rows:
            header = row.select_one('th')
            if not header: continue
            meal_type = header.get_text(strip=True)
            cells = row.select('td')
            for i, cell in enumerate(cells):
                if i < len(days):
                    day = days[i]
                    if day not in meal_data: meal_data[day] = {}
                    menu = cell.get_text(separator="\n", strip=True)
                    if "조식" in meal_type: meal_data[day]['breakfast'] = menu
                    elif "중식" in meal_type: meal_data[day]['lunch'] = menu
                    elif "석식" in meal_type: meal_data[day]['dinner'] = menu
    return meal_data

if __name__ == "__main__":
    os.makedirs('assets/data', exist_ok=True)
    
    # 공지사항 저장
    notices = crawl_notices()
    with open('assets/data/notices.json', 'w', encoding='utf-8') as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)
        
    # 식단 저장
    meals = crawl_meals()
    with open('assets/data/meals.json', 'w', encoding='utf-8') as f:
        json.dump(meals, f, ensure_ascii=False, indent=2)
        
    print("All data saved to assets/data/")
