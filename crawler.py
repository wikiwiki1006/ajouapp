import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import re
import time

def get_date_list():
    date_list = []
    current = datetime.now()
    for i in range(-1, 8):
        target = current + timedelta(days=i)
        date_list.append(target.strftime('%Y-%m-%d'))
    return date_list

def crawl_ajou_meals():
    print("Crawling Ajou Meals...")
    cafeterias = {'dormitory': '363910', 'staff': '221904'}
    date_list = get_date_list()
    final_data = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    for date_str in date_list:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = ['월', '화', '수', '목', '금', '토', '일'][dt.weekday()]
            display_key = f"{day_name} ({date_str})"
            final_data[display_key] = {}

            for cafe_name, cafe_id in cafeterias.items():
                url = f"https://www.ajou.ac.kr/kr/life/food.do?mode=view&articleNo={cafe_id}&date={date_str}"
                resp = requests.get(url, headers=headers, timeout=15)
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                meal_info = {'breakfast': '정보 없음', 'lunch': '정보 없음', 'dinner': '정보 없음'}
                if cafe_name == 'dormitory': meal_info['snack'] = '정보 없음'

                found = False
                for key, sel in {'breakfast':'.breakfast', 'lunch':'.lunch', 'dinner':'.dinner', 'snack':'.snackBar'}.items():
                    if key not in meal_info: continue
                    sec = soup.select_one(f'.b-menu-day{sel}')
                    if sec and sec.select_one('pre'):
                        txt = sec.select_one('pre').get_text(separator="\n", strip=True)
                        if txt and "등록된 식단이 없습니다" not in txt:
                            meal_info[key] = txt
                            found = True
                
                if not found:
                    pres = soup.select('.food_view pre, .b-menu-day pre, pre')
                    combined = "\n".join([p.get_text(separator="\n", strip=True) for p in pres])
                    if combined.strip() and "등록된 식단이 없습니다" not in combined:
                        if "[중식]" in combined or "[석식]" in combined:
                            l_m = re.search(r'\[중식\].*?(?=\[석식\]|$)', combined, re.DOTALL)
                            d_m = re.search(r'\[석식\].*$', combined, re.DOTALL)
                            if l_m: meal_info['lunch'] = l_m.group(0).strip()
                            if d_m: meal_info['dinner'] = d_m.group(0).strip()
                        else:
                            meal_info['lunch'] = combined.strip()
                final_data[display_key][cafe_name] = meal_info
        except: pass
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
                        reached_existing = True
                        break
                    else:
                        new_regular_notices.append({'title': title, 'link': link, 'date': date_str, 'is_pinned': False})
            
            if reached_existing: break
            offset += limit
            time.sleep(0.2)
            if offset > 500: break
                
        except Exception as e:
            print(f"  Error: {e}")
            break
            
    old_regular_notices = [n for n in existing_notices if not n.get('is_pinned')]
    combined_regular = new_regular_notices + old_regular_notices
    final_list = pinned_notices + combined_regular
    
    print(f"  New regular notices found: {len(new_regular_notices)}")
    print(f"  Total notices: {len(final_list)}")
    return final_list

if __name__ == "__main__":
    # 프로젝트 구조에 맞춰 저장 경로 설정
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
