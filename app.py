import streamlit as st
import pandas as pd
import plotly.express as px
import jdatetime
import json
import os
from datetime import time, date

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="Task Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

QUEST_FILE = "quests.json"

PASSWORDS = {
    "Sajad": "2232245",
    "Romina": "112131",
    "Melika": "122232",
    "Fatemeh": "132333"
}

DESIGNERS = ["Sajad", "Romina", "Melika", "Fatemeh"]

# ======================
# QUEST STORAGE
# ======================
def load_quests():
    if not os.path.exists(QUEST_FILE):
        with open(QUEST_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(QUEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quests(data):
    with open(QUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ======================
# SESSION STATE
# ======================
if "step" not in st.session_state:
    st.session_state.step = "upload"

if "df_clean" not in st.session_state:
    st.session_state.df_clean = None

if "holidays" not in st.session_state:
    st.session_state.holidays = []

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Team KPI"

if "quest_view" not in st.session_state:
    st.session_state.quest_view = None

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
        "تاریخ ددلاین": "Deadline - date",
        "ساعت ددلاین": "Hour",
        "نوع کاور": "Type",
        "تعداد ویرایش": "Edit count",
        "علت ویرایش": "Reason",
        "زمان ثبت بریف - تاریخ": "Submission date",
        "زمان ثبت بریف - ساعت": "Submission hour"
    }
    df = df.rename(columns=lambda x: rename_map.get(x, x))

    designer_map = {
        "ملیکا عرب زاده": "Melika",
        "رومینا": "Romina",
        "سجاد": "Sajad",
        "فاطمه": "Fatemeh"
    }

    df["Designer Name"] = df["Designer Name"].replace(designer_map)

    df["Deadline - date"] = df["Deadline - date"].apply(jalali_to_gregorian)
    df["Submission date"] = pd.to_datetime(df["Submission date"], errors="coerce")
    df["Submission hour"] = pd.to_datetime(df["Submission hour"], errors="coerce").dt.time
    df["Customer"] = df["Customer"].apply(normalize_customer)

    return df

def pie(title, value, total, color):
    fig = px.pie(
        names=[title, "Other"],
        values=[value, max(total - value, 0)],
        hole=0.4,
        color_discrete_sequence=[color, "#ECECEC"]
    )
    fig.update_traces(textinfo="percent+value")
    fig.update_layout(title=title, showlegend=False)
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
            st.session_state.quest_view = None
            st.rerun()

        if st.session_state.active_tab == "Sajad KPI":
            if st.button("🗺️ Quests"):
                st.session_state.quest_view = "menu"

# ======================
# UPLOAD
# ======================
if st.session_state.step == "upload":
    uploaded = st.file_uploader("📤 Upload Excel", type=["xlsx"])
    if uploaded:
        st.session_state.df_clean = clean_excel(uploaded)
        st.session_state.step = "ready"
        st.success("✅ File cleaned")

if st.session_state.step == "ready":
    if st.button("▶️ Calculate"):
        st.session_state.step = "done"
        st.rerun()

# ======================
# MAIN DASHBOARD
# ======================
if st.session_state.step == "done":

    tabs = ["Team KPI"] + [f"{d} KPI" for d in DESIGNERS]
    selected = st.radio("Select dashboard", tabs, horizontal=True)
    st.session_state.active_tab = selected

    df = st.session_state.df_clean.copy()

    # PASSWORD GATE
    if selected != "Team KPI":
        name = selected.replace(" KPI", "")
        pwd = st.text_input("🔒 Enter password", type="password")
        st.warning("⚠️ پسورد خودتونو در اختیار بقیه قرار ندید")
        if pwd != PASSWORDS[name]:
            st.stop()
        df = df[df["Designer Name"] == name]

    total = len(df)

    st.header(f"📈 {selected}")

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.plotly_chart(pie("🥬 Ghorme Sabzi", (df["Type"] == "Ghorme Sabzi").sum(), total, "#2ECC71"))
    c2.plotly_chart(pie("🍳 Omlet", (df["Type"] == "Omlet").sum(), total, "#F1C40F"))
    c3.plotly_chart(pie("🍔 Burger", (df["Type"] == "Burger").sum(), total, "#E67E22"))

    c4.plotly_chart(pie("❌ Designer Error", df["Reason"].str.contains("Designer Error", na=False).sum(), total, "#E74C3C"))
    c5.plotly_chart(pie("❌❌ Edit ≥ 2", (df["Edit count"] >= 2).sum(), total, "#8E44AD"))
    c6.plotly_chart(pie("🧳 Late", (df["Submission hour"] >= time(18, 0)).sum(), total, "#34495E"))

    # ======================
    # QUESTS
    # ======================
    if st.session_state.quest_view:
        st.divider()
        st.header("🗺️ Quest Center")

        quests = load_quests()

        if st.button("🆕 New Quest"):
            st.session_state.quest_view = "new"

        if st.button("📜 All Quests"):
            st.session_state.quest_view = "all"

        if st.button("🎯 My Quests"):
            st.session_state.quest_view = "my"

        # NEW QUEST
        if st.session_state.quest_view == "new":
            with st.form("new_quest"):
                name = st.text_input("🏷️ Name the new quest")
                desc = st.text_area("📝 Describe the quest")
                dl = st.date_input("⏳ Deadline")
                owner = st.selectbox("👤 Owner", DESIGNERS)
                if st.form_submit_button("✅ Finish"):
                    quests.append({
                        "name": name,
                        "desc": desc,
                        "deadline": str(dl),
                        "owner": owner,
                        "done": False
                    })
                    save_quests(quests)
                    st.success("Quest added!")

        # ALL QUESTS
        if st.session_state.quest_view == "all":
            who = st.selectbox("⚔️ Whose quests?", DESIGNERS)
            for q in [x for x in quests if x["owner"] == who]:
                st.markdown(f"### 🏆 {q['name']}")
                st.caption(q["desc"])
                st.write(f"⏰ Deadline: {q['deadline']}")
                st.write("✅ Done" if q["done"] else "⬜ Not done")

        # MY QUESTS
        if st.session_state.quest_view == "my":
            owner = selected.replace(" KPI", "")
            for q in [x for x in quests if x["owner"] == owner]:
                st.markdown(f"### 🎯 {q['name']}")
                st.caption(q["desc"])
                st.write(f"⏰ Deadline: {q['deadline']}")
                st.write("✅ Done" if q["done"] else "⬜ Not done")
