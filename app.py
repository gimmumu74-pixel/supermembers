import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime, date
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

# 📌 전화번호 하이픈 자동 변환 함수
def format_phone(phone_str):
    digits = ''.join(filter(str.isdigit, phone_str))
    if len(digits) >= 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:11]}"
    elif len(digits) >= 7:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return digits

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

if full_dates:
    st.error(f"🚨 마감된 예약일: {', '.join(full_dates)}")

# 📌 min_value=date.today() 를 통해 오늘 이전 날짜 선택 차단
date = st.date_input("방문 날짜를 선택하세요", min_value=date.today())
date_str = date.strftime("%Y-%m-%d")

if date_str in full_dates:
    st.warning("해당 날짜는 예약이 마감되었습니다.")
else:
    tier = st.radio("슈퍼멤버스 등급", ["블랙", "레드", "옐로우"])
    with st.form("reservation_form"):
        time = st.selectbox("방문 시간", ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
        flavor_text = f"{st.selectbox('박스 1', flavors)}, {st.selectbox('박스 2', flavors)}" if tier in ["블랙", "레드"] else f"{st.selectbox('박스 1', flavors)}"
        name = st.text_input("성함")
        phone_input = st.text_input("연락처 (숫자만 입력하면 자동으로 정리돼요)")
        submit = st.form_submit_button("예약하기")

    if submit:
        if not name or not phone_input:
            st.warning("성함과 연락처를 모두 입력해 주세요!")
        else:
            formatted_phone = format_phone(phone_input)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, date_str, time, name, formatted_phone, tier, flavor_text])
            st.cache_data.clear()
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": f"🔔 예약: {date_str} {time}\n등급: {tier}\n이름: {name}\n연락처: {formatted_phone}"})
            st.success(f"🎉 예약 완료! ({formatted_phone})")
