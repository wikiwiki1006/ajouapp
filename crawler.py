import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

def get_date_list():
    date_list = []
    current = datetime.now()
    # 현재 날짜로부터 7일치 데이터 수집 (주말 포함)
    for i in range(7):
        target = current + timedelta(days=i)
        date_list.append(target.strftime('%Y-%m-%d'))
    return date_list

def crawl_ajou_meals():
    print("Crawling Ajou Meals with updated structure...")
    cafeterias = {
        'dormitory': '363910', # 기숙사식당
        'staff': '221904'      # 교직원식당
    }
    
    date_list = get_date_list()
    final_data = {}

    for date_str in date_list:
        weekday_map = ['월', '화', '수', '목', '금', '토', '일']
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = weekday_map[dt.weekday()]
        
        display_key = f"{day_name} ({date_str})"
        final_data[display_key] = {}

        for cafe_name, cafe_id in cafeterias.items():
            url = f"https://www.ajou.ac.kr/kr/life/food.do?mode=view&articleNo={cafe_id}&date={date_str}"
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                response = requests.get(url, headers=headers, timeout=10)
                response.encoding = 'utf-8' # 인코딩 명시
                soup = BeautifulSoup(response.text, 'html.parser')
                
                meal_info = {
                    'breakfast': '정보 없음',
                    'lunch': '정보 없음',
                    'dinner': '정보 없음'
                }
                if cafe_name == 'dormitory':
                    meal_info['snack'] = '정보 없음'

                # New structure: .b-menu-day.breakfast, etc.
                mappings = {
                    'breakfast': '.b-menu-day.breakfast',
                    'lunch': '.b-menu-day.lunch',
                    'dinner': '.b-menu-day.dinner'
                }
                if cafe_name == 'dormitory':
                    mappings['snack'] = '.b-menu-day.snackBar'

                for key, selector in mappings.items():
                    container = soup.select_one(selector)
                    if container:
                        menu_content = container.select_one('pre')
                        if menu_content:
                            text = menu_content.get_text(separator="\n", strip=True)
                            # Clean up
                            if not text or "등록된 식단이 없습니다" in text or "식단이 없습니다" in text:
                                text = "정보 없음"
                            meal_info[key] = text
                
                final_data[display_key][cafe_name] = meal_info
                print(f"  Fetched {cafe_name} for {date_str}")
                        
            except Exception as e:
                print(f"Error crawling {cafe_name} on {date_str}: {e}")
                
    return final_data

def crawl_notices():
    print("Crawling notices from 2026-01-01...")
    base_url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    pinned_notices = []
    regular_notices = []
    
    offset = 0
    limit = 10
    target_date = datetime(2026, 1, 1)
    reached_target = False
    
    while not reached_target:
        url = f"{base_url}?article.offset={offset}&articleLimit={limit}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('tbody tr')
            
            if not rows:
                break
                
            page_has_new_regular = False
            for row in rows:
                num_box = row.select_one('.b-num-box')
                is_pinned = "num-notice" in num_box.get("class", []) if num_box else False
                
                title_elem = row.select_one('.b-title-box a')
                date_elem = row.select_one('td:nth-last-child(1)') # Date is usually the last td
                
                if title_elem and date_elem:
                    title = title_elem.get_text(strip=True)
                    # Remove [공지] prefix from title if exists
                    if title.startswith("[공지]"):
                        title = title[4:].strip()
                        
                    link = f"{base_url}{title_elem['href']}"
                    date_str = date_elem.get_text(strip=True)
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                    except:
                        continue

                    notice_item = {
                        'title': title,
                        'link': link,
                        'date': date_str,
                        'is_pinned': is_pinned
                    }

                    if is_pinned:
                        # Only collect pinned notices from the first page
                        if offset == 0:
                            pinned_notices.append(notice_item)
                    else:
                        if dt >= target_date:
                            regular_notices.append(notice_item)
                            page_has_new_regular = True
                        else:
                            reached_target = True
            
            if not page_has_new_regular and offset > 0 and not is_pinned: # Safety break
                 # If we are past the first page and didn't find any regular notices >= target_date
                 # but we need to be careful because pinned notices are on every page
                 pass

            if reached_target:
                break
                
            offset += limit
            print(f"  Fetched offset {offset}...")
            
        except Exception as e:
            print(f"  Error at offset {offset}: {e}")
            break
            
    # Combine: Pinned at top, then regular
    return pinned_notices + regular_notices

if __name__ == "__main__":
    os.makedirs('assets/data', exist_ok=True)
    # 공지사항 업데이트
    notices = crawl_notices()
    with open('assets/data/notices.json', 'w', encoding='utf-8') as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)
    # 식단 업데이트
    meals = crawl_ajou_meals()
    with open('assets/data/meals.json', 'w', encoding='utf-8') as f:
        json.dump(meals, f, ensure_ascii=False, indent=2)
    print("Data update completed successfully.")
