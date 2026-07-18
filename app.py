import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime, timedelta
from collections import Counter
import json
import os

# ==========================================
# 1. 설정
# ==========================================
ANNOUNCEMENT = "📢 [공지사항] 예약을 취소하시려면 아래 '예약 취소하기'를 이용해 주세요."
SHEET_NAME = '슈퍼멤버스' 
TELEGRAM_TOKEN = '8683541983:AAHNo1XHon2bQGW-dM-QUJx6OwTCepPuGOs'
CHAT_ID = '8928088522' 

# 전화번호 검증 및 하이픈 삽입
def format_phone(phone_str):
    digits = ''.join(filter(str.isdigit, phone_str))
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return None # 10~11자리가 아니면 None 반환

# ==========================================
# 2. 구글 시트 연동
# ==========================================
@st.cache_resource
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = json.loads(st.secrets["gcp_json"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

sheet = get_sheet()

@st.cache_data(ttl=10) # 취소 기능 때문에 캐시 시간을 짧게 줄임
def get_records():
    return get_sheet().get_all_records()

records = get_records()
booked_dates = [str(row.get('방문 날짜', '')) for row in records if row.get('방문 날짜', '') != '']
date_counts = Counter(booked_dates)
full_dates = [date for date, count in date_counts.items() if count >= 3]

# ==========================================
# 3. 메인 화면
# ==========================================
st.set_page_config(page_title="강릉샌드 체험단 예약", page_icon="🏖️")
st.info(ANNOUNCEMENT)
st.title("🏖️ 강릉샌드 슈퍼멤버스 예약")

# 예약 폼
if full_dates:
    st.error(f"🚨 마감된 예약일: {', '.join(full_dates)}")

kst_now = datetime.utcnow() + timedelta(hours=9)
today = kst_now.date()
date = st.date_input("방문 날짜를 선택하세요", min_value=today)
date_str = date.strftime("%Y-%m-%d")

if date_str in full_dates:
    st.warning("해당 날짜는 예약이 마감되었습니다.")
else:
    tier = st.radio("슈퍼멤버스 등급", ["블랙", "레드", "옐로우"])
    with st.form("reservation_form", clear_on_submit=True):
        time = st.selectbox("방문 시간", ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
        flavor_text = f"{st.selectbox('박스 1', flavors)}, {st.selectbox('박스 2', flavors)}" if tier in ["블랙", "레드"] else f"{st.selectbox('박스 1', flavors)}"
        name = st.text_input("성함")
        phone_input = st.text_input("연락처 (숫자만 입력)")
        submit = st.form_submit_button("예약하기")

    if submit:
        formatted_phone = format_phone(phone_input)
        if not name or not formatted_phone:
            st.warning("성함 확인 및 연락처(10~11자리 숫자)를 정확히 입력해 주세요!")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, date_str, time, name, formatted_phone, tier, flavor_text])
            st.cache_data.clear()
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": f"🔔 예약: {date_str} {time}\n등급: {tier}\n이름: {name}\n연락처: {formatted_phone}"})
            st.success(f"🎉 예약 완료! ({formatted_phone})")

# ==========================================
# 4. 예약 취소 기능
# ==========================================
st.write("---")
with st.expander("❌ 예약 취소하기"):
    cancel_phone = st.text_input("예약 시 사용한 전화번호 입력")
    if st.button("취소 실행"):
        cell = sheet.find(cancel_phone)
        if cell:
            sheet.delete_rows(cell.row)
            st.cache_data.clear()
            st.success("예약이 성공적으로 취소되었습니다.")
        else:
            st.error("해당 번호로 된 예약 기록을 찾을 수 없습니다.")
