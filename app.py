import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import jdatetime
from datetime import time, date
import json
import os
import uuid
from io import BytesIO

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(
    page_title="Task Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ======================
# CUSTOM CSS
# ======================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background-color: #f8fafc;
    }
    .upload-box {
        border: 3px dashed #60A5FA;
        border-radius: 15px;
        padding: 3rem;
        text-align: center;
        background-color: #f0f9ff;
        margin: 2rem auto;
        max-width: 600px;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #3B82F6;
    }
    .quest-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 5px solid #10B981;
    }
    .success-badge {
        background-color: #10B981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        display: inline-block;
    }
    .pending-badge {
        background-color: #F59E0B;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        display: inline-block;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ======================
# SESSION STATE
# ======================
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

if "df_clean" not in st.session_state:
    st.session_state.df_clean = None

if "holidays" not in st.session_state:
    st.session_state.holidays = []

if "active_page" not in st.session_state:
    st.session_state.active_page = "landing"

if "trend_filters" not in st.session_state:
    st.session_state.trend_filters = {
        "selected_kpi": "Ghorme Sabzi",
        "time_range": "Monthly"
    }

if "show_upload_modal" not in st.session_state:
    st.session_state.show_upload_modal = False

# ======================
# QUEST STORAGE
# ======================
QUEST_FILE = "quests.json"

def load_quests():
    if not os.path.exists(QUEST_FILE):
        return []
    try:
        with open(QUEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_quests(data):
    with open(QUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ======================
# HELPER FUNCTIONS
# ======================
def jalali_to_gregorian(val):
    try:
        if pd.isna(val):
            return None
        y, m, d = map(int, str(val).split("/"))
        return jdatetime.date(y, m, d).togregorian()
    except:
        return None

def normalize_customer(val):
    if pd.isna(val):
        return val
    val = str(val)
    if "سرگرمی" in val:
        return "Entertainment"
    if "موزیک" in val or "ميوزيک" in val:
        return "Music"
    if "موویز" in val or "موويز" in val or "movies" in val.lower():
        return "Movies"
    if "صراط" in val:
        return "Serat"
    return val

def normalize_designer(val):
    mapping = {
        "ملیکا عرب زاده": "Melika",
        "ملیکا عرب‌زاده": "Melika",
        "رومینا": "Romina",
        "سجاد": "Sajad",
        "فاطمه": "Fatemeh"
    }
    return mapping.get(str(val).strip(), val)

def clean_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    drop_letters = ["B","E","F","G","H","I","L","R","S","T","U"]
    drop_indexes = [
        ord(l) - ord("A")
        for l in drop_letters
        if ord(l) - ord("A") < len(df.columns)
    ]
    df.drop(df.columns[drop_indexes], axis=1, inplace=True)

    rename_map = {
        "شماره بریف": "Brief Number",
        "نام طراح": "Designer Name",
        "درخواست کننده": "Customer",
        "درخواست‌کننده": "Customer",
        "تاریخ ددلاین": "Deadline - date",
        "ساعت ددلاین": "Hour",
        "نوع کاور": "Type",
        "تعداد ویرایش": "Edit count",
        "علت ویرایش": "Reason",
        "زمان ثبت بریف - تاریخ": "Submission date",
        "زمان ثبت بریف - ساعت": "Submission hour"
    }

    df = df.rename(columns=lambda x: rename_map.get(x, x))
    df["Designer Name"] = df["Designer Name"].apply(normalize_designer)
    df["Customer"] = df["Customer"].apply(normalize_customer)
    df["Deadline - date"] = df["Deadline - date"].apply(jalali_to_gregorian)

    replace_map = {
        "سبز": "Ghorme Sabzi",
        "قرمز": "Omlet",
        "زرد": "Burger",
        "ایراد طراح": "Designer Error",
        "ایراد سفارش دهنده": "Customer Error",
        "سلیقه": "Taste",
        "تیم لید: سلیقه": "Team-lead: Taste",
        "تیم لید: ایراد طراح": "Team-lead: Designer Error",
        "تیم لید: ایراد سفارش دهنده": "Team-lead: Customer Error"
    }

    for col in ["Type", "Reason"]:
        df[col] = df[col].replace(replace_map)

    df["Submission date"] = pd.to_datetime(df["Submission date"], errors="coerce")
    df["Submission hour"] = pd.to_datetime(df["Submission hour"], errors="coerce").dt.time

    return df

def pie_chart(title, value, total, color):
    fig = px.pie(
        names=[title, "Others"],
        values=[value, max(total - value, 0)],
        hole=0.45,
        color_discrete_sequence=[color, "#ECECEC"]
    )
    fig.update_traces(textinfo="percent+value", pull=[0.07, 0])
    fig.update_layout(showlegend=False, height=260)
    return fig

def get_kpi_options():
    return {
        "Ghorme Sabzi": {"emoji": "🥬", "color": "#2ECC71"},
        "Omlet": {"emoji": "🥚", "color": "#F1C40F"},
        "Burger": {"emoji": "🍔", "color": "#E67E22"},
        "Error Rate": {"emoji": "❌", "color": "#E74C3C"},
        "Edits > 2": {"emoji": "🔁", "color": "#8E44AD"},
        "Late Submissions": {"emoji": "⏰", "color": "#34495E"}
    }

def calculate_kpi(df, kpi_name, holidays):
    if kpi_name == "Ghorme Sabzi":
        return (df["Type"] == "Ghorme Sabzi").sum()
    elif kpi_name == "Omlet":
        return (df["Type"] == "Omlet").sum()
    elif kpi_name == "Burger":
        return (df["Type"] == "Burger").sum()
    elif kpi_name == "Error Rate":
        return df["Reason"].isin(["Designer Error", "Team-lead: Designer Error"]).sum()
    elif kpi_name == "Edits > 2":
        return (df["Edit count"] >= 2).sum()
    elif kpi_name == "Late Submissions":
        late_condition = (df["Submission hour"] >= time(18, 0)) | (df["Submission date"].dt.date.isin(holidays))
        return df[late_condition].shape[0]
    return 0

def create_trend_chart(df, kpi_name, time_range, holidays):
    """ایجاد نمودار خطی روند"""
    kpi_options = get_kpi_options()
    emoji = kpi_options[kpi_name]["emoji"]
    color = kpi_options[kpi_name]["color"]
    
    df = df.copy()
    df["year_month"] = df["Submission date"].dt.to_period("M")
    
    time_range_titles = {
        "Monthly": "ماه گذشته (روزانه)",
        "Annually": "یک سال گذشته (ماهانه)",
        "All time": "کل زمان (ماهانه)"
    }
    
    if time_range == "Monthly":
        end_date = df["Submission date"].max()
        start_date = end_date - pd.Timedelta(days=30)
        df_period = df[df["Submission date"] >= start_date]
        
        if df_period.empty:
            return None
        
        daily_data = []
        current_date = start_date.date()
        
        while current_date <= end_date.date():
            day_data = df_period[df_period["Submission date"].dt.date == current_date]
            value = calculate_kpi(day_data, kpi_name, holidays)
            daily_data.append({
                "date": current_date,
                "value": value,
                "label": current_date.strftime("%Y-%m-%d")
            })
            current_date += pd.Timedelta(days=1)
        
        trend_df = pd.DataFrame(daily_data)
        
        fig = px.line(
            trend_df,
            x="label",
            y="value",
            title=f"{emoji} {kpi_name} Trend - {time_range_titles[time_range]}",
            color_discrete_sequence=[color]
        )
        
        fig.update_xaxes(title_text="روز")
        
    else:
        if time_range == "Annually":
            end_date = df["Submission date"].max()
            start_date = end_date - pd.DateOffset(months=11)
            df_period = df[df["Submission date"] >= start_date]
            time_title = time_range_titles["Annually"]
        else:
            df_period = df
            time_title = time_range_titles["All time"]
        
        if df_period.empty:
            return None
        
        monthly_data = df_period.groupby("year_month").apply(
            lambda x: calculate_kpi(x, kpi_name, holidays)
        ).reset_index(name="value")
        
        monthly_data["label"] = monthly_data["year_month"].dt.strftime("%Y-%m")
        
        fig = px.line(
            monthly_data,
            x="label",
            y="value",
            title=f"{emoji} {kpi_name} Trend - {time_title}",
            color_discrete_sequence=[color]
        )
        
        fig.update_xaxes(title_text="ماه")
    
    fig.update_layout(
        yaxis_title="تعداد",
        hovermode="x unified",
        height=500,
        showlegend=False
    )
    
    fig.update_traces(
        mode="lines+markers",
        marker=dict(size=8),
        line=dict(width=3)
    )
    
    return fig

# ======================
# AUTHENTICATION
# ======================
def show_login_page():
    """صفحه لاگین"""
    st.markdown('<h1 class="main-header">📊 Task Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 🔐 ورود به سیستم")
            st.markdown("لطفاً اطلاعات کاربری خود را وارد کنید")
            
            username = st.selectbox(
                "👤 نام کاربری",
                options=["انتخاب کنید", "Sajad", "Romina", "Melika", "Fatemeh"]
            )
            
            password = st.text_input("🔑 رمز عبور", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.button("🚀 ورود", type="primary", use_container_width=True)
            with col_btn2:
                clear_btn = st.button("🔄 پاک کردن", use_container_width=True)
            
            if login_btn:
                if username == "انتخاب کنید":
                    st.error("❌ لطفاً نام کاربری را انتخاب کنید")
                else:
                    passwords = {
                        "Sajad": "2232245",
                        "Romina": "112131",
                        "Melika": "122232",
                        "Fatemeh": "132333"
                    }
                    
                    if password == passwords.get(username, ""):
                        st.session_state.current_user = username
                        st.session_state.is_authenticated = True
                        st.session_state.active_page = "kpi"
                        st.success(f"✅ خوش آمدید {username}!")
                        st.rerun()
                    else:
                        st.error("❌ نام کاربری یا رمز عبور اشتباه است")
            
            if clear_btn:
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# ======================
# SIDEBAR
# ======================
def render_sidebar():
    """سایدبار اصلی بعد از لاگین"""
    with st.sidebar:
        st.markdown(f"### 👋 سلام {st.session_state.current_user}!")
        st.markdown("---")
        
        menu_options = [
            ("📊 KPI", "kpi"),
            ("🗡️ Quests", "quests"),
            ("📈 Trend", "trend")
        ]
        
        for emoji_text, page_key in menu_options:
            if st.button(emoji_text, use_container_width=True, 
                        type="primary" if st.session_state.active_page == page_key else "secondary"):
                st.session_state.active_page = page_key
                st.rerun()
        
        st.markdown("---")
        
        if st.button("🚪 خروج از سیستم", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.is_authenticated = False
            st.session_state.active_page = "landing"
            st.session_state.df_clean = None
            st.session_state.holidays = []
            st.rerun()

# ======================
# KPI PAGE
# ======================
def render_kpi_page():
    """صفحه KPI"""
    st.markdown('<h1 class="main-header">📊 KPI Dashboard</h1>', unsafe_allow_html=True)
    
    # نمایش باکس آپلود اگر داده‌ای وجود ندارد
    if st.session_state.df_clean is None:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.markdown("### 📁 آپلود فایل اکسل")
        st.markdown("لطفاً فایل اکسل را در اینجا رها کنید یا از دستگاه انتخاب کنید")
        
        uploaded_file = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            with st.spinner("🔄 در حال پردازش فایل..."):
                st.session_state.df_clean = clean_excel(uploaded_file)
                st.success("✅ فایل با موفقیت آپلود و پردازش شد!")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # اگر داده وجود دارد، نمایش KPI
    df_all = st.session_state.df_clean.copy()
    
    # تنظیمات بازه زمانی و تعطیلات
    st.markdown("### ⚙️ تنظیمات")
    col1, col2 = st.columns(2)
    
    with col1:
        min_d = df_all["Submission date"].min()
        max_d = df_all["Submission date"].max()
        start_date, end_date = st.date_input(
            "📅 بازه تحلیل",
            value=(min_d, max_d),
            key="date_range_kpi"
        )
    
    with col2:
        selected_day = st.date_input("📌 روز تعطیل", value=None, key="holiday_day")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ افزودن تعطیل", use_container_width=True):
                if selected_day and selected_day not in st.session_state.holidays:
                    st.session_state.holidays.append(selected_day)
                    st.success(f"✅ {selected_day} به تعطیلات اضافه شد")
                    st.rerun()
        
        with col_btn2:
            if st.button("🗑️ حذف تعطیلات", use_container_width=True):
                if st.session_state.holidays:
                    st.session_state.holidays = []
                    st.success("✅ همه تعطیلات حذف شدند")
                    st.rerun()
    
    # نمایش تعطیلات فعلی
    if st.session_state.holidays:
        st.info(f"📋 تعطیلات ثبت شده: {', '.join([str(d) for d in st.session_state.holidays])}")
    
    # فیلتر داده‌ها بر اساس بازه زمانی
    df_filtered = df_all[
        (df_all["Submission date"] >= pd.to_datetime(start_date)) &
        (df_all["Submission date"] <= pd.to_datetime(end_date))
    ]
    
    # انتخاب KPI برای نمایش
    kpi_options = get_kpi_options()
    
    # تب‌های مختلف برای هر طراح
    if st.session_state.current_user == "Sajad":
        # سجاد همه را می‌بیند
        tab_names = ["Team KPI", "Sajad KPI", "Romina KPI", "Melika KPI", "Fatemeh KPI"]
        tab_designers = [None, "Sajad", "Romina", "Melika", "Fatemeh"]
    else:
        # دیگران فقط تیم و خودشان را می‌بینند
        tab_names = ["Team KPI", f"{st.session_state.current_user} KPI"]
        tab_designers = [None, st.session_state.current_user]
    
    tabs = st.tabs([f"**{name}**" for name in tab_names])
    
    for idx, (tab, designer) in enumerate(zip(tabs, tab_designers)):
        with tab:
            if designer is None:
                df_to_show = df_filtered
                title = "تیم"
            else:
                df_to_show = df_filtered[df_filtered["Designer Name"] == designer]
                title = designer
            
            total = len(df_to_show)
            
            if total == 0:
                st.warning(f"⚠️ هیچ داده‌ای برای {title} در این بازه زمانی یافت نشد")
                continue
            
            # محاسبه KPIها
            ghorme = (df_to_show["Type"] == "Ghorme Sabzi").sum()
            omlet = (df_to_show["Type"] == "Omlet").sum()
            burger = (df_to_show["Type"] == "Burger").sum()
            designer_error = df_to_show["Reason"].isin(["Designer Error", "Team-lead: Designer Error"]).sum()
            revision_2 = (df_to_show["Edit count"] >= 2).sum()
            late = df_to_show[(df_to_show["Submission hour"] >= time(18, 0)) | 
                              (df_to_show["Submission date"].dt.date.isin(st.session_state.holidays))].shape[0]
            
            # نمایش KPIها در دو ردیف
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🥬 Ghorme Sabzi", f"{ghorme}", f"{ghorme/total*100:.1f}%")
                st.plotly_chart(pie_chart("Ghorme Sabzi", ghorme, total, "#2ECC71"), 
                              use_container_width=True, config={'displayModeBar': False})
            
            with col2:
                st.metric("🥚 Omlet", f"{omlet}", f"{omlet/total*100:.1f}%")
                st.plotly_chart(pie_chart("Omlet", omlet, total, "#F1C40F"), 
                              use_container_width=True, config={'displayModeBar': False})
            
            with col3:
                st.metric("🍔 Burger", f"{burger}", f"{burger/total*100:.1f}%")
                st.plotly_chart(pie_chart("Burger", burger, total, "#E67E22"), 
                              use_container_width=True, config={'displayModeBar': False})
            
            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("❌ Designer Error", f"{designer_error}", f"{designer_error/total*100:.1f}%")
                st.plotly_chart(pie_chart("Designer Error", designer_error, total, "#E74C3C"), 
                              use_container_width=True, config={'displayModeBar': False})
            
            with col5:
                st.metric("🔁 Edits > 2", f"{revision_2}", f"{revision_2/total*100:.1f}%")
                st.plotly_chart(pie_chart("2+ Revisions", revision_2, total, "#8E44AD"), 
                              use_container_width=True, config={'displayModeBar': False})
            
            with col6:
                st.metric("⏰ Late Submissions", f"{late}", f"{late/total*100:.1f}%")
                st.plotly_chart(pie_chart("Late", late, total, "#34495E"), 
                              use_container_width=True, config={'displayModeBar': False})
    
    # دکمه آپلود مجدد در پایین صفحه
    st.markdown("---")
    if st.button("📤 آپلود فایل اکسل جدید", use_container_width=True):
        st.session_state.show_upload_modal = True
    
    # مودال آپلود مجدد
    if st.session_state.show_upload_modal:
        with st.container():
            st.markdown("""
            <style>
            .modal {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                z-index: 1000;
                width: 90%;
                max-width: 500px;
            }
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                z-index: 999;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown('<div class="modal">', unsafe_allow_html=True)
                st.markdown("### 📁 آپلود فایل جدید")
                
                new_file = st.file_uploader("فایل اکسل را انتخاب کنید", type=["xlsx"], 
                                          key="modal_uploader")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ تایید", use_container_width=True):
                        if new_file is not None:
                            st.session_state.df_clean = clean_excel(new_file)
                            st.session_state.show_upload_modal = False
                            st.success("✅ فایل جدید با موفقیت آپلود شد!")
                            st.rerun()
                
                with col_btn2:
                    if st.button("❌ لغو", use_container_width=True):
                        st.session_state.show_upload_modal = False
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

# ======================
# QUESTS PAGE
# ======================
def render_quests_page():
    """صفحه کوئست‌ها"""
    st.markdown('<h1 class="main-header">🗡️ Quest Management</h1>', unsafe_allow_html=True)
    
    quests = load_quests()
    
    if st.session_state.current_user == "Sajad":
        # سجاد - داشبورد کامل
        tab1, tab2, tab3 = st.tabs(["➕ New Quest", "📜 All Quests", "🎯 My Quests"])
        
        with tab1:
            st.markdown("### 🆕 ایجاد کوئست جدید")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("📝 نام کوئست")
                description = st.text_area("📋 توضیحات")
            
            with col2:
                deadline = st.date_input("📅 ددلاین", value=date.today())
                owner = st.selectbox("👤 واگذار به", ["Sajad", "Romina", "Melika", "Fatemeh"])
            
            if st.button("✅ ایجاد کوئست", type="primary", use_container_width=True):
                if name and description:
                    quests.append({
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "description": description,
                        "deadline": str(deadline),
                        "owner": owner,
                        "done": False,
                        "created_by": st.session_state.current_user,
                        "created_at": str(date.today())
                    })
                    save_quests(quests)
                    st.success("✅ کوئست جدید با موفقیت ایجاد شد!")
                    st.rerun()
                else:
                    st.error("❌ لطفاً نام و توضیحات کوئست را وارد کنید")
        
        with tab2:
            st.markdown("### 📋 همه کوئست‌ها")
            
            filter_owner = st.selectbox("فیلتر بر اساس صاحب", 
                                       ["همه", "Sajad", "Romina", "Melika", "Fatemeh"])
            
            filtered_quests = quests if filter_owner == "همه" else [q for q in quests if q["owner"] == filter_owner]
            
            if not filtered_quests:
                st.info("📭 هیچ کوئستی یافت نشد")
            else:
                for q in filtered_quests:
                    with st.container():
                        st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"#### {q['name']}")
                            st.caption(q["description"])
                            st.markdown(f"**📅 ددلاین:** {q['deadline']} | **👤 صاحب:** {q['owner']}")
                        
                        with col2:
                            status = "✅ انجام شده" if q["done"] else "🔄 در حال انجام"
                            st.markdown(f"**وضعیت:** {status}")
                        
                        with col3:
                            col_edit, col_del = st.columns(2)
                            with col_edit:
                                if st.button("✏️", key=f"edit_{q['id']}"):
                                    # اینجا می‌توانی مودال ویرایش اضافه کنی
                                    st.info("ویژگی ویرایش به زودی اضافه می‌شود")
                            
                            with col_del:
                                if st.button("🗑️", key=f"del_{q['id']}"):
                                    quests.remove(q)
                                    save_quests(quests)
                                    st.success("✅ کوئست حذف شد")
                                    st.rerun()
                        
                        st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown("### 🎯 کوئست‌های من")
            my_quests = [q for q in quests if q["owner"] == "Sajad"]
            
            if not my_quests:
                st.info("📭 هیچ کوئستی برای شما ایجاد نشده است")
            else:
                for q in my_quests:
                    with st.container():
                        st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                        
                        st.markdown(f"#### {q['name']}")
                        st.caption(q["description"])
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**📅 ددلاین:** {q['deadline']}")
                        
                        with col2:
                            if q["done"]:
                                st.markdown('<span class="success-badge">✅ انجام شده</span>', unsafe_allow_html=True)
                            else:
                                st.markdown('<span class="pending-badge">🔄 در حال انجام</span>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # دیگر کاربران - فقط کوئست‌های خودشان
        st.markdown(f"### 🎯 کوئست‌های {st.session_state.current_user}")
        
        user_quests = [q for q in quests if q["owner"] == st.session_state.current_user]
        
        if not user_quests:
            st.info("📭 هیچ کوئستی برای شما ایجاد نشده است")
        else:
            for q in user_quests:
                with st.container():
                    st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {q['name']}")
                    st.caption(q["description"])
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**📅 ددلاین:** {q['deadline']}")
                        if "created_by" in q:
                            st.caption(f"ایجاد شده توسط: {q['created_by']}")
                    
                    with col2:
                        if q["done"]:
                            st.markdown('<span class="success-badge">✅ انجام شده</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="pending-badge">🔄 در حال انجام</span>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# ======================
# TREND PAGE
# ======================
def render_trend_page():
    """صفحه تحلیل روند"""
    st.markdown('<h1 class="main-header">📈 Trend Analysis</h1>', unsafe_allow_html=True)
    
    if st.session_state.df_clean is None:
        st.warning("⚠️ لطفاً ابتدا از صفحه KPI یک فایل اکسل آپلود کنید")
        return
    
    df_all = st.session_state.df_clean.copy()
    
    # فیلترهای بالای صفحه
    col1, col2, col3 = st.columns(3)
    
    with col1:
        kpi_options = get_kpi_options()
        selected_kpi = st.selectbox(
            "📊 Select KPI",
            options=list(kpi_options.keys()),
            index=list(kpi_options.keys()).index(st.session_state.trend_filters["selected_kpi"])
        )
        st.session_state.trend_filters["selected_kpi"] = selected_kpi
    
    with col2:
        time_options = ["Monthly", "Annually", "All time"]
        selected_time = st.selectbox(
            "📅 Time Range",
            options=time_options,
            index=time_options.index(st.session_state.trend_filters["time_range"])
        )
        st.session_state.trend_filters["time_range"] = selected_time
    
    with col3:
        # تعیین اینکه چه داده‌هایی نمایش داده شود
        if st.session_state.current_user == "Sajad":
            # سجاد همه را می‌بیند
            view_options = ["Team Only", "All Designers", "Sajad Only", "Romina Only", "Melika Only", "Fatemeh Only"]
            selected_view = st.selectbox("👀 View", options=view_options)
        else:
            # دیگران فقط تیم و خودشان را می‌بینند
            view_options = ["Team Only", f"{st.session_state.current_user} Only"]
            selected_view = st.selectbox("👀 View", options=view_options)
    
    # ایجاد نمودارها
    holidays = st.session_state.holidays
    
    if selected_view == "Team Only" or selected_view == "All Designers":
        # نمودار تیم
        fig = create_trend_chart(
            df_all,
            st.session_state.trend_filters["selected_kpi"],
            st.session_state.trend_filters["time_range"],
            holidays
        )
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ داده‌ای برای نمایش روند یافت نشد")
    
    if selected_view == "All Designers" and st.session_state.current_user == "Sajad":
        # سجاد: نمودار جداگانه برای هر طراح
        designers = ["Sajad", "Romina", "Melika", "Fatemeh"]
        
        cols = st.columns(2)
        for idx, designer in enumerate(designers):
            with cols[idx % 2]:
                df_designer = df_all[df_all["Designer Name"] == designer]
                if not df_designer.empty:
                    fig = create_trend_chart(
                        df_designer,
                        st.session_state.trend_filters["selected_kpi"],
                        st.session_state.trend_filters["time_range"],
                        holidays
                    )
                    if fig:
                        # تغییر عنوان برای نشان دادن طراح
                        fig.update_layout(title=f"{designer}'s Trend")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"📊 هیچ داده‌ای برای {designer} یافت نشد")
                else:
                    st.info(f"📊 هیچ داده‌ای برای {designer} یافت نشد")
    
    elif selected_view.endswith("Only") and selected_view != "Team Only":
        # نمودار شخصی
        if st.session_state.current_user == "Sajad":
            designer = selected_view.replace(" Only", "")
        else:
            designer = st.session_state.current_user
        
        df_designer = df_all[df_all["Designer Name"] == designer]
        
        if not df_designer.empty:
            fig = create_trend_chart(
                df_designer,
                st.session_state.trend_filters["selected_kpi"],
                st.session_state.trend_filters["time_range"],
                holidays
            )
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"⚠️ داده‌ای برای نمایش روند {designer} یافت نشد")
        else:
            st.warning(f"⚠️ هیچ داده‌ای برای {designer} یافت نشد")
    
    # آمار خلاصه
    st.markdown("---")
    st.markdown("### 📊 آمار خلاصه")
    
    if selected_view == "Team Only" or selected_view == "All Designers":
        # آمار تیم
        total = len(df_all)
        kpi_value = calculate_kpi(df_all, st.session_state.trend_filters["selected_kpi"], holidays)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 تیم", f"{kpi_value}")
        with col2:
            st.metric("📊 مقدار KPI انتخابی", f"{kpi_value}")
        with col3:
            if total > 0:
                st.metric("📈 درصد", f"{kpi_value/total*100:.1f}%")
    
    if selected_view == "All Designers" and st.session_state.current_user == "Sajad":
        # آمار هر طراح برای سجاد
        designers = ["Sajad", "Romina", "Melika", "Fatemeh"]
        cols = st.columns(4)
        
        for idx, designer in enumerate(designers):
            with cols[idx]:
                df_designer = df_all[df_all["Designer Name"] == designer]
                total = len(df_designer)
                kpi_value = calculate_kpi(df_designer, st.session_state.trend_filters["selected_kpi"], holidays)
                
                st.metric(f"👤 {designer}", f"{kpi_value}", 
                         f"{kpi_value/total*100:.1f}%" if total > 0 else "0%")

# ======================
# MAIN APP FLOW
# ======================
def main():
    """گردش کار اصلی برنامه"""
    
    # صفحه لاگین
    if not st.session_state.is_authenticated:
        show_login_page()
        return
    
    # بعد از لاگین موفق
    render_sidebar()
    
    # نمایش صفحه فعال
    if st.session_state.active_page == "kpi":
        render_kpi_page()
    elif st.session_state.active_page == "quests":
        render_quests_page()
    elif st.session_state.active_page == "trend":
        render_trend_page()

# ======================
# RUN APP
# ======================
if __name__ == "__main__":
    main()
