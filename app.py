import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import jdatetime
from datetime import time, date, datetime
import json
import os
import uuid
from io import BytesIO
import hashlib

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
    /* Remove white space at top */
    .stApp {
        margin-top: -50px;
    }
    
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        padding-top: 1rem;
    }
    
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
    }
    
    .login-title {
        text-align: center;
        color: #374151;
        margin-bottom: 0.5rem;
    }
    
    .login-subtitle {
        text-align: center;
        color: #6b7280;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #3B82F6;
    }
    
    .quest-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        margin-bottom: 1rem;
        border-left: 5px solid #10B981;
    }
    
    .success-badge {
        background-color: #10B981;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.875rem;
        display: inline-block;
        font-weight: 600;
    }
    
    .pending-badge {
        background-color: #F59E0B;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.875rem;
        display: inline-block;
        font-weight: 600;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.75rem;
        font-size: 1rem;
    }
    
    /* مخفی کردن المان‌های ناخواسته */
    .upload-section,
    [class*="upload"],
    .success-message {
        display: none !important;
    }
    
    /* بک‌گراند ترنسپرنت برای چارت‌ها */
    .js-plotly-plot .plotly,
    .js-plotly-plot .plotly .modebar,
    .js-plotly-plot .plotly .main-svg {
        background-color: transparent !important;
    }
    
    /* لجند کاملاً ترنسپرنت */
    .js-plotly-plot .plotly .legend {
        background-color: rgba(255, 255, 255, 0) !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* حذف هرگونه stroke از لجند */
    .js-plotly-plot .plotly .legend rect {
        stroke: none !important;
        stroke-opacity: 0 !important;
        fill-opacity: 0 !important;
    }
    
    /* متن لجند */
    .js-plotly-plot .plotly .legend .legendtext {
        font-weight: 500 !important;
        fill: #333333 !important;
    }
    
    /* عنوان لجند */
    .js-plotly-plot .plotly .legend .legendtitletext {
        font-weight: 600 !important;
        fill: #333333 !important;
    }
    
    /* بهبود ظاهر expander */
    .streamlit-expanderHeader {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        border: 1px solid #e9ecef !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderContent {
        background-color: white !important;
        border-radius: 0 0 8px 8px !important;
        border: 1px solid #e9ecef !important;
        border-top: none !important;
    }
    
    /* فاصله‌گذاری بهتر */
    .element-container {
        margin-bottom: 1rem;
    }
    
    /* بهبود ظاهر selectbox */
    .stSelectbox > div > div {
        border-radius: 8px !important;
    }
    
    /* بهبود ظاهر date input */
    .stDateInput > div > div {
        border-radius: 8px !important;
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

if "editing_quest" not in st.session_state:
    st.session_state.editing_quest = None

if "quest_created" not in st.session_state:
    st.session_state.quest_created = False

# ======================
# DATA STORAGE
# ======================
def get_data_dir():
    """Get or create data directory"""
    data_dir = "dashboard_data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def get_quests_file():
    """Get quests file path"""
    return os.path.join(get_data_dir(), "quests.json")

def get_holidays_file():
    """Get holidays file path"""
    return os.path.join(get_data_dir(), "holidays.json")

def load_quests():
    """Load quests from persistent storage"""
    quests_file = get_quests_file()
    if not os.path.exists(quests_file):
        return []
    try:
        with open(quests_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading quests: {e}")
        return []

def save_quests(data):
    """Save quests to persistent storage"""
    quests_file = get_quests_file()
    try:
        with open(quests_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving quests: {e}")

def load_holidays():
    """Load holidays from persistent storage"""
    holidays_file = get_holidays_file()
    if not os.path.exists(holidays_file):
        return []
    try:
        with open(holidays_file, "r", encoding="utf-8") as f:
            dates = json.load(f)
            # Convert string dates back to date objects
            return [date.fromisoformat(d) if isinstance(d, str) else d for d in dates]
    except Exception as e:
        st.error(f"Error loading holidays: {e}")
        return []

def save_holidays(holidays_list):
    """Save holidays to persistent storage"""
    holidays_file = get_holidays_file()
    try:
        # Convert date objects to strings for JSON serialization
        dates_str = [str(d) if isinstance(d, date) else d for d in holidays_list]
        with open(holidays_file, "w", encoding="utf-8") as f:
            json.dump(dates_str, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving holidays: {e}")

# Load persistent data on startup
if "holidays_loaded" not in st.session_state:
    st.session_state.holidays = load_holidays()
    st.session_state.holidays_loaded = True

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
    fig.update_layout(
        showlegend=False, 
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
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

def create_trend_chart(df_all, kpi_name, time_range, holidays, designers=None):
    """Create multi-line chart for trend analysis"""
    kpi_options = get_kpi_options()
    emoji = kpi_options[kpi_name]["emoji"]
    
    # Color palette for designers
    color_palette = {
        "Team": "#3498DB",      # Blue
        "Sajad": "#2ECC71",     # Green
        "Romina": "#E74C3C",    # Red
        "Melika": "#9B59B6",    # Purple
        "Fatemeh": "#F39C12"    # Orange
    }
    
    all_data = []
    
    # Determine which designers to show
    if designers is None:
        designers_to_show = ["Team", "Sajad", "Romina", "Melika", "Fatemeh"]
    else:
        designers_to_show = designers
    
    for designer in designers_to_show:
        # Filter data for each designer
        if designer == "Team":
            df_designer = df_all
            display_name = "Team"
        else:
            df_designer = df_all[df_all["Designer Name"] == designer]
            display_name = designer
        
        if df_designer.empty:
            continue
        
        # Prepare data
        df = df_designer.copy()
        
        if time_range == "Monthly":
            # Daily trend for last 30 days
            end_date = df["Submission date"].max()
            start_date = end_date - pd.Timedelta(days=30)
            df_period = df[df["Submission date"] >= start_date]
            
            if df_period.empty:
                continue
            
            # Group by day
            daily_data = []
            current_date = start_date.date()
            
            while current_date <= end_date.date():
                day_data = df_period[df_period["Submission date"].dt.date == current_date]
                value = calculate_kpi(day_data, kpi_name, holidays)
                daily_data.append({
                    "date": current_date,
                    "value": value,
                    "designer": display_name,
                    "time_label": current_date.strftime("%Y-%m-%d")
                })
                current_date += pd.Timedelta(days=1)
            
            if daily_data:
                designer_df = pd.DataFrame(daily_data)
                all_data.append(designer_df)
        
        else:  # Annually or All time
            # Create year_month column for grouping
            df["year_month"] = df["Submission date"].dt.to_period("M")
            
            if time_range == "Annually":
                end_date = df["Submission date"].max()
                start_date = end_date - pd.DateOffset(months=11)
                df_period = df[df["Submission date"] >= start_date]
            else:  # All time
                df_period = df
            
            if df_period.empty:
                continue
            
            # Group by month
            monthly_stats = df_period.groupby("year_month").apply(
                lambda x: calculate_kpi(x, kpi_name, holidays)
            ).reset_index(name="value")
            
            monthly_stats["designer"] = display_name
            monthly_stats["time_label"] = monthly_stats["year_month"].dt.strftime("%Y-%m")
            
            all_data.append(monthly_stats)
    
    if not all_data:
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Create multi-line chart
    title = f"{emoji} {kpi_name} Trend"
    
    fig = px.line(
        combined_df,
        x="time_label",
        y="value",
        color="designer",
        title=title,
        markers=True,
        color_discrete_map=color_palette,
        line_shape="linear"  # خطوط مستقیم
    )
    
    # Chart styling - لجند کاملاً ترنسپرنت
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Count",
        hovermode="x unified",
        height=600,
        legend_title="Designer",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0)',  # کاملاً ترنسپرنت
            bordercolor='rgba(255, 255, 255, 0)',  # حاشیه ترنسپرنت
            borderwidth=0,
            font=dict(
                size=12,
                color="#333333"
            ),
            title=dict(
                font=dict(
                    size=13,
                    color="#333333",
                    weight="bold"
                )
            )
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="#333333"
        ),
        title=dict(
            x=0.5,
            xanchor='center',
            font=dict(size=20)
        )
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(0,0,0,0.1)',
        tickangle=45,
        tickfont=dict(size=11),
        linecolor='rgba(0,0,0,0.2)',
        zeroline=False
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(0,0,0,0.1)',
        tickfont=dict(size=11),
        linecolor='rgba(0,0,0,0.2)',
        zeroline=False
    )
    
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )
    
    return fig

# ======================
# AUTHENTICATION
# ======================
def show_login_page():
    """Login page"""
    st.markdown('<h1 class="main-header">📊 Task Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown('<h2 class="login-title">🔐 Login</h2>', unsafe_allow_html=True)
            st.markdown('<p class="login-subtitle">Please enter your credentials</p>', unsafe_allow_html=True)
            
            username = st.selectbox(
                "👤 Username",
                options=["Select...", "Sajad", "Romina", "Melika", "Fatemeh"]
            )
            
            password = st.text_input("🔑 Password", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.button("🚀 Login", type="primary", use_container_width=True)
            with col_btn2:
                clear_btn = st.button("🔄 Clear", use_container_width=True)
            
            if login_btn:
                if username == "Select...":
                    st.error("❌ Please select a username")
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
                        st.success(f"✅ Welcome {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")
            
            if clear_btn:
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# ======================
# SIDEBAR
# ======================
def render_sidebar():
    """Main sidebar after login"""
    with st.sidebar:
        st.markdown(f"### 👋 Hi {st.session_state.current_user}!")
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
        
        if st.button("🚪 Logout", use_container_width=True):
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
    """KPI Page"""
    st.markdown('<h1 class="main-header">📊 KPI Dashboard</h1>', unsafe_allow_html=True)
    
    # Show upload section if no data exists
    if st.session_state.df_clean is None:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 📁 Upload Excel File")
            st.markdown("Please upload your Excel file to start analysis")
            
            uploaded_file = st.file_uploader("Choose Excel file", type=["xlsx"], label_visibility="collapsed")
            
            if uploaded_file is not None:
                with st.spinner("🔄 Processing file..."):
                    st.session_state.df_clean = clean_excel(uploaded_file)
                    st.success("✅ File uploaded and processed successfully!")
                    st.rerun()
        return
    
    # If data exists, show KPI
    df_all = st.session_state.df_clean.copy()
    
    # Date range and holiday settings
    st.markdown("### ⚙️ Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        min_d = df_all["Submission date"].min()
        max_d = df_all["Submission date"].max()
        start_date, end_date = st.date_input(
            "📅 Analysis Period",
            value=(min_d, max_d),
            key="date_range_kpi"
        )
    
    with col2:
        selected_day = st.date_input("📌 Holiday Date", value=None, key="holiday_day")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ Add Holiday", use_container_width=True):
                if selected_day and selected_day not in st.session_state.holidays:
                    st.session_state.holidays.append(selected_day)
                    save_holidays(st.session_state.holidays)
                    st.success(f"✅ {selected_day} added to holidays")
                    st.rerun()
        
        with col_btn2:
            if st.button("🗑️ Clear Holidays", use_container_width=True):
                if st.session_state.holidays:
                    st.session_state.holidays = []
                    save_holidays([])
                    st.success("✅ All holidays cleared")
                    st.rerun()
    
    # Show current holidays
    if st.session_state.holidays:
        st.info(f"📋 Current Holidays: {', '.join([str(d) for d in st.session_state.holidays])}")
    
    # Filter data based on date range
    df_filtered = df_all[
        (df_all["Submission date"] >= pd.to_datetime(start_date)) &
        (df_all["Submission date"] <= pd.to_datetime(end_date))
    ]
    
    # Tabs for different designers
    if st.session_state.current_user == "Sajad":
        tab_names = ["Team KPI", "Sajad KPI", "Romina KPI", "Melika KPI", "Fatemeh KPI"]
        tab_designers = [None, "Sajad", "Romina", "Melika", "Fatemeh"]
    else:
        tab_names = ["Team KPI", f"{st.session_state.current_user} KPI"]
        tab_designers = [None, st.session_state.current_user]
    
    tabs = st.tabs([f"**{name}**" for name in tab_names])
    
    for idx, (tab, designer) in enumerate(zip(tabs, tab_designers)):
        with tab:
            if designer is None:
                df_to_show = df_filtered
                title = "Team"
            else:
                df_to_show = df_filtered[df_filtered["Designer Name"] == designer]
                title = designer
            
            total = len(df_to_show)
            
            if total == 0:
                st.warning(f"⚠️ No data found for {title} in this period")
                continue
            
            # Calculate KPIs
            ghorme = (df_to_show["Type"] == "Ghorme Sabzi").sum()
            omlet = (df_to_show["Type"] == "Omlet").sum()
            burger = (df_to_show["Type"] == "Burger").sum()
            designer_error = df_to_show["Reason"].isin(["Designer Error", "Team-lead: Designer Error"]).sum()
            revision_2 = (df_to_show["Edit count"] >= 2).sum()
            late = df_to_show[(df_to_show["Submission hour"] >= time(18, 0)) | 
                              (df_to_show["Submission date"].dt.date.isin(st.session_state.holidays))].shape[0]
            
            # Display KPIs in two rows
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🥬 Ghorme Sabzi", f"{ghorme}", f"{ghorme/total*100:.1f}%")
                fig1 = pie_chart("Ghorme Sabzi", ghorme, total, "#2ECC71")
                st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
            
            with col2:
                st.metric("🥚 Omlet", f"{omlet}", f"{omlet/total*100:.1f}%")
                fig2 = pie_chart("Omlet", omlet, total, "#F1C40F")
                st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
            
            with col3:
                st.metric("🍔 Burger", f"{burger}", f"{burger/total*100:.1f}%")
                fig3 = pie_chart("Burger", burger, total, "#E67E22")
                st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
            
            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("❌ Designer Error", f"{designer_error}", f"{designer_error/total*100:.1f}%")
                fig4 = pie_chart("Designer Error", designer_error, total, "#E74C3C")
                st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})
            
            with col5:
                st.metric("🔁 Edits > 2", f"{revision_2}", f"{revision_2/total*100:.1f}%")
                fig5 = pie_chart("2+ Revisions", revision_2, total, "#8E44AD")
                st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})
            
            with col6:
                st.metric("⏰ Late Submissions", f"{late}", f"{late/total*100:.1f}%")
                fig6 = pie_chart("Late", late, total, "#34495E")
                st.plotly_chart(fig6, use_container_width=True, config={'displayModeBar': False})
    
    # Re-upload button at bottom
    st.markdown("---")
    if st.button("📤 Upload New Excel File", use_container_width=True):
        st.session_state.show_upload_modal = True
    
    # Upload modal
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
                st.markdown("### 📁 Upload New File")
                
                new_file = st.file_uploader("Choose Excel file", type=["xlsx"], 
                                          key="modal_uploader")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Confirm", use_container_width=True):
                        if new_file is not None:
                            st.session_state.df_clean = clean_excel(new_file)
                            st.session_state.show_upload_modal = False
                            st.success("✅ New file uploaded successfully!")
                            st.rerun()
                
                with col_btn2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.show_upload_modal = False
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

# ======================
# QUESTS PAGE
# ======================
def render_quest_edit_form(quest):
    """Render quest edit form"""
    st.markdown(f"### ✏️ Edit Quest: {quest['name']}")
    
    name = st.text_input("📝 Quest Name", value=quest["name"])
    description = st.text_area("📋 Description", value=quest["description"])
    deadline = st.date_input("📅 Deadline", value=date.fromisoformat(quest["deadline"]))
    owner = st.selectbox("👤 Assign to", ["Sajad", "Romina", "Melika", "Fatemeh"], 
                        index=["Sajad", "Romina", "Melika", "Fatemeh"].index(quest["owner"]))
    done = st.checkbox("✅ Mark as completed", value=quest["done"])
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            # Update quest
            quest["name"] = name
            quest["description"] = description
            quest["deadline"] = str(deadline)
            quest["owner"] = owner
            quest["done"] = done
            
            # Save to file
            quests = load_quests()
            for i, q in enumerate(quests):
                if q["id"] == quest["id"]:
                    quests[i] = quest
                    break
            
            save_quests(quests)
            st.session_state.editing_quest = None
            st.success("✅ Quest updated successfully!")
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.editing_quest = None
            st.rerun()

def render_quests_page():
    """Quests Page"""
    st.markdown('<h1 class="main-header">🗡️ Quest Management</h1>', unsafe_allow_html=True)
    
    # Check if editing a quest
    if st.session_state.editing_quest is not None:
        render_quest_edit_form(st.session_state.editing_quest)
        return
    
    # Load quests from persistent storage
    quests = load_quests()
    
    # Show success message if quest was just created
    if st.session_state.quest_created:
        st.success("✅ **The new quest has been submitted successfully**")
        st.session_state.quest_created = False
    
    if st.session_state.current_user == "Sajad":
        # Sajad - Full dashboard
        tab1, tab2, tab3 = st.tabs(["➕ New Quest", "📜 All Quests", "🎯 My Quests"])
        
        with tab1:
            st.markdown("### 🆕 Create New Quest")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("📝 Quest Name")
                description = st.text_area("📋 Description")
            
            with col2:
                deadline = st.date_input("📅 Deadline", value=date.today())
                owner = st.selectbox("👤 Assign to", ["Sajad", "Romina", "Melika", "Fatemeh"])
            
            if st.button("✅ Create Quest", type="primary", use_container_width=True):
                if name and description:
                    new_quest = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "description": description,
                        "deadline": str(deadline),
                        "owner": owner,
                        "done": False,
                        "created_by": st.session_state.current_user,
                        "created_at": str(date.today())
                    }
                    quests.append(new_quest)
                    save_quests(quests)
                    st.session_state.quest_created = True
                    st.rerun()
                else:
                    st.error("❌ Please enter quest name and description")
        
        with tab2:
            st.markdown("### 📋 All Quests")
            
            filter_owner = st.selectbox("Filter by owner", 
                                       ["All", "Sajad", "Romina", "Melika", "Fatemeh"])
            
            filtered_quests = quests if filter_owner == "All" else [q for q in quests if q["owner"] == filter_owner]
            
            if not filtered_quests:
                st.info("📭 No quests found")
            else:
                for q in filtered_quests:
                    with st.container():
                        st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"#### {q['name']}")
                            st.caption(q["description"])
                            st.markdown(f"**📅 Deadline:** {q['deadline']} | **👤 Owner:** {q['owner']}")
                        
                        with col2:
                            if q["done"]:
                                st.markdown('<span class="success-badge">✅ Completed</span>', unsafe_allow_html=True)
                            else:
                                st.markdown('<span class="pending-badge">🔄 In Progress</span>', unsafe_allow_html=True)
                        
                        with col3:
                            col_edit, col_del = st.columns(2)
                            with col_edit:
                                if st.button("✏️ Edit", key=f"edit_{q['id']}"):
                                    st.session_state.editing_quest = q
                                    st.rerun()
                            
                            with col_del:
                                if st.button("🗑️", key=f"del_{q['id']}"):
                                    quests.remove(q)
                                    save_quests(quests)
                                    st.success("✅ Quest deleted")
                                    st.rerun()
                        
                        st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown("### 🎯 My Quests")
            my_quests = [q for q in quests if q["owner"] == "Sajad"]
            
            if not my_quests:
                st.info("📭 No quests assigned to you")
            else:
                for q in my_quests:
                    with st.container():
                        st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                        
                        st.markdown(f"#### {q['name']}")
                        st.caption(q["description"])
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**📅 Deadline:** {q['deadline']}")
                        
                        with col2:
                            if q["done"]:
                                st.markdown('<span class="success-badge">✅ Completed</span>', unsafe_allow_html=True)
                            else:
                                st.markdown('<span class="pending-badge">🔄 In Progress</span>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # Other users - Only their quests
        st.markdown(f"### 🎯 {st.session_state.current_user}'s Quests")
        
        user_quests = [q for q in quests if q["owner"] == st.session_state.current_user]
        
        if not user_quests:
            st.info("📭 No quests assigned to you")
        else:
            for q in user_quests:
                with st.container():
                    st.markdown('<div class="quest-card">', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {q['name']}")
                    st.caption(q["description"])
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**📅 Deadline:** {q['deadline']}")
                        if "created_by" in q:
                            st.caption(f"Created by: {q['created_by']}")
                    
                    with col2:
                        if q["done"]:
                            st.markdown('<span class="success-badge">✅ Completed</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="pending-badge">🔄 In Progress</span>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# ======================
# TREND PAGE
# ======================
def render_trend_page():
    """Trend Analysis Page"""
    st.markdown('<h1 class="main-header">📈 Trend Analysis</h1>', unsafe_allow_html=True)
    
    if st.session_state.df_clean is None:
        st.warning("⚠️ Please upload an Excel file from the KPI page first")
        return
    
    df_all = st.session_state.df_clean.copy()
    
    # Filters container
    with st.container():
        st.markdown("### ⚙️ Filters")
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
            if st.session_state.current_user == "Sajad":
                view_options = ["Team Only", "All Designers", "Sajad Only", "Romina Only", "Melika Only", "Fatemeh Only"]
                selected_view = st.selectbox("👀 View", options=view_options)
            else:
                view_options = ["Team Only", f"{st.session_state.current_user} Only"]
                selected_view = st.selectbox("👀 View", options=view_options)
    
    # Determine which designers to show
    if selected_view == "Team Only":
        designers_to_show = ["Team"]
    elif selected_view == "All Designers" and st.session_state.current_user == "Sajad":
        designers_to_show = ["Team", "Sajad", "Romina", "Melika", "Fatemeh"]
    elif selected_view.endswith("Only") and selected_view != "Team Only":
        designer = selected_view.replace(" Only", "")
        designers_to_show = [designer]
    else:
        designers_to_show = ["Team"]
    
    # Create and display chart
    holidays = st.session_state.holidays
    
    fig = create_trend_chart(
        df_all,
        st.session_state.trend_filters["selected_kpi"],
        st.session_state.trend_filters["time_range"],
        holidays,
        designers=designers_to_show
    )
    
    if fig:
        # Chart container
        with st.container():
            st.markdown("### 📊 Trend Chart")
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'responsive': True
            })
    else:
        st.warning("⚠️ No data found for trend analysis")

# ======================
# MAIN APP
# ======================
def main():
    # Check if user is authenticated
    if not st.session_state.is_authenticated:
        show_login_page()
    else:
        render_sidebar()
        
        if st.session_state.active_page == "kpi":
            render_kpi_page()
        elif st.session_state.active_page == "quests":
            render_quests_page()
        elif st.session_state.active_page == "trend":
            render_trend_page()

# Run the app
if __name__ == "__main__":
    main()
