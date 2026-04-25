import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import sys

def crawl_and_update():
    print("Starting crawler...")
    
    # 1. Firebase 인증 확인
    key_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    if not key_json:
        print("ERROR: FIREBASE_SERVICE_ACCOUNT_KEY secret is missing!")
        sys.exit(1)
        
    try:
        key_dict = json.loads(key_json)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully.")
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}")
        sys.exit(1)

    # 2. 크롤링
    base_url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('tbody tr')
        print(f"Found {len(rows)} rows on the page.")
    except Exception as e:
        print(f"ERROR: Failed to fetch website: {e}")
        sys.exit(1)

    batch = db.batch()
    count = 0

    for row in rows:
        try:
            title_elem = row.select_one('.b-title-box a')
            date_elem = row.select_one('.b-date')
            
            if title_elem and date_elem:
                title = title_elem.get_text(strip=True)
                href = title_elem['href']
                link = f"https://www.ajou.ac.kr/kr/ajou/notice.do{href}"
                date_str = date_elem.get_text(strip=True)
                
                try:
                    dt = datetime.datetime.strptime(date_str, '%y.%m.%d')
                except:
                    dt = datetime.datetime.strptime(date_str, '%Y.%m.%d')
                    
                doc_id = link.split('articleNo=')[1].split('&')[0] if 'articleNo=' in link else str(hash(link))
                
                # 파이썬 SDK에서는 .document()를 사용해야 함
                doc_ref = db.collection('notices').document(doc_id)
                batch.set(doc_ref, {
                    'id': doc_id,
                    'title': title,
                    'link': link,
                    'date': date_str,
                    'timestamp': dt.timestamp()
                }, merge=True)
                count += 1
        except Exception as e:
            print(f"Warning: Skipping a row due to error: {e}")
            continue

    if count > 0:
        try:
            batch.commit()
            print(f"Successfully updated {count} notices to Firestore.")
        except Exception as e:
            print(f"ERROR: Failed to commit to Firestore: {e}")
            sys.exit(1)
    else:
        print("No notices found to update.")

if __name__ == "__main__":
    crawl_and_update()
