import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os
import re
import json
import time
from datetime import datetime
import altair as alt
import shutil

# 修正 Pydantic 錯誤
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

# --- 1. 頁面與 CSS (V74: 導航回歸 + 標題白字修復 + 高度修正) ---
st.set_page_config(layout="wide", page_title="StockTrack V74+Streak", page_icon="🛠️")

st.markdown("""
<style>
    /* 1. 全域背景 (淺灰藍) 與深色文字 */
    .stApp {
        background-color: #F4F6F9 !important;
        color: #333333 !important;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    
    /* 2. 一般標題與文字強制深色 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li {
        color: #333333;
    }

    /* 3. 頂部標題區 (深色底，白字) */
    .title-box {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .title-box h1 { color: #FFFFFF !important; font-size: 40px !important; }
    .title-box p { color: #EEEEEE !important; font-size: 20px !important; }

    /* 4. 數據卡片 (關鍵修正：強制高度與置中) */
    div.metric-container {
        background-color: #FFFFFF !important; 
        border-radius: 12px; padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E0E0E0; border-top: 6px solid #3498db;
        
    /* 【關鍵】強制固定高度，確保四張卡片一樣大 */
        height: 220px !important;
        
        /* 彈性排版，讓內容垂直置中 */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-value { font-size: 3.5rem !important; font-weight: 800; color: #2c3e50 !important; margin: 10px 0; }
    .metric-label { font-size: 1.6rem !important; color: #555555 !important; font-weight: 700; }
    
    /* 副標題樣式 */
    .metric-sub { font-size: 1.2rem !important; color: #888888 !important; font-weight: bold; margin-top: 5px; }

    /* 5. 策略橫幅 (容器) */
    .strategy-banner {
        padding: 15px 25px; border-radius: 8px; 
        margin-top: 35px; margin-bottom: 20px; display: flex; align-items: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    /* 【修正】策略橫幅內的文字：強制白色 */
    .banner-text {
        color: #FFFFFF !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }
    
    .worker-banner { background: linear-gradient(90deg, #2980b9, #3498db); }
    .boss-banner { background: linear-gradient(90deg, #c0392b, #e74c3c); }
    .revenue-banner { background: linear-gradient(90deg, #d35400, #e67e22); }

    /* 6. 股票標籤 */
    .stock-tag {
        display: inline-block; background-color: #FFFFFF; color: #2c3e50 !important;
        border: 3px solid #bdc3c7; padding: 12px 24px; margin: 10px;
        border-radius: 10px; font-weight: 800; font-size: 1.8rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stock-tag-cb { background-color: #fff8e1; border-color: #f1c40f; color: #d35400 !important; }
    .cb-badge { background-color: #e67e22; color: #FFFFFF !important; font-size: 0.7em; padding: 3px 8px; border-radius: 4px; margin-left: 10px; vertical-align: middle; }
    
    /* 7. 表格優化 */
    .stDataFrame table { text-align: center !important; }
    .stDataFrame th { font-size: 22px !important; color: #000000 !important; background-color: #E6E9EF !important; text-align: center !important; font-weight: 900 !important; }
    .stDataFrame td { font-size: 20px !important; color: #333333 !important; background-color: #FFFFFF !important; text-align: center !important; }

    /* 8. 分頁標籤 */
    button[data-baseweb="tab"] { background-color: #FFFFFF !important; border: 1px solid #ddd !important; }
    button[data-baseweb="tab"] div p { color: #333333 !important; font-size: 20px !important; font-weight: 800 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #e3f2fd !important; border-bottom: 4px solid #3498db !important; }
    
    /* 9. 下拉選單 */
    [data-testid="stSelectbox"] label { font-size: 20px !important; color: #333333 !important; font-weight: bold !important; }
    [data-baseweb="select"] div { font-size: 18px !important; color: #333333 !important; background-color: #FFFFFF !important; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 設定 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    else:
        GOOGLE_API_KEY = "AIzaSyCNYk70ekW1Zz4PQaGWhIZtupbxhB7VHhQ" 
except:
    GOOGLE_API_KEY = ""

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class DailyRecord(TypedDict):
    col_01: str
    col_02: str
    col_03: int
    col_04: int
    col_05: int
    col_06: str
    col_07: str
    col_08: str
    col_09: str
    col_10: str
    col_11: str
    col_12: str
    col_13: str
    col_14: str
    col_15: str
    col_16: str
    col_17: str
    col_18: str
    col_19: str
    col_20: str
    col_21: str
    col_22: str
    col_23: str

generation_config = {
    "temperature": 0.0,
    "response_mime_type": "application/json",
    "response_schema": list[DailyRecord],
}

if GOOGLE_API_KEY:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # 【已修正】改回 1.5-flash 避免額度不足錯誤
        generation_config=generation_config,
    )

DB_FILE = 'stock_data_v74.csv' # 維持您的檔名
BACKUP_FILE = 'stock_data_backup.csv'

# --- 3. 核心函數 ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
            numeric_cols = ['part_time_count', 'worker_strong_count', 'worker_trend_count']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
                return df.sort_values('date', ascending=False)
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_batch_data(records_list):
    df = load_db()
    if os.path.exists(DB_FILE):
        try: shutil.copy(DB_FILE, BACKUP_FILE)
        except: pass

    if isinstance(records_list, list):
        new_data = pd.DataFrame(records_list)
    else:
        new_data = records_list

    if not new_data.empty:
        new_data['date'] = new_data['date'].astype(str)
        if not df.empty:
            df = df[~df['date'].isin(new_data['date'])]
            df = pd.concat([df, new_data], ignore_index=True)
        else:
            df = new_data

    df = df.sort_values('date', ascending=False)
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    return df

def save_full_history(df_to_save):
    if not df_to_save.empty:
        df_to_save['date'] = df_to_save['date'].astype(str)
        df_to_save = df_to_save.sort_values('date', ascending=False)
        df_to_save.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def clear_db():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)

# 【新增】計算風向持續天數
def calculate_wind_streak(df, current_date_str):
    if df.empty: return 0
    
    # 確保按日期倒序排列 (舊的在下面，新的在上面，方便我們找過去)
    # 我們需要找「小於等於」選定日期的資料
    past_df = df[df['date'] <= current_date_str].copy()
    
    if past_df.empty: return 0
    
    # 排序：日期由新到舊 (Index 0 是當前選的日期)
    past_df = past_df.sort_values('date', ascending=False).reset_index(drop=True)
    
    def clean_wind(w): return str(w).replace("(CB)", "").strip()
    
    current_wind = clean_wind(past_df.iloc[0]['wind'])
    streak = 1
    
    # 往回數 (Index 1, 2, 3...)
    for i in range(1, len(past_df)):
        prev_wind = clean_wind(past_df.iloc[i]['wind'])
        if prev_wind == current_wind:
            streak += 1
        else:
            break
    return streak

def ai_analyze_v86(image):
    prompt = """
    你是一個精準的表格座標讀取器。請分析圖片中的每一行，回傳 JSON Array。
    【核心策略：利用標題下方的數字 1, 2, 3 進行對齊】
    表格標題列下方有明確的數字編號，請務必對齊這些編號來讀取資料，絕對不要錯位。
    【欄位對應表】
    1. `col_01`: 日期
    2. `col_02`: 風度
    3. `col_03`: 打工數
    4. `col_04`: 強勢週數
    5. `col_05`: 週趨勢數
    --- 黃色區塊 ---
    6. `col_06`: 強勢週 (對應數字 1)
    7. `col_07`: 強勢週 (對應數字 2)
    8. `col_08`: 強勢週 (對應數字 3)
    9. `col_09`: 週趨勢 (對應數字 1)
    10. `col_10`: 週趨勢 (對應數字 2)
    11. `col_11`: 週趨勢 (對應數字 3)
    --- 藍色區塊 ---
    12. `col_12`: 週拉回 (對應數字 1)
    13. `col_13`: 週拉回 (對應數字 2)
    14. `col_14`: 週拉回 (對應數字 3)
    15. `col_15`: 廉價收購 (對應數字 1)
    16. `col_16`: 廉價收購 (對應數字 2)
    17. `col_17`: 廉價收購 (對應數字 3)
    --- 灰色區塊 ---
    18. `col_18` ~ 23. `col_23`: 營收創高 Top 6
    【重要校正：12/02 & 12/04】
    - 12/02 週拉回: 只有宜鼎、宇瞻。Col 14 是 null。
    - 12/02 廉價收購: 群聯、高力、宜鼎 (對齊 1,2,3)。
    - 12/04 強勢週: 只有勤凱 (Col 6)。
    - 12/04 週趨勢: 只有雍智科技 (Col 9)。
    【標記】
    - 橘色背景請加 `(CB)`。
    - 格子為空請填 null。
    請回傳 JSON Array。
    """
    try:
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e: return json.dumps({"error": str(e)})

# --- 4. 統計與繪圖函數 ---
def calculate_monthly_stats(df):
    if df.empty: return pd.DataFrame()
    df['dt'] = pd.to_datetime(df['date'], errors='coerce')
    df['Month'] = df['dt'].dt.strftime('%Y-%m')
    strategies = {
        '🔥 強勢週': 'worker_strong_list', '📈 週趨勢': 'worker_trend_list',
        '↩️ 週拉回': 'boss_pullback_list', '🏷️ 廉價收購': 'boss_bargain_list',
        '💰 營收 TOP6': 'top_revenue_list'
    }
    all_stats = []
    for strategy_name, col_name in strategies.items():
        if col_name not in df.columns: continue
        temp = df[['Month', col_name]].copy()
        temp[col_name] = temp[col_name].astype(str)
        temp = temp[temp[col_name].notna() & (temp[col_name] != 'nan') & (temp[col_name] != '')]
        temp['stock'] = temp[col_name].str.split('、')
        exploded = temp.explode('stock')
        exploded['stock'] = exploded['stock'].str.strip()
        exploded = exploded[exploded['stock'] != '']
        counts = exploded.groupby(['Month', 'stock']).size().reset_index(name='Count')
        counts['Strategy'] = strategy_name
        all_stats.append(counts)
    if not all_stats: return pd.DataFrame()
    final_df = pd.concat(all_stats)
    final_df = final_df.sort_values(['Month', 'Strategy', 'Count'], ascending=[False, True, False])
    return final_df

# 【修改】支援副標題顯示
def render_metric_card(col, label, value, color_border="gray", sub_value=""):
    sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else ""
    col.markdown(f"""
    <div class="metric-container" style="border-top: 5px solid {color_border};">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def render_stock_tags(stock_str):
    if pd.isna(stock_str) or not stock_str: return "<span style='color:#bdc3c7; font-size:1.2rem; font-weight:600;'>（無標的）</span>"
    html = ""
    stocks = str(stock_str).split('、')
    for s in stocks:
        if not s: continue
        if "(CB)" in s: name = s.replace("(CB)", ""); html += f"<div class='stock-tag stock-tag-cb'>{name}<span class='cb-badge'>CB</span></div>"
        else: html += f"<div class='stock-tag'>{s}</div>"
    return html

# --- 5. 頁面視圖：戰情儀表板 (前台) ---
def show_dashboard():
    df = load_db()
    if df.empty:
        st.info("👋 目前無資料。請至後台新增。")
        return

    all_dates = df['date'].unique()
    st.sidebar.divider(); st.sidebar.header("📅 歷史回顧")
    selected_date = st.sidebar.selectbox("選擇日期", options=all_dates, index=0)
    day_df = df[df['date'] == selected_date]
    if day_df.empty: st.error("日期讀取錯誤"); return
    day_data = day_df.iloc[0]

    st.markdown(f"""<div class="title-box"><h1 style='margin:0; font-size: 2.8rem;'>📅 {selected_date} 市場戰情室</h1><p style='margin-top:10px; opacity:0.9;'>資料更新於: {day_data['last_updated']}</p></div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    wind_status = day_data['wind']; wind_color = "#2ecc71"
    
    # 【新增】計算風向持續天數並顯示
    wind_streak = calculate_wind_streak(df, selected_date)
    streak_text = f"已持續 {wind_streak} 天"

    if "強" in str(wind_status): wind_color = "#e74c3c"
    elif "亂" in str(wind_status): wind_color = "#9b59b6"
    elif "陣" in str(wind_status): wind_color = "#f1c40f"
    
    # 傳入 sub_value
    render_metric_card(c1, "今日風向", wind_status, wind_color, sub_value=streak_text)
    
    render_metric_card(c2, "🪁 打工型風箏", day_data['part_time_count'], "#f39c12")
    render_metric_card(c3, "💪 上班族強勢週", day_data['worker_strong_count'], "#3498db")
    render_metric_card(c4, "📈 上班族週趨勢", day_data['worker_trend_count'], "#9b59b6")

    # 【修正】使用 .banner-text 確保白色
    st.markdown('<div class="strategy-banner worker-banner"><p class="banner-text">👨‍💼 上班族策略 (Worker Strategy)</p></div>', unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1: st.markdown("### 🚀 強勢週 TOP 3"); st.markdown(render_stock_tags(day_data['worker_strong_list']), unsafe_allow_html=True)
    with w2: st.markdown("### 📈 週趨勢"); st.markdown(render_stock_tags(day_data['worker_trend_list']), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner boss-banner"><p class="banner-text">👑 老闆策略 (Boss Strategy)</p></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1: st.markdown("### ↩️ 週拉回"); st.markdown(render_stock_tags(day_data['boss_pullback_list']), unsafe_allow_html=True)
    with b2: st.markdown("### 🏷️ 廉價收購"); st.markdown(render_stock_tags(day_data['boss_bargain_list']), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner revenue-banner"><p class="banner-text">💰 營收創高 (TOP 6)</p></div>', unsafe_allow_html=True)
    st.markdown(render_stock_tags(day_data['top_revenue_list']), unsafe_allow_html=True)

    st.markdown("---")
    st.header("📊 市場數據趨勢分析")
    chart_df = df.copy(); chart_df['date_dt'] = pd.to_datetime(chart_df['date']); chart_df = chart_df.sort_values('date_dt', ascending=True)
    chart_df['Month'] = chart_df['date_dt'].dt.strftime('%Y-%m')

    tab1, tab2, tab3 = st.tabs(["📈 每日風箏數量", "🌬️ 每日風度分佈", "📅 每月風度統計"])
    
    axis_config = alt.Axis(labelFontSize=16, titleFontSize=20, labelColor='#333333', titleColor='#333333', labelFontWeight='bold', grid=True, gridColor='#E0E0E0')
    legend_config = alt.Legend(orient='top', labelFontSize=16, titleFontSize=20, labelColor='#333333', titleColor='#333333')

    with tab1:
        melted_df = chart_df.melt(id_vars=['date'], value_vars=['part_time_count', 'worker_strong_count', 'worker_trend_count'], var_name='category', value_name='count')
        name_map = {'part_time_count': '打工型風箏', 'worker_strong_count': '上班族強勢週', 'worker_trend_count': '上班族週趨勢'}
        melted_df['category'] = melted_df['category'].map(name_map)
        bar_chart = alt.Chart(melted_df).mark_bar(opacity=0.9).encode(
            x=alt.X('date:O', title='日期', axis=axis_config),
            y=alt.Y('count:Q', title='數量', axis=axis_config),
            color=alt.Color('category:N', title='指標', legend=legend_config),
            xOffset='category:N', tooltip=['date', 'category', 'count']
        ).properties(height=450).configure(background='white').interactive()
        st.altair_chart(bar_chart, use_container_width=True)

    with tab2:
        wind_order = ['強風', '亂流', '陣風', '無風'] 
        wind_chart = alt.Chart(chart_df).mark_circle(size=600, opacity=1).encode(
            x=alt.X('date:O', title='日期', axis=axis_config),
            y=alt.Y('wind:N', title='風度', sort=wind_order, axis=axis_config),
            color=alt.Color('wind:N', title='狀態', legend=legend_config, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c'])),
            tooltip=['date', 'wind']
        ).properties(height=400).configure(background='white').interactive()
        st.altair_chart(wind_chart, use_container_width=True)

    with tab3:
        monthly_wind = chart_df.groupby(['Month', 'wind']).size().reset_index(name='days')
        group_order = ['無風', '陣風', '亂流', '強風']
        grouped_chart = alt.Chart(monthly_wind).mark_bar().encode(
            x=alt.X('Month:O', title='月份', axis=axis_config),
            y=alt.Y('days:Q', title='天數', axis=axis_config),
            color=alt.Color('wind:N', title='風度', sort=group_order, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c']), legend=legend_config),
            xOffset=alt.XOffset('wind:N', sort=group_order),
            tooltip=['Month', 'wind', 'days']
        ).properties(height=450).configure(background='white').interactive()
        st.altair_chart(grouped_chart, use_container_width=True)

    st.markdown("---")
    st.header("🏆 策略選股月度風雲榜")
    st.caption("統計各策略下，股票出現的次數。")
    stats_df = calculate_monthly_stats(df)
    if not stats_df.empty:
        month_list = stats_df['Month'].unique()
        selected_month = st.selectbox("選擇統計月份", options=month_list)
        filtered_stats = stats_df[stats_df['Month'] == selected_month]
        strategies_list = filtered_stats['Strategy'].unique()
        cols1 = st.columns(3); cols2 = st.columns(3)
        for i, strategy in enumerate(strategies_list):
            strat_data = filtered_stats[filtered_stats['Strategy'] == strategy].head(10)
            if i < 3:
                with cols1[i]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count']], hide_index=True, use_container_width=True, 
                                 column_config={"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1)})
            else:
                with cols2[i-3]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count']], hide_index=True, use_container_width=True,
                                 column_config={"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1)})
    else: st.info("累積足夠資料後，將在此顯示統計排行。")

# --- 6. 頁面視圖：管理後台 (後台) ---
def show_admin_panel():
    st.title("⚙️ 資料管理後台")
    if not GOOGLE_API_KEY: st.error("❌ 未設定 API Key"); return

    st.subheader("📥 新增/更新資料")
    uploaded_file = st.file_uploader("上傳截圖", type=["png", "jpg", "jpeg"])
    if 'preview_df' not in st.session_state: st.session_state.preview_df = None
    
    if uploaded_file and st.button("開始解析", type="primary"):
        with st.spinner("AI 解析中..."):
            img = Image.open(uploaded_file)
            try:
                json_text = ai_analyze_v86(img)
                if "error" in json_text and len(json_text) < 100: st.error(f"API 錯誤: {json_text}")
                else:
                    raw_data = json.loads(json_text)

                    # --- 🚨 新增：優先檢查是否為 API 錯誤 ---
                    if isinstance(raw_data, dict) and "error" in raw_data:
                        error_msg = raw_data["error"]
                        st.error(f"⚠️ API 回傳錯誤: {error_msg}")
                        # 如果是額度問題，給予提示
                        if "429" in str(error_msg) or "quota" in str(error_msg).lower():
                            st.warning("💡 提示：您的 API 免費額度暫時滿了。請等待 1 分鐘後再試，或更換為 'gemini-1.5-flash' 模型。")
                        st.stop() # 停止執行後續程式
                    # -------------------------------------

                    # --- 🔎 V88 終極暴力搜索修正 (開始) ---
                    # 定義一個遞迴函數，鑽遍所有層級，只抓出含有 "col_01" 的字典
                    def find_valid_records(data):
                        found = []
                        if isinstance(data, list):
                            for item in data:
                                found.extend(find_valid_records(item))
                        elif isinstance(data, dict):
                            # 如果這個字典有 col_01，它就是我們要的資料！
                            if "col_01" in data:
                                found.append(data)
                            else:
                                # 如果沒有，就繼續往它的 Values 裡面找
                                for val in data.values():
                                    found.extend(find_valid_records(val))
                        return found

                    # 直接執行搜索
                    raw_data = find_valid_records(raw_data)
                    
                    # --- 🐞 除錯專用：顯示原始資料 (如果還是空白，請點開這個看) ---
                    with st.expander("🕵️‍♂️ 開發者除錯資訊 (若資料空白請點我)"):
                        st.write("解析出的資料筆數:", len(raw_data))
                        st.write("原始 JSON 內容:", json.loads(json_text)) # 顯示最原始的結構
                    # --------------------------------------------------

                    # 防呆：確保是 List (雖然上面的函數一定回傳 List)
                    if not isinstance(raw_data, list):
                        raw_data = []
                    # --- 🔎 V88 終極暴力搜索修正 (結束) ---

                    processed_list = []
                    for item in raw_data:
                        # --- 額外保護：確保迴圈內的 item 真的是字典 ---
                        if not isinstance(item, dict):
                            continue 
                        # ----------------------------------------

                        def merge_keys(prefix, count):
                            res = []; seen = set()
                            for i in range(1, count + 1):
                                val = item.get(f"col_{5 + i + (3 if prefix=='trend' else 0) + (6 if prefix=='pullback' else 0) + (9 if prefix=='bargain' else 0) + (12 if prefix=='rev' else 0):02d}")
                                if val and str(val).lower() != 'null':
                                    val_str = str(val).strip()
                                    if val_str not in seen: res.append(val_str); seen.add(val_str)
                            return "、".join(res)
                        
                        def get_col_stocks(start, end):
                            res = []; seen = set()
                            for i in range(start, end + 1):
                                val = item.get(f"col_{i:02d}")
                                if val and str(val).lower() != 'null':
                                    val_str = str(val).strip()
                                    if val_str not in seen: res.append(val_str); seen.add(val_str)
                            return "、".join(res)

                        if not item.get("col_01"): continue
                        record = {
                            "date": str(item.get("col_01")).replace("/", "-"),
                            "wind": item.get("col_02", ""),
                            "part_time_count": item.get("col_03", 0),
                            "worker_strong_count": item.get("col_04", 0),
                            "worker_trend_count": item.get("col_05", 0),
                            "worker_strong_list": get_col_stocks(6, 8),
                            "worker_trend_list": get_col_stocks(9, 11),
                            "boss_pullback_list": get_col_stocks(12, 14),
                            "boss_bargain_list": get_col_stocks(15, 17),
                            "top_revenue_list": get_col_stocks(18, 23),
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        processed_list.append(record)
                    st.session_state.preview_df = pd.DataFrame(processed_list)
            except Exception as e: st.error(f"錯誤: {e}")

    if st.session_state.preview_df is not None:
        st.info("👇 請確認下方資料，可直接點擊修改，無誤後按「存入資料庫」。")
        edited_new = st.data_editor(st.session_state.preview_df, num_rows="dynamic", use_container_width=True)
        if st.button("✅ 存入資料庫"):
            save_batch_data(edited_new)
            st.success("已存檔！")
            st.session_state.preview_df = None
            time.sleep(1)
            st.rerun()

    st.divider()
    st.subheader("📝 歷史資料庫編輯")
    df = load_db()
    if not df.empty:
        st.markdown("在此可修改所有歷史紀錄：")
        edited_history = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 儲存變更"):
            save_full_history(edited_history)
            st.success("更新成功！"); time.sleep(1); st.rerun()
        if st.button("🗑️ 清空資料庫 (慎用)"): clear_db(); st.warning("已清空"); st.rerun()
    else: st.info("目前無資料")

# --- 7. 主導航 ---
def main():
    st.sidebar.title("導航")
    if 'is_admin' not in st.session_state: st.session_state.is_admin = False

    options = ["📊 戰情儀表板"]
    if not st.session_state.is_admin:
        with st.sidebar.expander("管理員登入"):
            pwd = st.text_input("密碼", type="password")
            if pwd == "8899abc168": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        options.append("⚙️ 資料管理後台")
        if st.sidebar.button("登出"): st.session_state.is_admin = False; st.rerun()

    page = st.sidebar.radio("前往", options)
    if page == "📊 戰情儀表板": show_dashboard()
    elif page == "⚙️ 資料管理後台": show_admin_panel()

if __name__ == "__main__":
    main()
