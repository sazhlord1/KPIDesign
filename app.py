import streamlit as st
import pandas as pd
import plotly.express as px
import jdatetime
from datetime import time, date
import json
import os
import uuid

# ======================
# PAGE CONFIG
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

if "holidays" not in st.session_state:
    st.session_state.holidays = []

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = {}

if "active_page" not in st.session_state:
    st.session_state.active_page = "kpi"

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ======================
# QUEST STORAGE
# ======================
QUEST_FILE = "quests.json"

def load_quests():
    if not os.path.exists(QUEST_FILE):
        return []
    with open(QUEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quests(data):
    with open(QUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def normalize_designer(val):
    mapping = {
        "ملیکا عرب زاده": "Melika",
        "ملیکا عرب‌زاده": "Melika",
        "رومینا": "Romina",
        "سجاد": "Sajad",
        "فاطمه": "Fatemeh"
    }
    return mapping.get(str(val).strip(), val)

# ======================
# CLEAN EXCEL
# ======================
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

# ======================
# CHART
# ======================
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

def chart_block(col, title, emoji, fig):
    with col:
        st.markdown(f"### {emoji} {title}")
        st.plotly_chart(fig, use_container_width=True)

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.title("📊 KPI Dashboard")

    if st.session_state.step == "done":
        if st.button("🔄 شروع دوباره"):
            st.session_state.step = "upload"
            st.session_state.df_clean = None
            st.session_state.holidays = []
            st.session_state.auth_ok = {}
            st.session_state.active_page = "kpi"
            st.session_state.current_user = None
            st.rerun()

        if st.session_state.current_user:
            if st.button("🗡️ Quests"):
                st.session_state.active_page = "quests"
                st.rerun()

# ======================
# STEP 1 — UPLOAD
# ======================
if st.session_state.step == "upload":
    st.header("📤 آپلود فایل اکسل")
    uploaded_file = st.file_uploader("فایل Exported را بارگذاری کنید", type=["xlsx"])

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
# STEP 3 — KPI / QUESTS
# ======================
if st.session_state.step == "done":

    # ======================
    # QUEST PAGE
    # ======================
    if st.session_state.active_page == "quests":
        st.header("🗡️ Quests")

        if st.button("⬅️ بازگشت به داشبورد KPI"):
            st.session_state.active_page = "kpi"
            st.rerun()

        quests = load_quests()
        user = st.session_state.current_user

        if user == "Sajad":
            tab1, tab2, tab3 = st.tabs(["➕ New Quest", "📜 All Quests", "🎯 My Quests"])

            with tab1:
                name = st.text_input("Name the new quest")
                desc = st.text_area("What describes the quest the best?")
                deadline = st.date_input("Pose a new deadline", value=date.today())
                owner = st.selectbox("Assign to", ["Sajad", "Romina", "Melika", "Fatemeh"])
                if st.button("Finish"):
                    quests.append({
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "description": desc,
                        "deadline": str(deadline),
                        "owner": owner,
                        "done": False
                    })
                    save_quests(quests)
                    st.success("✅ Quest added")

            with tab2:
                who = st.selectbox("🗡️ Whose Quests you want to see?", ["Sajad", "Romina", "Melika", "Fatemeh"])
                for q in [x for x in quests if x["owner"] == who]:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"### {q['name']}")
                        st.caption(q["description"])
                        st.write(f"⏰ {q['deadline']}")
                    with col2:
                        if st.checkbox("Done", value=q["done"], key=q["id"]):
                            q["done"] = True
                        if st.button("🗑️ Delete", key="del"+q["id"]):
                            quests.remove(q)
                            save_quests(quests)
                            st.rerun()
                save_quests(quests)

            with tab3:
                for q in [x for x in quests if x["owner"] == "Sajad"]:
                    st.markdown(f"### {q['name']}")
                    st.caption(q["description"])
                    st.write(f"⏰ {q['deadline']} | {'✅ Done' if q['done'] else '⬜ Pending'}")

        else:
            st.subheader("🎯 My Quests")
            for q in [x for x in quests if x["owner"] == user]:
                st.markdown(f"### {q['name']}")
                st.caption(q["description"])
                st.write(f"⏰ {q['deadline']} | {'✅ Done' if q['done'] else '⬜ Pending'}")

    # ======================
    # KPI PAGE
    # ======================
    else:
        df_all = st.session_state.df_clean.copy()
        min_d = df_all["Submission date"].min()
        max_d = df_all["Submission date"].max()

        st.subheader("📅 تنظیم بازه و تعطیلات")

        c1, c2 = st.columns([2, 1])
        with c1:
            start_date, end_date = st.date_input("بازه تحلیل", value=(min_d, max_d))

        with c2:
            selected_day = st.date_input("روز تعطیل", value=None)
            if st.button("➕ افزودن"):
                if selected_day and selected_day not in st.session_state.holidays:
                    st.session_state.holidays.append(selected_day)

            holidays = st.multiselect("تعطیلات", st.session_state.holidays, st.session_state.holidays)

        df_all = df_all[
            (df_all["Submission date"] >= pd.to_datetime(start_date)) &
            (df_all["Submission date"] <= pd.to_datetime(end_date))
        ]

        tabs = st.tabs(["Team KPI", "Sajad KPI", "Romina KPI", "Melika KPI", "Fatemeh KPI"])

        passwords = {
            "Sajad": "2232245",
            "Romina": "112131",
            "Melika": "122232",
            "Fatemeh": "132333"
        }

        def render_kpi(df):
            total = len(df)
            if total == 0:
                st.warning("⚠️ دیتایی وجود ندارد")
                return

            ghorme = (df["Type"] == "Ghorme Sabzi").sum()
            omlet = (df["Type"] == "Omlet").sum()
            burger = (df["Type"] == "Burger").sum()
            designer_error = df["Reason"].isin(["Designer Error", "Team-lead: Designer Error"]).sum()
            revision_2 = (df["Edit count"] >= 2).sum()
            late = df[(df["Submission hour"] >= time(18, 0)) | (df["Submission date"].dt.date.isin(holidays))].shape[0]

            r1 = st.columns(3)
            r2 = st.columns(3)

            chart_block(r1[0], "Ghorme Sabzi Ratio", "🥬", pie_chart("Ghorme Sabzi", ghorme, total, "#2ECC71"))
            chart_block(r1[1], "Omlet Ratio", "🥚", pie_chart("Omlet", omlet, total, "#F1C40F"))
            chart_block(r1[2], "Burger Ratio", "🍔", pie_chart("Burger", burger, total, "#E67E22"))
            chart_block(r2[0], "Designer Error Rate", "❌", pie_chart("Designer Error", designer_error, total, "#E74C3C"))
            chart_block(r2[1], "More Than 2 Revisions", "🔁", pie_chart("2+ Revisions", revision_2, total, "#8E44AD"))
            chart_block(r2[2], "Late Submissions", "⏰", pie_chart("Late", late, total, "#34495E"))

        with tabs[0]:
            render_kpi(df_all)

        for i, name in enumerate(["Sajad", "Romina", "Melika", "Fatemeh"], start=1):
            with tabs[i]:
                if not st.session_state.auth_ok.get(name, False):
                    pwd = st.text_input(f"پسورد {name}", type="password", key=f"pwd_{name}")
                    st.warning("⚠️ پسورد شخصی است")
                    if st.button("ورود", key=f"btn_{name}"):
                        if pwd == passwords[name]:
                            st.session_state.auth_ok[name] = True
                            st.session_state.current_user = name
                            st.rerun()
                        else:
                            st.error("❌ پسورد اشتباه است")
                else:
                    render_kpi(df_all[df_all["Designer Name"] == name])
