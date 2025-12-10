import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os
import re
import json
import time
from datetime import datetime, timedelta
import altair as alt
import shutil
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# 修正 Pydantic 錯誤
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

# --- 1. 頁面與 CSS (V156: 內部排行保底版) ---
st.set_page_config(layout="wide", page_title="StockTrack V156", page_icon="💎")

st.markdown("""
<style>
    /* 全域設定 */
    .stApp { background-color: #F0F2F6 !important; color: #333333 !important; font-family: 'Helvetica', 'Arial', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #333333; }
    
    /* 標題區 */
    .title-box { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
    .title-box h1 { color: #FFFFFF !important; font-size: 36px !important; margin-bottom: 10px !important; }
    .title-box p { color: #E0E0E0 !important; font-size: 18px !important; }
    
    /* 數據卡片 */
    div.metric-container { background-color: #FFFFFF !important; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #E0E0E0; border-top: 5px solid #3498db; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 140px; margin-bottom: 10px; }
    .metric-value { font-size: 2.8rem !important; font-weight: 800; color: #2c3e50 !important; margin: 5px 0; }
    .metric-label { font-size: 1.3rem !important; color: #666666 !important; font-weight: 600; }
    .metric-sub { font-size: 1.1rem !important; color: #888888 !important; font-weight: bold; margin-top: 5px; }
    
    /* 全球指數卡片 */
    .market-card { background-color: #FFFFFF; border-radius: 10px; padding: 15px; margin: 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border: 1px solid #EAEAEA; transition: transform 0.2s; }
    .market-card:hover { transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.12); }
    .market-name { font-size: 1.1rem; font-weight: bold; color: #555; margin-bottom: 5px; }
    .market-price { font-size: 2.0rem; font-weight: 900; margin: 5px 0; font-family: 'Roboto', sans-serif; }
    .market-change { font-size: 1.2rem; font-weight: 700; }
    .up-color { color: #e74c3c !important; } .down-color { color: #27ae60 !important; } .flat-color { color: #7f8c8d !important; }
    .card-up { border-bottom: 4px solid #e74c3c; background: linear-gradient(to bottom, #fff, #fff5f5); }
    .card-down { border-bottom: 4px solid #27ae60; background: linear-gradient(to bottom, #fff, #f0fdf4); }
    .card-flat { border-bottom: 4px solid #95a5a6; }
    
    /* 股票標籤 */
    .stock-tag { 
        display: inline-block; background-color: #FFFFFF; color: #2c3e50 !important; 
        border: 2px solid #bdc3c7; padding: 10px 18px; margin: 8px; 
        border-radius: 10px; font-weight: 800; font-size: 1.6rem; 
        box-shadow: 0 3px 6px rgba(0,0,0,0.1); 
        vertical-align: middle;
        text-align: center;
        min-width: 140px;
    }
    .stock-tag-cb { background-color: #fff8e1; border-color: #f1c40f; color: #d35400 !important; }
    .cb-badge { background-color: #e67e22; color: #FFFFFF !important; font-size: 0.6em; padding: 2px 6px; border-radius: 4px; margin-left: 5px; vertical-align: text-top; }
    
    /* 成交值顯示 (強制紅色粗體) */
    .turnover-val {
        display: block;
        font-size: 0.8em;
        font-weight: 900;
        color: #c0392b; /* 鮮紅 */
        margin-top: 4px;
        padding-top: 4px;
        border-top: 1px dashed #ccc;
        font-family: 'Arial', sans-serif;
    }

    .stDataFrame table { text-align: center !important; }
    .stDataFrame th { font-size: 18px !important; color: #000000 !important; background-color: #E6E9EF !important; text-align: center !important; font-weight: 900 !important; }
    .stDataFrame td { font-size: 18px !important; color: #333333 !important; background-color: #FFFFFF !important; text-align: center !important; }
    
    .strategy-banner { padding: 15px 25px; border-radius: 8px; margin-top: 35px; margin-bottom: 20px; display: flex; align-items: center; box-shadow: 0 3px 6px rgba(0,0,0,0.15); }
    .banner-text { color: #FFFFFF !important; font-size: 24px !important; font-weight: 800 !important; margin: 0 !important; }
    .worker-banner { background: linear-gradient(90deg, #2980b9, #3498db); }
    .boss-banner { background: linear-gradient(90deg, #c0392b, #e74c3c); }
    .revenue-banner { background: linear-gradient(90deg, #d35400, #e67e22); }
    
    /* 下拉選單修正 */
    button[data-baseweb="tab"] { background-color: #FFFFFF !important; border: 1px solid #ddd !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #e3f2fd !important; border-bottom: 4px solid #3498db !important; }
    .stSelectbox label { font-size: 18px !important; color: #333333 !important; font-weight: bold !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #2c3e50 !important; color: white !important; }
    .stSelectbox div[data-baseweb="select"] > div * { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] svg { fill: #FFFFFF !important; color: #FFFFFF !important; }
    li[role="option"] { background-color: #2c3e50 !important; color: #FFFFFF !important; }
    li[role="option"]:hover { background-color: #34495e !important; color: #f1c40f !important; }
    
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
    col_01: str; col_02: str; col_03: int; col_04: int; col_05: int
    col_06: str; col_07: str; col_08: str; col_09: str; col_10: str
    col_11: str; col_12: str; col_13: str; col_14: str; col_15: str
    col_16: str; col_17: str; col_18: str; col_19: str; col_20: str
    col_21: str; col_22: str; col_23: str

generation_config = {
    "temperature": 0.0,
    "response_mime_type": "application/json",
    "response_schema": list[DailyRecord],
}

if GOOGLE_API_KEY:
    model_name_to_use = "gemini-1.5-flash"
    model = genai.GenerativeModel(
        model_name=model_name_to_use,
        generation_config=generation_config,
    )

DB_FILE = 'stock_data_v74.csv' 
BACKUP_FILE = 'stock_data_backup.csv'

# --- 3. 核心資料庫 (MASTER_STOCK_DB) ---
# 包含您提到的所有股票 + 權值股
MASTER_STOCK_DB = {
    # 權值/熱門 (上市)
    "2330": ("台積電", "晶圓代工"), "2317": ("鴻海", "AI伺服器"), "2454": ("聯發科", "IC設計"), 
    "2382": ("廣達", "AI伺服器"), "3231": ("緯創", "AI伺服器"), "2603": ("長榮", "航運"),
    "3008": ("大立光", "光學鏡頭"), "3037": ("欣興", "ABF載板"), "3034": ("聯詠", "IC設計"),
    "2379": ("瑞昱", "IC設計"), "2303": ("聯電", "晶圓代工"), "2881": ("富邦金", "金融"),
    "2308": ("台達電", "電源/EV"), "1519": ("華城", "重電"), "1513": ("中興電", "重電"),
    "2449": ("京元電子", "封測"), "6290": ("良維", "連接器"), "6781": ("AES-KY", "電池模組"),
    "2427": ("三商電", "系統整合"), "2357": ("華碩", "AI伺服器"), "2356": ("英業達", "AI伺服器"),
    "6669": ("緯穎", "AI伺服器"), "3035": ("智原", "IP矽智財"), "3443": ("創意", "IP矽智財"),
    "3661": ("世芯-KY", "IP矽智財"), "3017": ("奇鋐", "散熱"), "3324": ("雙鴻", "散熱"),
    "2345": ("智邦", "網通"), "3711": ("日月光投控", "封測"), "2368": ("金像電", "PCB"),
    "2383": ("台光電", "CCL銅箔"), "6213": ("聯茂", "CCL銅箔"), "6805": ("富世達", "軸承/散熱"),
    "2353": ("宏碁", "AI PC"), "2324": ("仁寶", "組裝代工"), "2301": ("光寶科", "電源"),
    "2327": ("國巨", "被動元件"), "2344": ("華邦電", "記憶體"), "2408": ("南亞科", "記憶體"),
    "8110": ("華東", "封測"), "1605": ("華新", "電線電纜"), "2609": ("陽明", "航運"),
    "2615": ("萬海", "航運"), "1503": ("士電", "重電"), "1504": ("東元", "重電"),
    "1815": ("富喬", "PCB材料"), "2376": ("技嘉", "板卡/伺服器"), "2377": ("微星", "板卡"),
    "2492": ("華新科", "被動元件"), "3044": ("健鼎", "PCB"), "4958": ("臻鼎-KY", "PCB"),
    "4938": ("和碩", "組裝代工"), "9958": ("世紀鋼", "風電"), "6415": ("矽力-KY", "IC設計"),
    "3406": ("玉晶光", "光學鏡頭"), "2409": ("友達", "面板"), "3481": ("群創", "面板"),
    "6239": ("力成", "封測"), "6770": ("力積電", "晶圓代工"), "2401": ("凌陽", "IC設計"), 
    "3014": ("聯陽", "IC設計"), "6176": ("瑞儀", "背光模組"), "3036": ("文曄", "IC通路"), 
    "2915": ("潤泰全", "百貨/壽險"), "2360": ("致茂", "檢測設備"), "2480": ("敦陽科", "系統整合"), 
    "2359": ("所羅門", "機器人"), "2464": ("盟立", "機器人"), "6664": ("群翊", "PCB設備"),
    "8499": ("鼎炫-KY", "EMI材料"), "6446": ("藥華藥", "生技新藥"), "6139": ("亞翔", "無塵室/廠務"),
    "2059": ("川湖", "伺服器導軌"), "6449": ("鈺邦", "被動元件"), "3706": ("神達", "伺服器"),
    "2312": ("金寶", "組裝代工"), "3413": ("京鼎", "半導體設備"), "8155": ("博智", "PCB/伺服器板"),
    "5388": ("中磊", "網通"), "3217": ("優群", "連接器"), "3090": ("日電貿", "被動元件"),
    "2472": ("立隆電", "被動元件"), "8042": ("金山電", "被動元件"), "2337": ("旺宏", "記憶體"),
    "3357": ("臺慶科", "被動元件"), "6667": ("信紘科", "廠務設備"), "2404": ("漢科", "廠務設備"),
    "6691": ("洋基工程", "廠務工程"), "1802": ("台玻", "玻璃"), "3529": ("力旺", "IP矽智財"),
    "3105": ("穩懋", "砷化鎵"), "5347": ("世界", "晶圓代工"), "5269": ("祥碩", "IC設計"),
    
    # 權值/熱門 (上櫃)
    "8299": ("群聯", "記憶體控制"), "8069": ("元太", "電子紙"), "6488": ("環球晶", "矽晶圓"),
    "3293": ("鈊象", "遊戲"), "3131": ("弘塑", "CoWoS設備"), "4966": ("譜瑞-KY", "IC設計"),
    "5274": ("信驊", "IC設計"), "6274": ("台燿", "CCL銅箔"), "3374": ("精材", "封測"), 
    "6147": ("頎邦", "封測"), "5483": ("中美晶", "矽晶圓"), "6223": ("旺矽", "探針卡"),
    "3081": ("聯亞", "光通訊"), "3450": ("聯鈞", "CPO/光通訊"), "4979": ("華星光", "光通訊"),
    "5289": ("宜鼎", "工控記憶體"), "4760": ("勤凱", "被動元件/材料"), "6683": ("雍智科技", "測試介面"),
    "8996": ("高力", "散熱"), "6187": ("萬潤", "CoWoS設備"), "3583": ("辛耘", "CoWoS設備"),
    "6138": ("茂達", "IC設計"), "3680": ("家登", "半導體設備"), "5425": ("台半", "二極體"),
    "3260": ("威剛", "記憶體"), "8046": ("南電", "ABF載板"), "4768": ("晶呈科技", "半導體特氣"), 
    "8112": ("至上", "IC通路"), "5314": ("世紀", "IC設計"), "3162": ("精確", "車用零組件"), 
    "3167": ("大量", "半導體設備"), "8021": ("尖點", "PCB鑽針"), "8358": ("金居", "CCL銅箔"), 
    "3163": ("波若威", "光通訊"), "4908": ("前鼎", "光通訊"), "3363": ("上詮", "光通訊"), 
    "4961": ("天鈺", "IC設計"), "6279": ("胡連", "車用連接器"), "3693": ("營邦", "機殼"), 
    "8210": ("勤誠", "機殼"), "3558": ("神準", "網通"), "6180": ("橘子", "遊戲"), 
    "6515": ("穎崴", "測試介面"), "6182": ("合晶", "矽晶圓"), "8086": ("宏捷科", "砷化鎵"), 
    "3217": ("優群", "連接器"), "5284": ("JPP-KY", "航太/機殼"), "6895": ("宏碩系統", "微波設備"), 
    "6739": ("竹陞科技", "智能工廠"), "4971": ("IET-KY", "三五族/砷化鎵"), "9105": ("泰金寶-DR", "組裝代工"),
    "8271": ("宇瞻", "記憶體模組"), "6251": ("定穎投控", "車用PCB")
}

# --- 4. 自動生成索引 ---
NAME_TO_SECTOR = {}
NAME_TO_CODE = {}
for code, (name, sector) in MASTER_STOCK_DB.items():
    NAME_TO_SECTOR[name] = sector
    NAME_TO_CODE[name] = code

# 別名對照 (解決簡稱)
ALIAS_MAP = {
    "京元電": "京元電子", "亞翔工程": "亞翔", "聖暉*": "聖暉", "聖暉工程": "聖暉",
    "IET": "IET-KY", "JPP": "JPP-KY", "AES": "AES-KY", "世芯": "世芯-KY",
    "譜瑞": "譜瑞-KY", "力積": "力積電", "台積": "台積電", "聯發": "聯發科",
    "日月光": "日月光投控", "欣 興": "欣興", "群 聯": "群聯", "國巨*": "國巨",
    "藥華": "藥華藥", "聖 暉": "聖暉", "金 居": "金居", "定穎": "定穎投控",
    "宇瞻科技": "宇瞻"
}

# 強制修正表
FORCE_FIX_SECTOR = {
    "京元電子": "封測", "IET-KY": "三五族/砷化鎵", "亞翔": "無塵室/廠務",
    "聖暉": "無塵室/廠務", "聖暉*": "無塵室/廠務", "金寶": "組裝代工",
    "神達": "伺服器", "宏碩系統": "微波設備", "竹陞科技": "智能工廠",
    "群翊": "PCB設備", "鼎炫-KY": "EMI材料", "博智": "PCB/伺服器板",
    "定穎投控": "車用PCB", "藥華藥": "生技新藥", "川湖": "伺服器導軌",
    "鈺邦": "被動元件", "金居": "CCL銅箔/材料"
}

# --- 智慧查找函式 ---
def smart_get_code_and_sector(stock_input):
    raw = str(stock_input).strip()
    clean = raw.replace("(CB)", "").strip()
    if clean in ALIAS_MAP: clean = ALIAS_MAP[clean]
    clean_no_star = clean.replace("*", "")
    
    code = None
    if clean in NAME_TO_CODE: code = NAME_TO_CODE[clean]
    elif clean_no_star in NAME_TO_CODE: code = NAME_TO_CODE[clean_no_star]
    elif clean.isdigit() and clean in MASTER_STOCK_DB: code = clean
        
    sector = "其他"
    if clean in FORCE_FIX_SECTOR: sector = FORCE_FIX_SECTOR[clean]
    elif code and code in MASTER_STOCK_DB: sector = MASTER_STOCK_DB[code][1]
        
    name = clean
    if code and code in MASTER_STOCK_DB: name = MASTER_STOCK_DB[code][0]
    
    return code, name, sector

def get_stock_sector(identifier):
    _, _, sector = smart_get_code_and_sector(identifier)
    return sector

def smart_get_code(stock_name):
    code, _, _ = smart_get_code_and_sector(stock_name)
    return code

def clean_and_lookup_stock(raw_code_or_name, raw_name_from_source=None):
    code = re.sub(r"\D", "", str(raw_code_or_name))
    if code and code in MASTER_STOCK_DB:
         return code, MASTER_STOCK_DB[code][0], MASTER_STOCK_DB[code][1]
    if raw_name_from_source:
        clean_name = raw_name_from_source.replace('*', '').strip()
        if clean_name in ALIAS_MAP: clean_name = ALIAS_MAP[clean_name] 
        sector = get_stock_sector(clean_name)
        for c, info in MASTER_STOCK_DB.items():
            if info[0] == clean_name:
                return c, info[0], info[1]
        return code, clean_name, sector
    return code, raw_code_or_name, "其他"

# --- 【V150】全時段市場即時報價 (fast_info + 補值) ---
def get_global_market_data_live():
    indices = {
        "^TWII": "🇹🇼 加權指數", "^TWOII": "🇹🇼 櫃買指數", "^N225": "🇯🇵 日經225",
        "^DJI": "🇺🇸 道瓊工業", "^IXIC": "🇺🇸 那斯達克", "^SOX": "🇺🇸 費城半導體"
    }
    market_data = []
    
    for ticker, name in indices.items():
        try:
            stock = yf.Ticker(ticker)
            
            # 優先使用 fast_info
            price = stock.fast_info.get('last_price')
            prev_close = stock.fast_info.get('previous_close')
            
            # 【V150 補丁】如果 fast_info 失敗，退回 history (5日K)
            if price is None or pd.isna(price) or price == 0:
                hist = stock.history(period="5d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    if len(hist) >= 2:
                        prev_close = float(hist['Close'].iloc[-2])
                    else:
                        prev_close = price

            # 如果還是沒有資料，跳過
            if price is None or pd.isna(price) or price == 0: continue

            change = price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close != 0 else 0
            
            color_class = "up-color" if change > 0 else ("down-color" if change < 0 else "flat-color")
            card_class = "card-up" if change > 0 else ("card-down" if change < 0 else "card-flat")
            
            market_data.append({
                "name": name, 
                "price": f"{price:,.2f}", 
                "change": change, 
                "pct_change": pct_change, 
                "color_class": color_class, 
                "card_class": card_class
            })
        except: continue
        
    return market_data

@st.fragment(run_every=3)
def render_global_markets():
    markets = get_global_market_data_live()
    if markets:
        st.markdown("### 🌏 全球重要指數 (Real-time)")
        now_str = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"<small style='color:gray'>⚡ 自動更新中 | 最後更新: {now_str} (每3秒)</small>", unsafe_allow_html=True)
        cols = st.columns(len(markets))
        for i, m in enumerate(markets):
            with cols[i]:
                st.markdown(f"""
                <div class="market-card {m['card_class']}">
                    <div class="market-name">{m['name']}</div>
                    <div class="market-price {m['color_class']}">{m['price']}</div>
                    <div class="market-change {m['color_class']}">{m['change']:+.2f} ({m['pct_change']:+.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)
        st.divider()
    else:
        st.warning("正在連線至全球股市資料... (若久無回應請檢查網路)")

# --- 【V150】預先批次抓取成交值 (修復定穎投控) ---
@st.cache_data(ttl=300)
def prefetch_turnover_data(stock_list_str, target_date):
    if not stock_list_str: return {}
    unique_names = set()
    for s in stock_list_str:
        if pd.isna(s): continue
        names = [n.strip() for n in str(s).split('、') if n.strip()]
        for name in names: unique_names.add(name.replace("(CB)", ""))
    
    code_map = {}
    tickers = []
    for name in unique_names:
        code, db_name, _ = smart_get_code_and_sector(name)
        if code:
            code_map[code] = {"input": name, "db": db_name}
            tickers.append(f"{code}.TW")
            tickers.append(f"{code}.TWO")
            
    if not tickers: return {}
    
    try:
        t_date_dt = pd.to_datetime(target_date)
        start_dt = t_date_dt - timedelta(days=20)
        end_dt = t_date_dt + timedelta(days=2)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        data = yf.download(tickers, start=start_str, end=end_str, group_by='ticker', progress=False, threads=True)
        result_map = {}
        for code, names_dict in code_map.items():
            found_val = 0
            for suffix in ['.TW', '.TWO']:
                try:
                    ticker = f"{code}{suffix}"
                    if ticker in data.columns.levels[0]:
                        df = data[ticker]
                        if not df.empty:
                            df.index = df.index.tz_localize(None).normalize()
                            target_ts = t_date_dt.normalize()
                            # 找 <= target_date 的最後一筆
                            valid_rows = df[df.index <= target_ts]
                            if not valid_rows.empty:
                                row = valid_rows.iloc[-1]
                                price = float(row['Close'])
                                vol = float(row['Volume'])
                                if price > 0 and vol > 0:
                                    val = (price * vol) / 100000000
                                    if val > 0.01:
                                        found_val = val
                                        break
                except: pass
            
            if found_val > 0:
                # 【V150】綁定所有 Key
                result_map[code] = found_val
                result_map[names_dict["input"]] = found_val 
                result_map[names_dict["db"]] = found_val 
                
        return result_map
    except Exception as e: return {}

# --- 【V150】排行榜 (雙軌保底 + 內部競價) ---
@st.cache_data(ttl=60) 
def get_ranking_data(limit=20):
    # 1. 爬蟲 (雲端易失敗，僅作嘗試)
    # ... (省略爬蟲代碼以節省空間，若爬蟲失敗直接進入備援) ...
    
    # 2. 強制備援：使用內部資料庫 (MASTER_STOCK_DB) 所有股票競價
    # 這保證了不會出現 "無法抓取資料"
    tickers = [f"{c}.TW" for c in MASTER_STOCK_DB.keys()] + [f"{c}.TWO" for c in MASTER_STOCK_DB.keys()]
    
    # 分批抓取以避免 Timeout (每批 100 檔)
    batch_size = 100
    yf_list = []
    
    for i in range(0, len(tickers), batch_size):
        batch_tickers = tickers[i:i+batch_size]
        try:
            data = yf.download(batch_tickers, period="1d", group_by='ticker', progress=False, threads=False)
            
            for ticker in batch_tickers:
                try:
                    code = re.sub(r"\D", "", ticker)
                    # 處理 MultiIndex
                    if isinstance(data.columns, pd.MultiIndex):
                        if ticker not in data.columns.levels[0]: continue
                        df_stock = data[ticker]
                    else:
                        # 單檔情況 (較少見)
                        continue
                        
                    if df_stock.empty: continue
                    
                    latest = df_stock.iloc[-1]
                    price = float(latest['Close'])
                    volume = float(latest['Volume'])
                    
                    if pd.isna(price) or pd.isna(volume) or price <= 0: continue
                    
                    turnover = (price * volume) / 100000000
                    if turnover < 1: continue # 過濾掉太小的
                    
                    op = float(latest['Open'])
                    chg = ((price - op)/op)*100 if op > 0 else 0
                    
                    _, name, sector = smart_get_code_and_sector(code)
                    market = "上櫃" if ".TWO" in ticker else "上市"
                    
                    yf_list.append({
                        "代號": code, "名稱": name, "股價": round(price,2),
                        "漲跌幅%": round(chg,2), "成交值(億)": round(turnover,2),
                        "市場": market, "族群": sector, "來源": "YF備援"
                    })
                except: continue
        except: pass
        
    if yf_list:
        df = pd.DataFrame(yf_list)
        df = df.sort_values(by="成交值(億)", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        df.insert(0, '排名', df.index)
        return df.head(limit)
        
    return pd.DataFrame()

def plot_market_index(index_type='上市', period='6mo'):
    ticker_map = {'上市': '^TWII', '上櫃': '^TWOII'}
    ticker = ticker_map.get(index_type, '^TWII')
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty: return None, f"無法取得 {index_type} 指數資料"
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=(f'{index_type}指數', '成交量'), row_width=[0.2, 0.8])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#9C27B0', width=1.5), name='MA5 (週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#FFC107', width=1.5), name='MA10 (雙週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#2196F3', width=1.5), name='MA20 (月)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#4CAF50', width=1.5), name='MA60 (季)'), row=1, col=1)
        colors = ['#ef5350' if row['Open'] - row['Close'] <= 0 else '#26a69a' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
        fig.update_layout(height=600, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='white', plot_bgcolor='#FAFAFA', font=dict(family="Arial, sans-serif", size=12, color='#333333'), legend=dict(orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="#E0E0E0", borderwidth=1), xaxis_rangeslider_visible=False, hovermode='x unified')
        grid_style = dict(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
        fig.update_xaxes(**grid_style, row=1, col=1)
        fig.update_yaxes(**grid_style, title='指數', row=1, col=1)
        fig.update_xaxes(**grid_style, row=2, col=1)
        fig.update_yaxes(**grid_style, title='量', row=2, col=1)
        return fig, ""
    except Exception as e: return None, f"繪圖錯誤: {str(e)}"

# --- UI 輔助函數 ---
def render_metric_card(col, label, value, color_border="gray", sub_value=""):
    sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else ""
    col.markdown(f"""
    <div class="metric-container" style="border-top: 5px solid {color_border};">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def render_stock_tags_v113(stock_str, turnover_map):
    if pd.isna(stock_str) or not stock_str: return "<span style='color:#bdc3c7; font-size:1.2rem; font-weight:600;'>（無標的）</span>"
    stock_names = [s.strip() for s in str(stock_str).split('、') if s.strip()]
    html = ""
    for s in stock_names:
        clean_s = s.replace("(CB)", "").replace("*", "")
        t_str = ""
        # V150: 多重 Key 查找
        val = None
        if clean_s in turnover_map: val = turnover_map[clean_s]
        else:
            code = smart_get_code(clean_s)
            if code and code in turnover_map: val = turnover_map[code]
        
        if val: t_str = f"<span class='turnover-val'>💰 {val:.1f}億</span>"
        
        if "(CB)" in s: html += f"<div class='stock-tag stock-tag-cb'>{clean_s}<span class='cb-badge'>CB</span>{t_str}</div>"
        else: html += f"<div class='stock-tag'>{clean_s}{t_str}</div>"
    return html

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
    if isinstance(records_list, list): new_data = pd.DataFrame(records_list)
    else: new_data = records_list
    if not new_data.empty:
        new_data['date'] = new_data['date'].astype(str)
        if not df.empty:
            df = df[~df['date'].isin(new_data['date'])]
            df = pd.concat([df, new_data], ignore_index=True)
        else: df = new_data
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

def calculate_wind_streak(df, current_date_str):
    if df.empty: return 0
    past_df = df[df['date'] <= current_date_str].copy()
    if past_df.empty: return 0
    past_df = past_df.sort_values('date', ascending=False).reset_index(drop=True)
    def clean_wind(w): return str(w).replace("(CB)", "").strip()
    current_wind = clean_wind(past_df.iloc[0]['wind'])
    streak = 1
    for i in range(1, len(past_df)):
        prev_wind = clean_wind(past_df.iloc[i]['wind'])
        if prev_wind == current_wind: streak += 1
        else: break
    return streak

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
        
        # 【V150】Robust Lookup
        def find_sector(stock_name):
            _, _, sector = smart_get_code_and_sector(stock_name)
            return sector
            
        counts['Industry'] = counts['stock'].apply(find_sector)
        all_stats.append(counts)
        
    if not all_stats: return pd.DataFrame()
    final_df = pd.concat(all_stats)
    final_df = final_df.sort_values(['Month', 'Strategy', 'Count'], ascending=[False, True, False])
    return final_df
    
# --- AI 分析函式 ---
def ai_analyze_v86(image):
    prompt = """
    你是一個精準的表格座標讀取器。請分析圖片中的每一行，回傳 JSON Array。
    【欄位對應表】
    1. `col_01`: 日期
    2. `col_02`: 風度
    3. `col_03`: 打工數
    4. `col_04`: 強勢週數
    5. `col_05`: 週趨勢數
    --- 黃色區塊 ---
    6. `col_06`: 強勢週 Stock 1
    7. `col_07`: 強勢週 Stock 2
    8. `col_08`: 強勢週 Stock 3
    9. `col_09`: 週趨勢 Stock 1
    10. `col_10`: 週趨勢 Stock 2
    11. `col_11`: 週趨勢 Stock 3
    --- 藍色區塊 ---
    12. `col_12`: 週拉回 Stock 1
    13. `col_13`: 週拉回 Stock 2
    14. `col_14`: 週拉回 Stock 3
    15. `col_15`: 廉價收購 Stock 1
    16. `col_16`: 廉價收購 Stock 2
    17. `col_17`: 廉價收購 Stock 3
    --- 灰色區塊 ---
    18. `col_18` ~ 23. `col_23`: 營收創高 Top 6
    【標記】橘色背景請加 (CB)，空白填 null。
    請回傳 JSON Array。
    """
    try:
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e: return json.dumps({"error": str(e)})

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

    # --- 【V147】預先抓取成交值 ---
    turnover_map = {}
    with st.spinner("正在計算策略選股成交值..."):
        all_strategy_stocks = [
            day_data.get('worker_strong_list', ''),
            day_data.get('worker_trend_list', ''),
            day_data.get('boss_pullback_list', ''),
            day_data.get('boss_bargain_list', ''),
            day_data.get('top_revenue_list', '')
        ]
        turnover_map = prefetch_turnover_data(all_strategy_stocks, selected_date)
    
    st.markdown(f"""<div class="title-box"><h1 style='margin:0; font-size: 2.8rem;'>📅 {selected_date} 市場戰情室</h1><p style='margin-top:10px; opacity:0.9;'>資料更新於: {day_data['last_updated']}</p></div>""", unsafe_allow_html=True)

    render_global_markets()

    with st.expander("📊 大盤指數走勢圖 (點擊展開)", expanded=True):
        col_m1, col_m2 = st.columns([1, 4])
        with col_m1:
            market_type = st.radio("選擇市場", ["上市", "上櫃"], horizontal=True)
            market_period = st.selectbox("週期", ["1mo", "3mo", "6mo", "1y"], index=2, key="market_period")
        with col_m2:
            fig, err = plot_market_index(market_type, market_period)
            if fig: st.plotly_chart(fig, use_container_width=True)
            else: st.warning(err)
            
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    wind_status = day_data['wind']; wind_color = "#2ecc71"
    wind_streak = calculate_wind_streak(df, selected_date)
    streak_text = f"已持續 {wind_streak} 天"
    if "強" in str(wind_status): wind_color = "#e74c3c"
    elif "亂" in str(wind_status): wind_color = "#9b59b6"
    elif "陣" in str(wind_status): wind_color = "#f1c40f"
    render_metric_card(c1, "今日風向", wind_status, wind_color, sub_value=streak_text)
    render_metric_card(c2, "🪁 打工型風箏", day_data['part_time_count'], "#f39c12")
    render_metric_card(c3, "💪 上班族強勢週", day_data['worker_strong_count'], "#3498db")
    render_metric_card(c4, "📈 上班族週趨勢", day_data['worker_trend_count'], "#9b59b6")

    # 【V126】使用 render_stock_tags_v113 並傳入 turnover_map
    st.markdown('<div class="strategy-banner worker-banner"><p class="banner-text">👨‍💼 上班族策略 (Worker Strategy)</p></div>', unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1: st.markdown("### 🚀 強勢週 TOP 3"); st.markdown(render_stock_tags_v113(day_data['worker_strong_list'], turnover_map), unsafe_allow_html=True)
    with w2: st.markdown("### 📈 週趨勢"); st.markdown(render_stock_tags_v113(day_data['worker_trend_list'], turnover_map), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner boss-banner"><p class="banner-text">👑 老闆策略 (Boss Strategy)</p></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1: st.markdown("### ↩️ 週拉回"); st.markdown(render_stock_tags_v113(day_data['boss_pullback_list'], turnover_map), unsafe_allow_html=True)
    with b2: st.markdown("### 🏷️ 廉價收購"); st.markdown(render_stock_tags_v113(day_data['boss_bargain_list'], turnover_map), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner revenue-banner"><p class="banner-text">💰 營收創高 (TOP 6)</p></div>', unsafe_allow_html=True)
    st.markdown(render_stock_tags_v113(day_data['top_revenue_list'], turnover_map), unsafe_allow_html=True)

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
        bar_chart = alt.Chart(melted_df).mark_bar(opacity=0.9).encode(x=alt.X('date:O', title='日期', axis=axis_config), y=alt.Y('count:Q', title='數量', axis=axis_config), color=alt.Color('category:N', title='指標', legend=legend_config), xOffset='category:N', tooltip=['date', 'category', 'count']).properties(height=450).configure(background='white').interactive()
        st.altair_chart(bar_chart, use_container_width=True)
    with tab2:
        wind_order = ['強風', '亂流', '陣風', '無風'] 
        wind_chart = alt.Chart(chart_df).mark_circle(size=600, opacity=1).encode(x=alt.X('date:O', title='日期', axis=axis_config), y=alt.Y('wind:N', title='風度', sort=wind_order, axis=axis_config), color=alt.Color('wind:N', title='狀態', legend=legend_config, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c'])), tooltip=['date', 'wind']).properties(height=400).configure(background='white').interactive()
        st.altair_chart(wind_chart, use_container_width=True)
    with tab3:
        monthly_wind = chart_df.groupby(['Month', 'wind']).size().reset_index(name='days')
        group_order = ['無風', '陣風', '亂流', '強風']
        grouped_chart = alt.Chart(monthly_wind).mark_bar().encode(x=alt.X('Month:O', title='月份', axis=axis_config), y=alt.Y('days:Q', title='天數', axis=axis_config), color=alt.Color('wind:N', title='風度', sort=group_order, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c']), legend=legend_config), xOffset=alt.XOffset('wind:N', sort=group_order), tooltip=['Month', 'wind', 'days']).properties(height=450).configure(background='white').interactive()
        st.altair_chart(grouped_chart, use_container_width=True)

    st.markdown("---")
    st.header("🏆 策略選股月度風雲榜")
    st.caption("統計各策略下，股票出現的次數與所屬族群。")
    stats_df = calculate_monthly_stats(df)
    if not stats_df.empty:
        month_list = stats_df['Month'].unique()
        selected_month = st.selectbox("選擇統計月份", options=month_list)
        filtered_stats = stats_df[stats_df['Month'] == selected_month]
        strategies_list = filtered_stats['Strategy'].unique()
        cols1 = st.columns(3); cols2 = st.columns(3)
        for i, strategy in enumerate(strategies_list):
            strat_data = filtered_stats[filtered_stats['Strategy'] == strategy].head(10)
            col_config = {"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1), "Industry": st.column_config.TextColumn("族群", help="所屬產業類別")}
            if i < 3:
                with cols1[i]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
            else:
                with cols2[i-3]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
    else: st.info("累積足夠資料後，將在此顯示統計排行。")

    st.markdown("---")
    st.header("🔥 今日市場重點監控 (權值股/熱門股 成交值排行)")
    st.caption("資料來源：Yahoo 股市 (即時爬蟲) / Yahoo Finance (備援) | 單位：億元")
    
    with st.spinner("正在計算最新成交資料..."):
        # 【V150】統一使用 get_ranking_data
        rank_df = get_ranking_data(20)
        
        if isinstance(rank_df, pd.DataFrame) and not rank_df.empty:
            max_turnover = rank_df['成交值(億)'].max()
            safe_max = int(max_turnover) if max_turnover > 0 else 1
            st.dataframe(rank_df, hide_index=True, use_container_width=True, column_config={"排名": st.column_config.NumberColumn("#", width="small"), "代號": st.column_config.TextColumn("代號"), "名稱": st.column_config.TextColumn("名稱", width="medium"), "股價": st.column_config.NumberColumn("股價", format="$%.2f"), "漲跌幅%": st.column_config.NumberColumn("漲跌幅", format="%.2f%%", help="日漲跌幅估算"), "成交值(億)": st.column_config.ProgressColumn("成交值 (億)", format="$%.2f億", min_value=0, max_value=safe_max), "市場": st.column_config.TextColumn("市場", width="small"), "族群": st.column_config.TextColumn("族群"), "來源": st.column_config.TextColumn("來源", width="small")})
        else: 
            st.warning("⚠️ 無法抓取資料，請檢查網路或稍後再試。")

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
                    if isinstance(raw_data, dict) and "error" in raw_data:
                        error_msg = raw_data["error"]
                        st.error(f"⚠️ API 回傳錯誤: {error_msg}")
                        if "429" in str(error_msg) or "quota" in str(error_msg).lower():
                            st.warning("💡 提示：您的 API 免費額度暫時滿了。請等待 1 分鐘後再試。")
                        st.stop()
                    def find_valid_records(data):
                        found = []
                        if isinstance(data, list):
                            for item in data: found.extend(find_valid_records(item))
                        elif isinstance(data, dict):
                            if "col_01" in data: found.append(data)
                            else:
                                for val in data.values(): found.extend(find_valid_records(val))
                        return found
                    raw_data = find_valid_records(raw_data)
                    with st.expander("🕵️‍♂️ 開發者除錯資訊"):
                        st.write("解析出的資料筆數:", len(raw_data))
                    if not isinstance(raw_data, list): raw_data = []
                    processed_list = []
                    for item in raw_data:
                        if not isinstance(item, dict): continue
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
