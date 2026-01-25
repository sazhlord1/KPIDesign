import streamlit as st
import pandas as pd
import plotly.express as px
import jdatetime
from datetime import time

# ======================
# PAGE CONFIG (LIGHT MODE)
# ======================
st.set_page_config(
    page_title="Task Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================
# SESSION STATE
# ======================
if "step" not in st.session_state:
    st.session_state.step = "upload"

if "df_clean" not in st.session_state:
    st.session_state.df_clean = None

# ======================
# HELPERS
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


def clean_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    drop_letters = ["D","E","F","G","H","K","Q","R","S","T"]
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
        "درخواست كننده": "Customer",
        "تاریخ ددلاین": "Deadline - date",
        "ساعت ددلاین": "Hour",
        "نوع کاور": "Type",
        "تعداد ویرایش": "Edit count",
        "علت ویرایش": "Reason",
        "زمان ثبت بریف - تاریخ": "Submission date",
        "زمان ثبت بریف - ساعت": "Submission hour"
    }
    df = df.rename(columns=lambda x: rename_map.get(x, x))

    if "Deadline - date" in df.columns:
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
        if col in df.columns:
            df[col] = df[col].replace(replace_map)

    if "Customer" in df.columns:
        df["Customer"] = df["Customer"].apply(normalize_customer)

    if "Submission date" in df.columns:
        df["Submission date"] = pd.to_datetime(df["Submission date"], errors="coerce")

    if "Submission hour" in df.columns:
        df["Submission hour"] = pd.to_datetime(
            df["Submission hour"], errors="coerce"
        ).dt.time

    return df


def pie_chart(title, emoji, value, total, color):
    fig = px.pie(
        names=[title, "سایر"],
        values=[value, max(total - value, 0)],
        hole=0.4,
        color_discrete_sequence=[color, "#ECECEC"]
    )
    fig.update_traces(
        textinfo="percent+value",
        textfont_size=14,
        pull=[0.08, 0]
    )
    fig.update_layout(
        title=f"{emoji} {title}",
        showlegend=False,
        height=300,
        margin=dict(t=60, b=10)
    )
    return fig

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.title("📊 KPI Dashboard")
    if st.session_state.step == "done":
        if st.button("🔄 شروع دوباره"):
            st.session_state.step = "upload"
            st.session_state.df_clean = None
            st.rerun()

# ======================
# STEP 1 — UPLOAD
# ======================
if st.session_state.step == "upload":
    st.header("📤 آپلود فایل اکسل")
    uploaded_file = st.file_uploader(
        "فایل Exported را بارگذاری کنید",
        type=["xlsx"]
    )

    if uploaded_file:
        st.session_state.df_clean = clean_excel(uploaded_file)
        st.session_state.step = "ready"
        st.success("✅ فایل با موفقیت پاکسازی شد")

# ======================
# STEP 2 — READY
# ======================
if st.session_state.step == "ready":
    st.header("⚙️ آماده محاسبه KPI")
    if st.button("▶️ Calculate"):
        st.session_state.step = "done"
        st.rerun()

# ======================
# STEP 3 — ANALYSIS
# ======================
if st.session_state.step == "done":
    df = st.session_state.df_clean.copy()

    st.header("📈 تحلیل تسک‌ها")

    min_d = df["Submission date"].min()
    max_d = df["Submission date"].max()

    st.subheader("📅 تنظیم بازه و تعطیلات")

    col1, col2 = st.columns([2, 1])

    with col1:
        start_date, end_date = st.date_input(
            "بازه تحلیل",
            value=(min_d, max_d)
        )

    with col2:
        holidays = st.date_input(
            "روزهای تعطیل",
            value=[],
            help="این روزها به‌عنوان تعطیل در KPI دیرفرستاده‌ها لحاظ می‌شوند"
        )

    if not isinstance(holidays, list):
        holidays = [holidays]

    df = df[
        (df["Submission date"] >= pd.to_datetime(start_date)) &
        (df["Submission date"] <= pd.to_datetime(end_date))
    ]

    total = len(df)

    if total == 0:
        st.warning("⚠️ دیتایی در این بازه وجود ندارد")
        st.stop()

    ghorme = (df["Type"] == "Ghorme Sabzi").sum()
    omlet = (df["Type"] == "Omlet").sum()
    burger = (df["Type"] == "Burger").sum()

    designer_error = df["Reason"].isin(
        ["Designer Error", "Team-lead: Designer Error"]
    ).sum()

    revision_2 = (df["Edit count"] >= 2).sum()

    late = df[
        (df["Submission hour"] >= time(18, 0)) |
        (df["Submission date"].dt.date.isin(holidays))
    ].shape[0]

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.plotly_chart(pie_chart("قرمه سبزی", "🥬", ghorme, total, "#2ECC71"), True)
    c2.plotly_chart(pie_chart("املت", "🥚", omlet, total, "#F1C40F"), True)
    c3.plotly_chart(pie_chart("برگر", "🍔", burger, total, "#E67E22"), True)

    c4.plotly_chart(pie_chart("ایراد طراح", "❌", designer_error, total, "#E74C3C"), True)
    c5.plotly_chart(pie_chart("ایراد طراح بیشتر از ۲بار", "❌❌", revision_2, total, "#8E44AD"), True)
    c6.plotly_chart(pie_chart("دیرفرستاده‌ها", "🧳", late, total, "#34495E"), True)
