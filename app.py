import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# NEW: TREND ANALYSIS STATE
# ======================
if "trend_filters" not in st.session_state:
    st.session_state.trend_filters = {
        "selected_kpi": "Ghorme Sabzi",
        "selected_designers": ["Team (All)"],
        "time_range": "Monthly",
        "password_inputs": {
            "Sajad": "",
            "Romina": "",
            "Melika": "", 
            "Fatemeh": ""
        },
        "password_verified": {
            "Sajad": False,
            "Romina": False,
            "Melika": False,
            "Fatemeh": False
        }
    }

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
# CHART FUNCTIONS
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
# TREND ANALYSIS FUNCTIONS
# ======================
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

def get_chart_colors():
    """دریافت رنگ‌ها بر اساس تم Streamlit"""
    # رنگ‌های پیش‌فرض برای لایت مود
    colors = {
        "background": "#FFFFFF",
        "text": "#000000",
        "grid": "#E5ECF6",
        "plot_bg": "#FFFFFF",
        "paper_bg": "#FFFFFF"
    }
    
    # اگر تم دارک فعال است
    try:
        # این رنگ‌ها با تم دارک Streamlit سازگار هستند
        if st.get_option("theme.base") == "dark":
            colors = {
                "background": "#0E1117",
                "text": "#FAFAFA",
                "grid": "#262730",
                "plot_bg": "#0E1117",
                "paper_bg": "#0E1117"
            }
    except:
        pass
    
    return colors

def create_multi_line_chart(df_all, kpi_name, time_range, selected_designers, holidays):
    """ایجاد نمودار چند خطی برای مقایسه طراحان"""
    
    kpi_options = get_kpi_options()
    emoji = kpi_options[kpi_name]["emoji"]
    
    # دریافت رنگ‌ها بر اساس تم
    theme_colors = get_chart_colors()
    
    # رنگ‌های متمایز برای هر طراح (با سازگاری با هر دو تم)
    color_palette = {
        "Team (All)": "#3498DB",  # آبی روشن
        "Sajad": "#2ECC71",       # سبز
        "Romina": "#E74C3C",      # قرمز
        "Melika": "#9B59B6",      # بنفش
        "Fatemeh": "#F39C12"      # نارنجی
    }
    
    # اگر تم دارک است، رنگ‌های روشن‌تر استفاده کن
    if theme_colors["background"] == "#0E1117":
        color_palette = {
            "Team (All)": "#1ABC9C",  # فیروزه‌ای
            "Sajad": "#2ECC71",       # سبز
            "Romina": "#E74C3C",      # قرمز
            "Melika": "#9B59B6",      # بنفش
            "Fatemeh": "#F1C40F"      # زرد
        }
    
    # ترجمه عنوان‌ها
    time_range_titles = {
        "Monthly": "ماه گذشته (روزانه)",
        "Annually": "یک سال گذشته (ماهانه)",
        "All time": "کل زمان (ماهانه)"
    }
    
    all_data = []
    
    for designer in selected_designers:
        # فیلتر کردن داده‌ها برای هر طراح
        if designer == "Team (All)":
            df_designer = df_all
            display_name = "تیم"
        else:
            df_designer = df_all[df_all["Designer Name"] == designer]
            display_name = designer
        
        if df_designer.empty:
            continue
        
        # آماده‌سازی داده‌ها
        df = df_designer.copy()
        df["year_month"] = df["Submission date"].dt.to_period("M")
        
        if time_range == "Monthly":
            # روند روزانه
            end_date = df["Submission date"].max()
            start_date = end_date - pd.Timedelta(days=30)
            df_period = df[df["Submission date"] >= start_date]
            
            if df_period.empty:
                continue
            
            # گروه‌بندی روزانه
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
        
        else:  # Annually یا All time
            if time_range == "Annually":
                end_date = df["Submission date"].max()
                start_date = end_date - pd.DateOffset(months=11)
                df_period = df[df["Submission date"] >= start_date]
            else:  # All time
                df_period = df
            
            if df_period.empty:
                continue
            
            # گروه‌بندی ماهانه
            monthly_stats = df_period.groupby("year_month").apply(
                lambda x: calculate_kpi(x, kpi_name, holidays)
            ).reset_index(name="value")
            
            monthly_stats["designer"] = display_name
            monthly_stats["time_label"] = monthly_stats["year_month"].dt.strftime("%Y-%m")
            
            all_data.append(monthly_stats)
    
    if not all_data:
        return None
    
    # ترکیب همه داده‌ها
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # ایجاد نمودار چند خطی
    title = f"{emoji} {kpi_name} Trend - {time_range_titles[time_range]}"
    
    fig = px.line(
        combined_df,
        x="time_label",
        y="value",
        color="designer",
        title=title,
        markers=True,
        color_discrete_map={k: color_palette.get(k, "#000000") for k in combined_df["designer"].unique()}
    )
    
    # تنظیمات ظاهری با توجه به تم
    fig.update_layout(
        xaxis_title="زمان",
        yaxis_title="تعداد",
        hovermode="x unified",
        height=550,
        legend_title="طراح",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor=theme_colors["paper_bg"],
            font=dict(color=theme_colors["text"])
        ),
        plot_bgcolor=theme_colors["plot_bg"],
        paper_bgcolor=theme_colors["paper_bg"],
        font=dict(color=theme_colors["text"])
    )
    
    # تنظیمات محورها
    fig.update_xaxes(
        gridcolor=theme_colors["grid"],
        zerolinecolor=theme_colors["grid"],
        linecolor=theme_colors["grid"]
    )
    
    fig.update_yaxes(
        gridcolor=theme_colors["grid"],
        zerolinecolor=theme_colors["grid"],
        linecolor=theme_colors["grid"]
    )
    
    # تنظیم ضخامت و رنگ خطوط
    for trace in fig.data:
        trace.line.width = 3
        trace.marker.size = 8
    
    return fig

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.title("📊 KPI Dashboard")
    
    # نمایش منو فقط وقتی که مرحله done هستیم
    if st.session_state.step == "done":
        # منوی ناوبری اصلی
        menu_options = ["kpi", "quests", "trend"]
        menu_labels = ["KPI Dashboard", "Quests", "نمودار روند"]
        
        selected = st.radio(
            "منو",
            options=menu_options,
            format_func=lambda x: dict(zip(menu_options, menu_labels))[x],
            index=menu_options.index(st.session_state.active_page)
        )
        
        if selected != st.session_state.active_page:
            st.session_state.active_page = selected
            st.rerun()
    
    # دکمه شروع مجدد (فقط در حالت KPI)
    if st.session_state.active_page == "kpi" and st.session_state.step == "done":
        if st.button("🔄 شروع دوباره"):
            st.session_state.step = "upload"
            st.session_state.df_clean = None
            st.session_state.holidays = []
            st.session_state.auth_ok = {}
            st.session_state.active_page = "kpi"
            st.session_state.current_user = None
            st.session_state.trend_filters = {
                "selected_kpi": "Ghorme Sabzi",
                "selected_designers": ["Team (All)"],
                "time_range": "Monthly",
                "password_inputs": {
                    "Sajad": "",
                    "Romina": "",
                    "Melika": "", 
                    "Fatemeh": ""
                },
                "password_verified": {
                    "Sajad": False,
                    "Romina": False,
                    "Melika": False,
                    "Fatemeh": False
                }
            }
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
# STEP 3 — MAIN DASHBOARD
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
    # TREND ANALYSIS PAGE
    # ======================
    elif st.session_state.active_page == "trend":
        st.header("📈 نمودار روند")
        
        # دکمه بازگشت
        if st.button("⬅️ بازگشت به داشبورد KPI"):
            st.session_state.active_page = "kpi"
            st.rerun()
        
        df_all = st.session_state.df_clean.copy()
        
        # ======================
        # فیلترها در سایدبار
        # ======================
        with st.sidebar:
            if st.session_state.active_page == "trend":
                st.markdown("---")
                st.subheader("⚙️ فیلترهای نمودار روند")
                
                # 1. فیلتر KPI
                kpi_options = get_kpi_options()
                selected_kpi = st.selectbox(
                    "📊 Select KPI:",
                    options=list(kpi_options.keys()),
                    index=list(kpi_options.keys()).index(st.session_state.trend_filters["selected_kpi"])
                )
                st.session_state.trend_filters["selected_kpi"] = selected_kpi
                
                st.markdown("---")
                
                # 2. فیلتر طراحان
                st.markdown("👤 **Designers:**")
                designers = ["Sajad", "Romina", "Melika", "Fatemeh", "Team (All)"]
                
                selected_designers = []
                for designer in designers:
                    if designer == "Team (All)":
                        if st.checkbox("Team (All)", 
                                      value="Team (All)" in st.session_state.trend_filters["selected_designers"],
                                      key=f"check_all"):
                            if "Team (All)" not in selected_designers:
                                selected_designers.append("Team (All)")
                    else:
                        if st.checkbox(designer, 
                                      value=designer in st.session_state.trend_filters["selected_designers"],
                                      key=f"check_{designer}"):
                            if designer not in selected_designers:
                                selected_designers.append(designer)
                
                st.session_state.trend_filters["selected_designers"] = selected_designers
                
                st.markdown("---")
                
                # 3. فیلتر بازه زمانی
                time_options = ["Monthly", "Annually", "All time"]
                selected_time = st.radio(
                    "📅 Time Range:",
                    options=time_options,
                    index=time_options.index(st.session_state.trend_filters["time_range"])
                )
                st.session_state.trend_filters["time_range"] = selected_time
                
                st.markdown("---")
                
                # 4. ورود پسورد برای طراحان انتخاب شده
                if selected_designers:
                    # فقط طراحان فردی (نه Team All)
                    individual_designers = [d for d in selected_designers if d != "Team (All)"]
                    
                    if individual_designers:
                        st.markdown("🔐 **ورود پسورد:**")
                        
                        passwords = {
                            "Sajad": "2232245",
                            "Romina": "112131",
                            "Melika": "122232",
                            "Fatemeh": "132333"
                        }
                        
                        for designer in individual_designers:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                password_input = st.text_input(
                                    f"پسورد {designer}",
                                    type="password",
                                    value=st.session_state.trend_filters["password_inputs"][designer],
                                    key=f"pwd_{designer}"
                                )
                                st.session_state.trend_filters["password_inputs"][designer] = password_input
                            
                            with col2:
                                if st.button("تایید", key=f"verify_{designer}"):
                                    if password_input == passwords[designer]:
                                        st.session_state.trend_filters["password_verified"][designer] = True
                                        st.success(f"✅ {designer} تأیید شد")
                                        st.rerun()
                                    else:
                                        st.session_state.trend_filters["password_verified"][designer] = False
                                        st.error(f"❌ پسورد {designer} اشتباه است")
                                        st.rerun()
                            
                            # نمایش وضعیت تأیید
                            if st.session_state.trend_filters["password_verified"][designer]:
                                st.success(f"✅ {designer} تأیید شده")
                            else:
                                st.warning(f"⚠️ {designer} نیاز به تأیید")
                
                st.markdown("---")
                
                # دکمه اعمال فیلترها
                if st.button("🔄 اعمال فیلترها", type="primary", use_container_width=True):
                    if not st.session_state.trend_filters["selected_designers"]:
                        st.error("⚠️ لطفاً حداقل یک طراح انتخاب کنید")
                    else:
                        st.rerun()
        
        # ======================
        # بررسی احراز هویت برای طراحان انتخاب شده
        # ======================
        unverified_designers = []
        for designer in st.session_state.trend_filters["selected_designers"]:
            if designer != "Team (All)" and not st.session_state.trend_filters["password_verified"][designer]:
                unverified_designers.append(designer)
        
        if unverified_designers:
            st.warning(f"⚠️ نیاز به وارد کردن پسورد برای: {', '.join(unverified_designers)}")
            st.info("لطفاً در پنل سمت چپ پسورد هر طراح را وارد کرده و دکمه 'تایید' را بزنید.")
            st.stop()
        
        # ======================
        # ایجاد نمودار چند خطی
        # ======================
        if st.session_state.trend_filters["selected_designers"]:
            holidays = st.session_state.holidays
            
            fig = create_multi_line_chart(
                df_all,
                st.session_state.trend_filters["selected_kpi"],
                st.session_state.trend_filters["time_range"],
                st.session_state.trend_filters["selected_designers"],
                holidays
            )
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # نمایش آمار خلاصه
                st.markdown("---")
                st.subheader("📊 آمار خلاصه")
                
                cols = st.columns(len(st.session_state.trend_filters["selected_designers"]))
                
                for idx, designer in enumerate(st.session_state.trend_filters["selected_designers"]):
                    with cols[idx]:
                        if designer == "Team (All)":
                            df_filtered = df_all
                            display_name = "تیم"
                        else:
                            df_filtered = df_all[df_all["Designer Name"] == designer]
                            display_name = designer
                        
                        total = len(df_filtered)
                        kpi_value = calculate_kpi(df_filtered, st.session_state.trend_filters["selected_kpi"], holidays)
                        
                        st.metric(
                            label=f"**{display_name}**",
                            value=kpi_value,
                            delta=f"{kpi_value/total*100:.1f}%" if total > 0 else "0%"
                        )
                        st.caption(f"از {total} تسک")
            else:
                st.warning("⚠️ داده‌ای برای نمایش روند یافت نشد")
        else:
            st.warning("⚠️ لطفاً حداقل یک طراح از پنل سمت چپ انتخاب کنید")
    
    # ======================
    # KPI PAGE (اصلی)
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
