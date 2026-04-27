import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import re
import time

def crawl_ajou_meals():
    print("Crawling Ajou Meals...")
    cafeterias = {'dormitory': '363910', 'staff': '221904'}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    base_path = os.path.join(os.path.dirname(__file__), 'assets', 'data')
    meal_file = os.path.join(base_path, 'meals.json')
    
    # 기존 데이터 로드
    final_data = {}
    if os.path.exists(meal_file):
        try:
            with open(meal_file, 'r', encoding='utf-8') as f:
                final_data = json.load(f)
        except:
            pass

    # 오늘+7일부터 과거로 가며 크롤링
    current_date = datetime.now() + timedelta(days=7)
    consecutive_overlap = 0
    max_days = 30 # 최대 30일까지만 거꾸로 확인 (안전장치)
    days_checked = 0

    while consecutive_overlap < 4 and days_checked < max_days:
        date_str = current_date.strftime('%Y-%m-%d')
        day_name = ['월', '화', '수', '목', '금', '토', '일'][current_date.weekday()]
        display_key = f"{day_name} ({date_str})"
        
        # 이미 데이터가 있고 내용이 '정보 없음'이 아닌 경우 중복으로 간주할 준비
        has_existing = display_key in final_data
        all_info_none = True
        if has_existing:
            for cafe in final_data[display_key]:
                for meal_type in final_data[display_key][cafe]:
                    if final_data[display_key][cafe][meal_type] != "정보 없음":
                        all_info_none = False
                        break
        
        # 실제 크롤링 수행
        day_meal_data = {}
        found_any_new = False

        for cafe_name, cafe_id in cafeterias.items():
            meal_info = {'breakfast': '정보 없음', 'lunch': '정보 없음', 'dinner': '정보 없음'}
            if cafe_name == 'dormitory': meal_info['snack'] = '정보 없음'
            
            try:
                url = f"https://www.ajou.ac.kr/kr/life/food.do?mode=view&articleNo={cafe_id}&date={date_str}"
                resp = requests.get(url, headers=headers, timeout=15)
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')

                found = False
                for key, sel in {'breakfast':'.breakfast', 'lunch':'.lunch', 'dinner':'.dinner', 'snack':'.snackBar'}.items():
                    if key not in meal_info: continue
                    sec = soup.select_one(f'.b-menu-day{sel}')
                    if sec:
                        pres = sec.select('pre')
                        valid_texts = []
                        for p in pres:
                            txt = p.get_text(separator="\n", strip=True)
                            if txt and "등록된 식단이 없습니다" not in txt:
                                valid_texts.append(txt)
                        
                        if valid_texts:
                            meal_info[key] = "\n".join(valid_texts)
                            found = True
                            found_any_new = True
                
                if not found:
                    pres = soup.select('.food_view pre, .b-menu-day pre, pre')
                    valid_pres = []
                    for p in pres:
                        txt = p.get_text(separator="\n", strip=True)
                        if txt and "등록된 식단이 없습니다" not in txt and "운영시간" not in txt:
                            valid_pres.append(txt)
                    
                    if valid_pres:
                        combined = "\n".join(valid_pres)
                        found_any_new = True
                        if "[중식]" in combined or "[석식]" in combined:
                            l_m = re.search(r'\[중식\].*?(?=\[석식\]|$)', combined, re.DOTALL)
                            d_m = re.search(r'\[석식\].*$', combined, re.DOTALL)
                            if l_m: meal_info['lunch'] = l_m.group(0).strip()
                            if d_m: meal_info['dinner'] = d_m.group(0).strip()
                        else:
                            meal_info['lunch'] = combined.strip()
                
                for k in meal_info:
                    if "운영시간" in meal_info[k] and len(meal_info[k]) < 100 and "코너" not in meal_info[k]:
                        meal_info[k] = "정보 없음"

            except Exception:
                pass
            day_meal_data[cafe_name] = meal_info
        
        # 중복 카운트 로직
        if has_existing and not all_info_none:
            consecutive_overlap += 1
        else:
            consecutive_overlap = 0
            
        final_data[display_key] = day_meal_data
        current_date -= timedelta(days=1)
        days_checked += 1
        
    return final_data

def crawl_notices():
    print("Crawling new notices...")
    base_url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    base_path = os.path.join(os.path.dirname(__file__), 'assets', 'data')
    notice_file = os.path.join(base_path, 'notices.json')
    
    existing_notices = []
    if os.path.exists(notice_file):
        try:
            with open(notice_file, 'r', encoding='utf-8') as f:
                existing_notices = json.load(f)
        except:
            existing_notices = []
    
    def get_article_no(link):
        match = re.search(r'articleNo=(\d+)', link)
        return match.group(1) if match else link

    existing_ids = {get_article_no(n['link']) for n in existing_notices if not n.get('is_pinned')}
    
    new_regular_notices = []
    pinned_notices = []
    
    offset = 0
    limit = 50 
    reached_existing = False
    consecutive_overlap = 0

    while not reached_existing:
        url = f"{base_url}?mode=list&&articleLimit={limit}&article.offset={offset}"
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            rows = soup.select('tbody tr')
            if not rows: break

            for row in rows:
                tds = row.select('td')
                if len(tds) < 5: continue
                
                is_pinned = "공지" in tds[0].get_text(strip=True)
                a_tag = row.select_one('.b-title-box a')
                if not a_tag: continue
                
                title = a_tag.get_text(strip=True).replace("[공지]", "").strip()
                link = f"{base_url}{a_tag['href']}" if a_tag['href'].startswith('?') else a_tag['href']
                ano = get_article_no(link)

                date_str = ""
                for td in reversed(tds):
                    txt = td.get_text(strip=True)
                    if re.match(r'\d{4}-\d{2}-\d{2}', txt):
                        date_str = txt
                        break
                
                if is_pinned:
                    if offset == 0:
                        pinned_notices.append({'title': title, 'link': link, 'date': date_str, 'is_pinned': True})
                else:
                    if ano in existing_ids:
                        consecutive_overlap += 1
                        if consecutive_overlap >= 4:
                            reached_existing = True
                            break
                    else:
                        consecutive_overlap = 0
                        new_regular_notices.append({'title': title, 'link': link, 'date': date_str, 'is_pinned': False})
            
            if reached_existing: break
            offset += limit
            time.sleep(0.2)
            if offset > 1000: break
                
        except Exception as e:
            print(f"  Error: {e}")
            break
            
    old_regular_notices = [n for n in existing_notices if not n.get('is_pinned')]
    
    seen_new_ids = set()
    unique_new_regular = []
    for n in new_regular_notices:
        ano = get_article_no(n['link'])
        if ano not in seen_new_ids:
            unique_new_regular.append(n)
            seen_new_ids.add(ano)
    
    final_list = pinned_notices + unique_new_regular + old_regular_notices
    
    print(f"  New regular notices found: {len(unique_new_regular)}")
    print(f"  Total notices: {len(final_list)}")
    return final_list

if __name__ == "__main__":
    base_path = os.path.join(os.path.dirname(__file__), 'assets', 'data')
    os.makedirs(base_path, exist_ok=True)
    
    # 공지사항
    results = crawl_notices()
    notice_file = os.path.join(base_path, 'notices.json')
    with open(notice_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 식단
    meal_data = crawl_ajou_meals()
    meal_file = os.path.join(base_path, 'meals.json')
    with open(meal_file, 'w', encoding='utf-8') as f:
        json.dump(meal_data, f, ensure_ascii=False, indent=2)
    
    print(f"Script finished. Files saved in: {base_path}")
