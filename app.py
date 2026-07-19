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
ANNOUNCEMENT = """
<div style="background-color: #F3EFE6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #d7ccc8;">
    <div style="text-align: center; font-weight: bold; font-size: 1.1em; color: #3E2723; margin-bottom: 12px;">
        📢 [필독] 공지사항
    </div>
    <ul style="color: #3E2723; margin-bottom: 0; padding-left: 20px; line-height: 1.6;">
        <li style="margin-bottom: 6px;">하루 최대 <strong>3팀</strong>까지만 예약을 받습니다!</li>
        <li>슈퍼멤버스 체험단은 <br><strong>[강릉샌드 본점]</strong>만 가능합니다!</li>
    </ul>
</div>
"""

SHEET_NAME = '슈퍼멤버스' 

TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"] 

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

# 📌 예약된 연락처 목록 추출 (중복 예약 방지용)
existing_phones = [str(row.get('연락처', '')) for row in records if row.get('연락처', '') != '']

# ==========================================
# 3. 메인 화면 및 스타일 설정
# ==========================================
st.set_page_config(page_title="강릉샌드 체험단 예약", page_icon="🏖️")

st.markdown("""
    <style>
    .stMarkdown, .stAlert, h1, h2, h3, p, span, li {
        word-break: keep-all !important;
    }
    [data-testid="stHeader"] {display: none !important;}
    footer {display: none !important;}
    .viewerBadge_container {display: none !important;}
    </style>
""", unsafe_allow_html=True)

st.markdown(ANNOUNCEMENT, unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>[강릉샌드 본점] 슈퍼멤버스 예약</h1>", unsafe_allow_html=True)

# ==========================================
# 📌 변수 발생 시 화면 전환 로직
# ==========================================
if 'booking_success' in st.session_state and st.session_state.booking_success:
    st.balloons() 
    st.success(f"🎉 **{st.session_state.success_name}** 님, 예약이 정상적으로 완료되었습니다!")
    st.markdown(f"""
    ### 📅 예약 확정 상세 내역
    *   **방문 날짜 :** {st.session_state.success_date}
    *   **방문 시간 :** {st.session_state.success_time}
    *   **선택 등급 :** {st.session_state.success_tier}
    *   **선택 구성 :** {st.session_state.success_flavor}
    ---
    📍 **매장 방문 시 안내**  
    카운터에서 직원에게 **[슈퍼멤버스]**라고 말씀해 주시면 빠른 안내 도와드릴게요!  
    조심히 오세요! 매장에서 뵙겠습니다. 😊
    """)
    if st.button("🏠 처음으로 돌아가기", key="btn_b_home"):
        del st.session_state.booking_success
        st.rerun()
    st.stop()

if 'cancel_success' in st.session_state and st.session_state.cancel_success:
    st.warning("❌ 예약 취소가 정상적으로 완료되었습니다.")
    st.markdown(f"""
    ### 🗑️ 취소된 예약 내역
    *   **예약자 성함 :** {st.session_state.c_success_name} 님
    *   **취소된 일정 :** {st.session_state.c_success_date} ({st.session_state.c_success_time})
    ---
    다음에 더 좋은 기회로 만나 뵙기를 기대하겠습니다! 감사합니다! 🏖️
    """)
    if st.button("🏠 처음으로 돌아가기", key="btn_c_home"):
        del st.session_state.cancel_success
        st.rerun()
    st.stop()

# ==========================================
# 1) 매장 안내 폴더
# ==========================================
with st.expander("ℹ️ [공식] 매장 안내 및 주의사항", expanded=False):
    st.markdown("""
    ### 🏖️ [강릉샌드 본점] 체험단 방문 안내

    안녕하세요! 
    
    강릉시 관광기념품 공모전 금상 수상작 강릉샌드입니다!
    
    방문 해주셔서 정말 감사합니다. :)

    **⚠️ 포스팅 전 꼭 확인해 주세요 (오리뷰 방지)**
    현재 네이버나 구글에 '강릉샌드 본점'을 검색하면 유사업체가 함께 노출되어 혼선이 많습니다.
    
    쿠키 겉면에 "강릉샌드" 글자가 각인된 것이 저희 매장의 진짜 시그니처입니다!

    번거로우시겠지만, 아래의 공식 주소를 꼭 확인하여 리뷰 등록 부탁드립니다!

    **🏠 공식 매장**
    - 강릉샌드 본점 : 강릉시 성곡고양길5번안길 31
    - 강릉샌드 월화점 : 강릉시 금성로12번길 6
    - 강릉샌드 초당점 : 강릉시 난설헌로 249
    - 강릉샌드 쿠키랩 : 강릉시 남구길30번길 23
    """)

# ==========================================
# 2) 예약하기 폴더
# ==========================================
with st.expander("📅 예약하기", expanded=False):
    st.markdown("""
    #### 📌 슈퍼멤버스 등급별 혜택
    *   🖤 **블랙** / ❤️ **레드** : 강릉샌드 **2박스** 제공
    *   💛 **옐로우** : 강릉샌드 **1박스** 제공
    
    ※ 방문 전, 상단 **[매장 안내 및 주의사항]**을 꼭 읽어주세요!
    """)
    st.write("---")

    # 📌 마감된 예약일 가독성 개선 (정렬 및 줄바꿈 적용)
    if full_dates:
        sorted_full_dates = sorted(full_dates)
        dates_list_str = "\n".join([f"• {d}" for d in sorted_full_dates])
        st.error(f"🚨 **마감된 예약일**\n{dates_list_str}")

    kst_now = datetime.utcnow() + timedelta(hours=9)
    today = kst_now.date()
    date = st.date_input("방문 날짜를 선택하세요", min_value=today)
    date_str = date.strftime("%Y-%m-%d")

    if date_str in full_dates:
        st.warning("해당 날짜는 예약이 마감되었습니다.")
    else:
        tier = st.radio("슈퍼멤버스 등급", ["블랙", "레드", "옐로우"])
        with st.form("reservation_form", clear_on_submit=False):
            time_options = ["11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00"]
            time = st.selectbox("방문 시간", time_options)
            flavors = ["커피", "옥수수", "곶감", "흑임자", "딸기", "고구마"]
            flavor_text = f"{st.selectbox('박스 1', flavors)}, {st.selectbox('박스 2', flavors)}" if tier in ["블랙", "레드"] else f"{st.selectbox('박스 1', flavors)}"
            name = st.text_input("성함")
            phone_input = st.text_input("연락처 (010-XXXX-XXXX)")
            
            st.markdown("""
            <div style="font-size: 0.8em; color: #666; margin: 15px 0 10px 0; text-align: center;">
            ※ 예약 버튼 클릭 시, 예약 진행 및 노쇼 방지를 위한<br>개인정보(성함, 연락처) 수집·이용에 동의한 것으로 간주합니다.
            </div>
            """, unsafe_allow_html=True)
            
            submit = st.form_submit_button("예약하기")

        if submit:
            formatted_phone = validate_and_format_phone(phone_input)
            if not name or not formatted_phone:
                st.warning("⚠️ 연락처 확인 부탁드립니다.")
            elif formatted_phone in existing_phones:  # 📌 중복 예약 방지 로직
                st.error("⚠️ 이미 예약된 내역이 있는 연락처입니다. 1인당 1회만 예약 가능합니다.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([now, date_str, time, name, formatted_phone, tier, flavor_text])
                st.cache_data.clear()
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": f"🔔 예약: {date_str} {time}\n등급: {tier}\n이름: {name}\n연락처: {formatted_phone}"})
                
                st.session_state.booking_success = True
                st.session_state.success_name = name
                st.session_state.success_date = date_str
                st.session_state.success_time = time
                st.session_state.success_tier = tier
                st.session_state.success_flavor = flavor_text
                st.rerun()

# ==========================================
# 3) 예약 취소 폴더
# ==========================================
with st.expander("❌ 예약 취소하기", expanded=False):
    st.markdown("""
    **⚠️ 예약 취소 및 노쇼 안내**  
    예약 당일 급작스러운 취소나 사전 연락 없는 노쇼(No-Show) 발생 시, 
    추후 [강릉샌드 본점] 체험단 진행에 불이익이 있을 수 있습니다. 
    일정 변경이나 취소가 필요하신 경우 반드시 미리 진행해 주세요!
    """)
    st.write("---")

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
        if st.button("예약 취소"):
            row_data = st.session_state['cancel_info']['data']
            c_name = row_data[3]
            c_date = row_data[1]
            c_time = row_data[2]
            c_phone = row_data[4]
            c_tier = row_data[5]

            sheet.delete_rows(st.session_state['cancel_info']['row'])
            st.cache_data.clear()
            
            cancel_msg = f"🚨 [취소 알림] 예약이 취소되었습니다!\n이름: {c_name}\n날짜: {c_date}\n시간: {c_time}\n등급: {c_tier}\n연락처: {c_phone}"
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": cancel_msg})
            
            st.session_state.cancel_success = True
            st.session_state.c_success_name = c_name
            st.session_state.c_success_date = c_date
            st.session_state.c_success_time = c_time
            
            del st.session_state['cancel_info']
            st.session_state.cancel_phone_input = ""
            st.rerun()
