import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

def get_date_list():
    date_list = []
    current = datetime.now()
    # 오늘부터 최대 10일치 데이터를 가져오도록 설정
    for i in range(10):
        target = current + timedelta(days=i)
        if target.weekday() < 5: # 월~금만 포함
            date_list.append(target.strftime('%Y-%m-%d'))
    return date_list

def crawl_ajou_meals():
    print("Crawling Ajou Meals via <pre> tags...")
    
    # 식당 ID (221903: 기숙사/학생식당, 221904: 교직원식당)
    cafeterias = {
        'dormitory': '221903',
        'staff': '221904'
    }
    
    date_list = get_date_list()
    final_data = {}

    for date_str in date_list:
        weekday_map = ['월', '화', '수', '목', '금', '토', '일']
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = weekday_map[dt.weekday()]
        
        display_key = f"{day_name} ({date_str})"
        final_data[display_key] = {
            'dormitory': {'breakfast': '정보 없음', 'lunch': '정보 없음', 'dinner': '정보 없음'},
            'staff': {'breakfast': '정보 없음', 'lunch': '정보 없음', 'dinner': '정보 없음'}
        }

        for cafe_name, cafe_id in cafeterias.items():
            url = f"https://www.ajou.ac.kr/kr/life/food.do?mode=view&articleNo={cafe_id}&date={date_str}"
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # <pre> 태그들을 모두 찾습니다.
                # 순서: 0:아침, 1:점심, 2:저녁, 3:분식
                pre_tags = soup.select('.food_menu_list pre')
                
                if len(pre_tags) >= 3:
                    final_data[display_key][cafe_name]['breakfast'] = pre_tags[0].get_text(strip=True)
                    final_data[display_key][cafe_name]['lunch'] = pre_tags[1].get_text(strip=True)
                    final_data[display_key][cafe_name]['dinner'] = pre_tags[2].get_text(strip=True)
                else:
                    # 구조가 다를 경우를 대비한 대체 로직 (전체 텍스트에서 찾기)
                    items = soup.select('.food_menu_list > li')
                    for item in items:
                        meal_time = item.select_one('strong').get_text(strip=True)
                        menu_text = item.select_one('pre').get_text(strip=True) if item.select_one('pre') else item.get_text(strip=True)
                        
                        if "아침" in meal_time:
                            final_data[display_key][cafe_name]['breakfast'] = menu_text
                        elif "점심" in meal_time:
                            final_data[display_key][cafe_name]['lunch'] = menu_text
                        elif "저녁" in meal_time:
                            final_data[display_key][cafe_name]['dinner'] = menu_text
            except Exception as e:
                print(f"Error crawling {cafe_name} on {date_str}: {e}")
                
    return final_data

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

if __name__ == "__main__":
    os.makedirs('assets/data', exist_ok=True)
    
    notices = crawl_notices()
    with open('assets/data/notices.json', 'w', encoding='utf-8') as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)
        
    meals = crawl_ajou_meals()
    with open('assets/data/meals.json', 'w', encoding='utf-8') as f:
        json.dump(meals, f, ensure_ascii=False, indent=2)
        
    print(f"Update complete! {len(notices)} notices and {len(meals)} days of meals saved.")
