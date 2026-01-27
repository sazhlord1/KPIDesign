import streamlit as st
import pandas as pd
import plotly.express as px
import jdatetime
from datetime import time, date
import json
import os

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(
    page_title="Task Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

QUEST_FILE = "quests_data.json"
DESIGNERS = ["Sajad", "Romina", "Melika", "Fatemeh"]

# ======================
# QUEST STORAGE
# ======================
def load_quests():
    if not os.path.exists(QUEST_FILE):
        data = {name: [] for name in DESIGNERS}
        with open(QUEST_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return data
    with open(QUEST_FILE, "r") as f:
        return json.load(f)

def save_quests(data):
    with open(QUEST_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

if "quest_page" not in st.session_state:
    st.session_state.quest_page = None

# ======================
# HELPERS (KPI)
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
    drop_indexes = [ord(l)-65 for l in drop_letters if ord(l)-65 < len(df.columns)]
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
            st.session_state.quest_page = None
            st.rerun()

        if st.session_state.auth_ok.get("Sajad"):
            if st.button("🗡️ Quests"):
                st.session_state.quest_page = "main"
                st.rerun()

# ======================
# QUEST PAGES
# ======================
if st.session_state.quest_page:
    quests = load_quests()
    st.header("🗡️ Quest Board")

    col1, col2, col3 = st.columns(3)

    if col1.button("➕ New Quest"):
        st.session_state.quest_page = "new"

    if col2.button("📜 All Quests"):
        st.session_state.quest_page = "all"

    if col3.button("🎯 My Quests"):
        st.session_state.quest_page = "my"

    st.divider()

    # NEW QUEST
    if st.session_state.quest_page == "new":
        st.subheader("➕ Create New Quest")
        name = st.text_input("Name the new quest")
        desc = st.text_area("What describes the quest the best?")
        deadline = st.date_input("Pose a new deadline", value=date.today())

        if st.button("Finish"):
            quests["Sajad"].append({
                "name": name,
                "description": desc,
                "deadline": str(deadline),
                "done": False
            })
            save_quests(quests)
            st.success("✅ Quest created")

    # ALL QUESTS
    if st.session_state.quest_page == "all":
        owner = st.selectbox("🗡️ Whose Quests you want to see?", DESIGNERS)
        for i, q in enumerate(quests[owner]):
            c1, c2 = st.columns([6,1])
            with c1:
                st.markdown(f"### {q['name']}")
                st.markdown(q["description"])
                st.caption(f"📅 Deadline: {q['deadline']}")
            with c2:
                q["done"] = st.checkbox("Done", value=q["done"], key=f"{owner}_{i}")
        save_quests(quests)

    # MY QUESTS
    if st.session_state.quest_page == "my":
        st.subheader("🎯 My Quests")
        for q in quests["Sajad"]:
            st.markdown(f"### {q['name']}")
            st.markdown(q["description"])
            st.caption(f"📅 {q['deadline']} | {'✅ Done' if q['done'] else '⬜ Pending'}")

    st.stop()
