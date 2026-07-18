import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime, timedelta # 📌 시간 오차 보정용
from collections import Counter
import pandas as pd
import json
import os

# ==========================================
# 1. 설정
# ==========================================
SHEET_NAME = '슈퍼멤버스' 
TELEGRAM_TOKEN = '8683541983:AAHNo1XHon2bQGW-dM-QUJx6OwTCepPuGOs'
CHAT_ID = '8928088522' 
ADMIN_PASSWORD = '123' 

# 📌 전화번호를 제출할 때 확실하게 하이픈 넣기
def format_phone(phone_str):
    digits = ''.join(filter(str.isdigit, phone_str))
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits # 11자리/10자리가 아니면 그냥 원본 반환

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

@st.cache_data(ttl=30)
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
st.title("🏖️ 강릉샌드 슈퍼멤버스 예약")

# 📌 KST 강제 보정 (UTC + 9시간)
kst_now = datetime.utcnow() + timedelta(hours=9)
today = kst_now.date()

if full_dates:
    st.error(f"🚨 마감된 예약일: {', '.join(full_dates)}")

# 📌 min_value를 한국 시간 오늘로 고정
date = st.date_input("방문 날짜를 선택하세요", min_value=today)
date_str = date.strftime("%Y-%m-%d")

if date_str in full_dates:
    st.warning("해당 날짜는 예약이 마감되었습니다.")
else:
    tier = st.radio("슈퍼멤버스 등급", ["블랙", "레드", "옐로우"])
    with st.form("reservation_form"):
        time = st.selectbox("방문 시간", ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
        
        if tier in ["블랙", "레드"]:
            flavor_text = f"{st.selectbox('박스 1', flavors)}, {st.selectbox('박스 2', flavors)}"
        else:
            flavor_text = f"{st.selectbox('박스 1', flavors)}"
            
        name = st.text_input("성함")
        phone_input = st.text_input("연락처 (숫자만 입력하세요)")
        submit = st.form_submit_button("예약하기")

    if submit:
        if not name or not phone_input:
            st.warning("성함과 연락처를 모두 입력해 주세요!")
        else:
            formatted_phone = format_phone(phone_input)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, date_str, time, name, formatted_phone, tier, flavor_text])
            st.cache_data.clear()
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": f"🔔 예약: {date_str} {time}\n등급: {tier}\n이름: {name}\n연락처: {formatted_phone}"})
            st.success(f"🎉 예약 완료! ({formatted_phone})")
