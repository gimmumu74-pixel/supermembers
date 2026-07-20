import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import pytz

# 1. 깃허브 시크릿에서 키 값 가져오기
gcp_json_str = os.environ.get("GCP_JSON")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

if not all([gcp_json_str, TELEGRAM_TOKEN, CHAT_ID]):
    print("⚠️ 시크릿 키가 설정되지 않았습니다.")
    exit()

# 2. 구글 시트 연결
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(gcp_json_str), scope)
client = gspread.authorize(creds)
sheet = client.open('슈퍼멤버스').sheet1

# 3. 오늘 날짜 방문객 필터링 (한국 시간 기준)
tz = pytz.timezone('Asia/Seoul')
today_str = datetime.now(tz).strftime("%Y-%m-%d")

records = sheet.get_all_records()
today_bookings = [row for row in records if str(row.get('방문 날짜', '')) == today_str]

# 4. 텔레그램 메시지 조립 및 발송
if not today_bookings:
    msg = f"🌅 [{today_str}] 오늘의 슈퍼멤버스 체험단\n\n오늘은 예약된 방문 일정이 없습니다! 🏖️"
else:
    today_bookings.sort(key=lambda x: str(x.get('방문 시간', ''))) # 시간순 정렬
    msg = f"🌅 [{today_str}] 오늘의 슈퍼멤버스 체험단\n총 {len(today_bookings)}팀 방문 예정입니다.\n\n"
    for idx, b in enumerate(today_bookings, 1):
        msg += f"{idx}. {b.get('방문 시간')} - {b.get('성함')} 님\n   (등급: {b.get('슈퍼멤버스 등급', b.get('등급', ''))} / 맛: {b.get('선택한 ', '')})\n\n"
    msg += "오늘 하루도 화이팅! 💪"

send_telegram(msg)
