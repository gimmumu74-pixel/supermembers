import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
from collections import Counter
import pandas as pd
import json
import os

# ==========================================
# 1. 환경 설정 (네 토큰 꼭 다시 넣어!)
# ==========================================
SHEET_NAME = '슈퍼멤버스' 
TELEGRAM_TOKEN = '8683541983:AAHNo1XHon2bQGW-dM-QUJx6OwTCepPuGOs'
CHAT_ID = '8928088522' 
ADMIN_PASSWORD = '123' 

# ==========================================
# 2. 구글 시트 연동 (클라우드/로컬 자동 인식)
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 내 컴퓨터에 파일이 있으면 파일을 읽고, 클라우드에서는 서버 금고를 읽음
    if os.path.exists('secrets.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
    else:
        key_dict = json.loads(st.secrets["gcp_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet.get_all_records(), sheet

records, sheet = load_data()

# 📌 아까 실수로 지워졌던 날짜 계산 코드가 바로 여기야!
booked_dates = [str(row.get('방문 날짜', '')) for row in records if row.get('방문 날짜', '') != '']
date_counts = Counter(booked_dates)
full_dates = [date for date, count in date_counts.items() if count >= 3]

# ==========================================
# 3. 메인 화면 & 예약 폼
# ==========================================
st.set_page_config(page_title="강릉샌드 체험단 예약", page_icon="🏖️")
st.title("🏖️ 강릉샌드 슈퍼멤버스 예약")
st.write("하루 최대 **3팀**까지만 예약을 받습니다.")

if full_dates:
    st.error(f"🚨 마감된 예약일: {', '.join(full_dates)}")

with st.expander("💡 [필독] 슈퍼멤버스 등급별 제공 내역", expanded=True):
    st.markdown("""
    - 🖤 **블랙** / ❤️ **레드 :** 강릉샌드 **2박스** 제공
    - 💛 **옐로우 :** 강릉샌드 **1박스** 제공
    """)

date = st.date_input("방문 날짜를 선택하세요")
date_str = date.strftime("%Y-%m-%d")

if date_str in full_dates:
    st.warning("해당 날짜는 이미 3팀 예약이 완료되어 예약할 수 없습니다. 다른 날짜를 골라주세요!")
else:
    tier = st.radio("슈퍼멤버스 등급을 선택해 주세요", ["블랙", "레드", "옐로우"])
    
    with st.form("reservation_form"):
        time = st.selectbox("방문 시간", ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        st.write("---")
        st.write("🎁 **원하시는 강릉샌드 맛을 선택해 주세요**")
        flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
        
        if tier in ["블랙", "레드"]:
            flavor1 = st.selectbox("첫 번째 박스 맛", flavors)
            flavor2 = st.selectbox("두 번째 박스 맛", flavors)
            flavor_text = f"{flavor1}, {flavor2}"
        else:
            flavor1 = st.selectbox("첫 번째 박스 맛", flavors)
            flavor_text = f"{flavor1}"
            
        st.write("---")
        name = st.text_input("성함")
        phone = st.text_input("연락처 (예: 01012345678)")
        submit = st.form_submit_button("예약하기")

    if submit:
        if not name or not phone:
            st.warning("성함과 연락처를 모두 입력해 주세요!")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, date_str, time, name, phone, tier, flavor_text])
            st.cache_data.clear() 
            
            message = f"🔔 [체험단 예약]\n- 날짜: {date_str} {time}\n- 등급: {tier}\n- 맛: {flavor_text}\n- 이름: {name}\n- 연락처: {phone}"
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": message})
            st.success("🎉 예약이 완료되었습니다! 매장에서 뵙겠습니다.")

# ==========================================
# 4. 📱 스마트폰에서 볼 수 있는 관리자 화면
# ==========================================
with st.sidebar:
    st.subheader("🕵️ 관리자 전용 메뉴")
    pw_input = st.text_input("비밀번호를 입력하세요", type="password")
    
    if pw_input == ADMIN_PASSWORD:
        st.success("인증 완료! 환영합니다, 대리님.")
        st.write("---")
        st.write("📌 **실시간 예약 현황**")
        
        if len(records) > 0:
            df = pd.DataFrame(records)
            show_df = df[['방문 날짜', '방문 시간', '성함', '연락처', '슈퍼멤버스 등급', '선택한 맛']].iloc[::-1]
            st.dataframe(show_df)
        else:
            st.write("아직 예약이 없습니다.")
