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
ANNOUNCEMENT = "📢 [공지사항] 예약을 취소하시려면 하단 '예약 취소하기'를 이용해 주세요."
SHEET_NAME = '슈퍼멤버스' 
TELEGRAM_TOKEN = '8683541983:AAHNo1XHon2bQGW-dM-QUJx6OwTCepPuGOs'
CHAT_ID = '8928088522' 

def validate_and_format_phone(phone_str):
    digits = ''.join(filter(str.isdigit, phone_str))
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return None 

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

@st.cache_data(ttl=5)
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

tab1, tab2 = st.tabs(["📅 예약하기", "❌ 예약 취소하기"])

with tab1:
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
        # 📌 clear_on_submit=False로 바꿔서 제출 실패해도 내용 유지
        with st.form("reservation_form", clear_on_submit=False):
            time_options = ["11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00"]
            time = st.selectbox("방문 시간", time_options)
            flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
            flavor_text = f"{st.selectbox('박스 1', flavors)}, {st.selectbox('박스 2', flavors)}" if tier in ["블랙", "레드"] else f"{st.selectbox('박스 1', flavors)}"
            name = st.text_input("성함")
            phone_input = st.text_input("연락처 (010으로 시작하는 11자리 숫자)")
            submit = st.form_submit_button("예약하기")

        if submit:
            formatted_phone = validate_and_format_phone(phone_input)
            if not name or not formatted_phone:
                # 📌 워딩 부드럽게 수정
                st.warning("⚠️ 연락처 확인 부탁드립니다. (010으로 시작하는 11자리 숫자를 입력해 주세요)")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([now, date_str, time, name, formatted_phone, tier, flavor_text])
                st.cache_data.clear()
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": f"🔔 예약: {date_str} {time}\n등급: {tier}\n이름: {name}\n연락처: {formatted_phone}"})
                st.success(f"🎉 {name} 님, 예약이 완료되었습니다! ({formatted_phone})")
                # 📌 성공했을 때만 화면 새로고침해서 폼 비우기
                st.rerun()

with tab2:
    st.subheader("예약 취소")
    if 'cancel_phone_input' not in st.session_state:
        st.session_state.cancel_phone_input = ""
        
    cancel_phone = st.text_input("취소할 전화번호 입력 (010-XXXX-XXXX)", value=st.session_state.cancel_phone_input)
    st.session_state.cancel_phone_input = cancel_phone
    
    if st.button("예약 내역 조회"):
        formatted_cancel_phone = validate_and_format_phone(cancel_phone)
        if not formatted_cancel_phone:
            st.error("올바른 번호 형식이 아닙니다.")
        else:
            cell = sheet.find(formatted_cancel_phone)
            if cell:
                row_data = sheet.row_values(cell.row)
                st.session_state['cancel_info'] = {"row": cell.row, "data": row_data}
                st.info(f"확인된 예약: **{row_data[3]}** 님 (날짜: {row_data[1]} / 시간: {row_data[2]})")
            else:
                st.error("해당 번호로 된 예약 기록을 찾을 수 없습니다.")

    if 'cancel_info' in st.session_state:
        if st.button("진짜 취소하기"):
            sheet.delete_rows(st.session_state['cancel_info']['row'])
            st.cache_data.clear()
            del st.session_state['cancel_info']
            st.session_state.cancel_phone_input = ""
            st.success("예약이 성공적으로 취소되었습니다.")
            st.rerun()
