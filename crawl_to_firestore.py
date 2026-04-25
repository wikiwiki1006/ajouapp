import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os

def crawl_and_update():
    # 1. Firebase 인증
    key_dict = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY'))
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # 2. 크롤링
    base_url = "https://www.ajou.ac.kr/kr/ajou/notice.do"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('tbody tr')

    batch = db.batch()
    count = 0

    for row in rows:
        title_elem = row.select_one('.b-title-box a')
        date_elem = row.select_one('.b-date')
        
        if title_elem and date_elem:
            title = title_elem.get_text(strip=True)
            href = title_elem['href']
            link = f"https://www.ajou.ac.kr/kr/ajou/notice.do{href}"
            date_str = date_elem.get_text(strip=True)
            
            # YY.MM.DD 파싱
            try:
                dt = datetime.datetime.strptime(date_str, '%y.%m.%d')
            except:
                dt = datetime.datetime.strptime(date_str, '%Y.%m.%d')
                
            doc_id = link.split('articleNo=')[1].split('&')[0] if 'articleNo=' in link else str(hash(link))
            
            # Firestore에 저장할 데이터
            doc_ref = db.collection('notices').doc(doc_id)
            batch.set(doc_ref, {
                'id': doc_id,
                'title': title,
                'link': link,
                'date': date_str,
                'timestamp': dt.timestamp()
            }, merge=True)
            count += 1

    batch.commit()
    print(f"Successfully updated {count} notices to Firestore.")

if __name__ == "__main__":
    crawl_and_update()
