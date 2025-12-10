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
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 修正 Pydantic 錯誤
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

# --- 1. 頁面與 CSS (V105: 族群資料庫地毯式補強) ---
st.set_page_config(layout="wide", page_title="StockTrack V105+SectorComplete", page_icon="🏷️")

st.markdown("""
<style>
    /* 1. 全域背景 (淺灰藍) 與深色文字 */
    .stApp {
        background-color: #e8e8e8 !important;
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

    /* --- 4. 數據卡片 (響應式設計) --- */
    div.metric-container {
        background-color: #FFFFFF !important; 
        border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E0E0E0; border-top: 6px solid #3498db;
        
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        
        height: 220px !important;
    }

    .metric-value { font-size: 3.0rem !important; font-weight: 800; color: #2c3e50 !important; margin: 10px 0; }
    .metric-label { font-size: 2.2rem !important; color: #555555 !important; font-weight: 700; }
    .metric-sub { font-size: 1.2rem !important; color: #888888 !important; font-weight: bold; margin-top: 5px; }

    /* 手機版優化 */
    @media (max-width: 900px) {
        div.metric-container {
            height: auto !important;
            min-height: 180px !important;
            padding: 10px !important;
        }
        .metric-value { font-size: 2.2rem !important; }
        .metric-label { font-size: 1.5rem !important; }
    }

    /* 5. 策略橫幅 */
    .strategy-banner {
        padding: 15px 25px; border-radius: 8px; 
        margin-top: 35px; margin-bottom: 20px; display: flex; align-items: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
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
    .stSelectbox label { font-size: 20px !important; color: #333333 !important; font-weight: bold !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #2c3e50 !important; border-color: #2c3e50 !important; color: white !important; }
    .stSelectbox div[data-baseweb="select"] > div * { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] svg { fill: #FFFFFF !important; color: #FFFFFF !important; }
    ul[data-baseweb="menu"], div[data-baseweb="popover"] div { background-color: #2c3e50 !important; }
    li[role="option"] { background-color: #2c3e50 !important; color: #FFFFFF !important; }
    li[role="option"]:hover, li[role="option"][aria-selected="true"] { background-color: #34495e !important; color: #f1c40f !important; }
    li[role="option"] div { color: #FFFFFF !important; }
    li[role="option"]:hover div { color: #f1c40f !important; }
    
    /* 10. 全球指數卡片 */
    [data-testid="stMetricValue"] {
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        font-family: 'Arial', sans-serif;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.4rem !important;
        color: #555555 !important;
        font-weight: bold !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 1.1rem !important;
        font-weight: bold !important;
    }

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
    model_name_to_use = "gemini-1.5-flash"
    model = genai.GenerativeModel(
        model_name=model_name_to_use,
        generation_config=generation_config,
    )

DB_FILE = 'stock_data_v74.csv' 
BACKUP_FILE = 'stock_data_backup.csv'

# --- 3. 核心函數 ---

# 【V105】超完整股名 -> 族群對照表 (針對中小型飆股與策略股補強)
NAME_TO_SECTOR = {
    # === 晶圓代工 ===
    "台積電": "晶圓代工", "聯電": "晶圓代工", "力積電": "晶圓代工", "世界": "晶圓代工",
    
    # === IP / ASIC (矽智財) ===
    "世芯-KY": "IP矽智財", "創意": "IP矽智財", "智原": "IP矽智財", "M31": "IP矽智財",
    "力旺": "IP矽智財", "晶心科": "IP矽智財", "巨有科技": "IP矽智財", "金麗科": "IP矽智財",
    "愛普*": "IP/記憶體", "伊雲谷": "雲端/IP",
    
    # === IC設計 (權值/熱門) ===
    "聯發科": "IC設計", "聯詠": "IC設計", "瑞昱": "IC設計", "祥碩": "IC設計", 
    "譜瑞-KY": "IC設計", "信驊": "IC設計", "矽力-KY": "IC設計", "新唐": "IC設計", 
    "天鈺": "IC設計", "晶豪科": "IC設計", "威盛": "IC設計", "矽創": "IC設計",
    "茂達": "IC設計", "原相": "IC設計", "敦泰": "IC設計", "凌陽": "IC設計",
    "聯陽": "IC設計", "揚智": "IC設計", "達發": "IC設計", "義隆": "IC設計",
    "致新": "IC設計", "偉詮電": "IC設計", "通嘉": "IC設計", "點序": "IC設計",
    "創惟": "IC設計", "鈺創": "IC設計", "九暘": "IC設計", "普誠": "IC設計",
    "世紀": "IC設計", "安國": "神盾集團", "神盾": "神盾集團", "安格": "神盾集團",
    "迅杰": "神盾集團", "芯鼎": "神盾集團",
    
    # === 記憶體 & 模組 ===
    "群聯": "記憶體控制", "威剛": "記憶體模組", "十銓": "記憶體模組", "宇瞻": "記憶體模組",
    "宜鼎": "工控記憶體", "創見": "記憶體模組", "華邦電": "記憶體", "南亞科": "記憶體",
    "旺宏": "記憶體", "品安": "記憶體模組", "廣穎": "記憶體模組",
    
    # === 散熱族群 (補強) ===
    "奇鋐": "散熱", "雙鴻": "散熱", "健策": "散熱", "高力": "散熱",
    "建準": "散熱", "力致": "散熱", "泰碩": "散熱", "元山": "散熱", 
    "尼得科超眾": "散熱", "協禧": "散熱", "廣運": "散熱/自動化", "富世達": "軸承/散熱",
    "動力-KY": "散熱", "萬在": "散熱",
    
    # === AI 伺服器 & 組裝 ===
    "鴻海": "AI伺服器", "廣達": "AI伺服器", "緯創": "AI伺服器", "緯穎": "AI伺服器",
    "英業達": "AI伺服器", "技嘉": "AI伺服器", "微星": "板卡/伺服器", "華碩": "AI伺服器",
    "仁寶": "組裝代工", "和碩": "組裝代工", "宏碁": "AI PC", "神達": "伺服器",
    "藍天": "NB代工",
    
    # === 機殼 & 導軌 ===
    "勤誠": "機殼", "川湖": "導軌", "營邦": "機殼", "晟銘電": "機殼",
    "迎廣": "機殼", "振發": "機殼", "富驊": "機殼", "旭品": "機殼",
    
    # === CPO / 光通訊 ===
    "聯鈞": "CPO/光通訊", "聯亞": "光通訊", "華星光": "光通訊", "上詮": "光通訊",
    "波若威": "光通訊", "光聖": "光通訊", "前鼎": "光通訊", "眾達-KY": "光通訊",
    "光環": "光通訊", "創威": "光通訊", "訊芯-KY": "CPO封測", "台通": "光通訊",
    "旺矽": "探針卡/CPO",
    
    # === 設備 & 檢測 (CoWoS/PCB) ===
    "弘塑": "CoWoS設備", "辛耘": "CoWoS設備", "萬潤": "CoWoS設備", "均華": "CoWoS設備",
    "家登": "光罩盒", "致茂": "檢測設備", "閎康": "檢測分析", "宜特": "檢測分析",
    "京鼎": "設備", "帆宣": "設備", "亞翔": "廠務", "漢唐": "廠務",
    "大量": "PCB/半導體設備", "志聖": "PCB/半導體設備", "均豪": "半導體設備",
    "鈦昇": "半導體設備", "群翊": "PCB設備", "牧德": "檢測設備",
    "瑞耘": "設備零組件", "千附精密": "設備零組件",
    
    # === 測試介面 ===
    "雍智科技": "測試介面", "精測": "測試介面", "穎崴": "測試介面", "旺矽": "探針卡",
    "中探針": "探針",
    
    # === 重電 & 綠能 ===
    "華城": "重電", "士電": "重電", "中興電": "重電", "亞力": "重電", "東元": "重電",
    "大同": "重電", "森崴能源": "綠能", "雲豹能源": "綠能", "世紀鋼": "風電",
    "上緯投控": "風電", "華新": "電線電纜", "大亞": "電線電纜", "合機": "電線電纜",
    "宏泰": "電線電纜", "泓德能源": "綠能",
    
    # === 連接器 & 線束 ===
    "良維": "連接器", "貿聯-KY": "連接器", "信邦": "連接器", "維熹": "連接器",
    "宏致": "連接器", "優群": "連接器", "嘉澤": "連接器", "凡甲": "連接器",
    "詮欣": "連接器", "胡連": "車用連接器", "正崴": "連接器",
    
    # === PCB / CCL / 載板 / 材料 ===
    "台光電": "CCL銅箔", "台燿": "CCL銅箔", "聯茂": "CCL銅箔",
    "金像電": "PCB", "健鼎": "PCB", "定穎投控": "PCB", "博智": "PCB", "華通": "PCB",
    "楠梓電": "PCB", "燿華": "PCB", "敬鵬": "車用PCB", "瀚宇博": "PCB",
    "欣興": "ABF載板", "南電": "ABF載板", "景碩": "ABF載板",
    "富喬": "PCB材料", "建榮": "PCB材料", "德宏": "PCB材料", "尖點": "PCB鑽針",
    "達興材料": "特用化學",
    
    # === 特用化學 / 氣體 ===
    "晶呈科技": "半導體特氣", "上品": "氟素設備", "三福化": "特用化學",
    "中華化": "特用化學", "永光": "特用化學", "勝一": "特用化學",
    
    # === 被動元件 & 材料 ===
    "國巨": "被動元件", "華新科": "被動元件", "勤凱": "被動元件/材料", "立隆電": "被動元件",
    "信昌電": "被動元件", "禾伸堂": "被動元件", "凱美": "被動元件", "大毅": "被動元件",
    
    # === 電池 & 車用 & AM ===
    "AES-KY": "電池模組", "順達": "電池模組", "新普": "電池模組", "加百裕": "電池模組",
    "台達電": "電源/EV", "康舒": "電源", "飛宏": "充電樁", "立德": "電源",
    "精確": "車用零組件", "劍麟": "車用零組件", "堤維西": "AM車燈", "東陽": "AM汽材",
    "帝寶": "AM車燈", "耿鼎": "AM鈑金",
    
    # === 系統整合 & IPC ===
    "三商電": "系統整合", "精誠": "系統整合", "零壹": "資安", "邁達特": "系統整合",
    "凌華": "IPC/機器人", "樺漢": "IPC", "研華": "IPC", "廣積": "IPC", "友通": "IPC",
    "立端": "網安IPC", "安勤": "IPC", "新漢": "IPC", "振樺電": "IPC",
    "至上": "IC通路", "文曄": "IC通路", "大聯大": "IC通路",
    
    # === 機器人概念 ===
    "所羅門": "機器人", "羅昇": "機器人", "盟立": "機器人", "昆盈": "機器人",
    "廣明": "機器人", "聰泰": "機器人", "圓剛": "機器人", "台灣精銳": "減速機",
    
    # === 網通 ===
    "智邦": "網通", "中磊": "網通", "啟碁": "網通", "明泰": "網通", "正文": "網通",
    "合勤控": "網通", "神準": "網通", "智易": "網通", "友訊": "網通", "建漢": "網通",
    
    # === 砷化鎵 / 三五族 ===
    "穩懋": "砷化鎵", "宏捷科": "砷化鎵", "全新": "砷化鎵", "IET-KY": "砷化鎵",
    
    # === 生技 ===
    "保瑞": "生技CDMO", "美時": "生技", "藥華藥": "生技", "合一": "生技",
    "北極星藥業-KY": "生技", "智擎": "生技", "台康生技": "生技", "高端疫苗": "生技",
    
    # === 航運 ===
    "長榮": "貨櫃航運", "陽明": "貨櫃航運", "萬海": "貨櫃航運",
    "長榮航": "航空", "華航": "航空", "星宇航空": "航空",
    "裕民": "散裝", "慧洋-KY": "散裝", "新興": "散裝",
    
    # === 金融 ===
    "富邦金": "金融", "國泰金": "金融", "中信金": "金融", "兆豐金": "金融",
    "開發金": "金融", "元大金": "金融", "玉山金": "金融", "臺企銀": "金融",
    "新光金": "金融", "台新金": "金融", "永豐金": "金融",
    
    # === 其他常見 ===
    "元太": "電子紙", "亞光": "光學", "先進光": "光學", "大立光": "光學",
    "中鋼": "鋼鐵", "台泥": "水泥", "統一": "食品",
    "美利達": "自行車", "巨大": "自行車", "豐泰": "製鞋", "寶成": "製鞋",
    "京元電子": "封測", "京元電": "封測", "日月光": "封測"
}

# 【V101 核心】代碼與族群對照 (用於排行榜)
TW_STOCK_INFO = {
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
    
    # 權值/熱門 (上櫃)
    "8299": ("群聯", "記憶體控制"), "8069": ("元太", "電子紙"), "6488": ("環球晶", "矽晶圓"),
    "3293": ("鈊象", "遊戲"), "3529": ("力旺", "IP矽智財"), "3131": ("弘塑", "CoWoS設備"),
    "5274": ("信驊", "IC設計"), "5347": ("世界", "晶圓代工"), "4966": ("譜瑞-KY", "IC設計"),
    "6274": ("台燿", "CCL銅箔"), "3374": ("精材", "封測"), "6147": ("頎邦", "封測"),
    "5483": ("中美晶", "矽晶圓"), "3105": ("穩懋", "砷化鎵"), "6223": ("旺矽", "探針卡"),
    "3081": ("聯亞", "光通訊"), "3450": ("聯鈞", "CPO/光通訊"), "4979": ("華星光", "光通訊"),
    "5289": ("宜鼎", "工控記憶體"), "4760": ("勤凱", "被動元件/材料"), "6683": ("雍智科技", "測試介面"),
    "8996": ("高力", "散熱"), "6187": ("萬潤", "CoWoS設備"), "3583": ("辛耘", "CoWoS設備"),
    "6138": ("茂達", "IC設計"), "3680": ("家登", "半導體設備"), "5425": ("台半", "二極體"),
    "3260": ("威剛", "記憶體"), "8046": ("南電", "ABF載板"), "1815": ("富喬", "PCB材料"),
    "4768": ("晶呈科技", "半導體特氣"), "8112": ("至上", "IC通路"), "5314": ("世紀", "IC設計"),
    "3162": ("精確", "車用零組件"), "4971": ("IET-KY", "砷化鎵"), "3167": ("大量", "半導體設備"),
    "8021": ("尖點", "PCB鑽針")
}

# 輔助函式：取得名稱
def get_stock_name(code):
    clean_code = code.replace("(CB)", "").strip()
    return TW_STOCK_INFO.get(clean_code, (clean_code, "其他"))[0]

# 輔助函式：取得族群 (支援從代號或名稱反查)
def get_stock_sector(identifier):
    clean_id = identifier.replace("(CB)", "").strip()
    if clean_id in TW_STOCK_INFO: return TW_STOCK_INFO[clean_id][1]
    if clean_id in NAME_TO_SECTOR: return NAME_TO_SECTOR[clean_id]
    return "其他"

# --- 【V104 新增】全球市場即時報價 (修復版) ---
@st.cache_data(ttl=60)
def get_global_market_data():
    try:
        # 定義要抓取的指數 (代號: 顯示名稱)
        indices = {
            "^TWII": "🇹🇼 加權指數",
            "^TWOII": "🇹🇼 櫃買指數",
            "^N225": "🇯🇵 日經225",
            "^DJI": "🇺🇸 道瓊工業",
            "^IXIC": "🇺🇸 那斯達克",
            "^SOX": "🇺🇸 費城半導體"
        }
        
        market_data = []
        
        # 逐一抓取 (避免批次失敗影響全部)
        for ticker, name in indices.items():
            try:
                stock = yf.Ticker(ticker)
                
                # 【關鍵修正】強制使用 history 抓取，不依賴 fast_info (容易 nan)
                hist = stock.history(period="5d") # 抓 5 天以防假日
                
                if not hist.empty:
                    # 最新價 = 最後一筆 Close
                    price = hist['Close'].iloc[-1]
                    
                    # 前一日收盤 = 倒數第二筆 Close (用來算漲跌)
                    if len(hist) >= 2:
                        prev_close = hist['Close'].iloc[-2]
                    else:
                        prev_close = price # 資料不足，無法計算漲跌
                    
                    # 計算漲跌
                    change = price - prev_close
                    pct_change = (change / prev_close) * 100
                    
                    market_data.append({
                        "name": name,
                        "price": f"{price:,.0f}", # 指數整數位
                        "change": change,
                        "pct_change": pct_change
                    })
            except:
                continue # 略過失敗的指數
                
        return market_data
    except: return []

# --- 顯示全球市場區塊 ---
def render_global_markets():
    markets = get_global_market_data()
    if markets:
        st.markdown("### 🌏 全球重要指數 (Real-time)")
        # 動態計算欄位數 (避免空欄位)
        cols = st.columns(len(markets))
        for i, m in enumerate(markets):
            cols[i].metric(
                label=m["name"],
                value=m["price"],
                delta=f"{m['change']:+.0f} ({m['pct_change']:+.2f}%)",
                delta_color="inverse" # 紅漲綠跌
            )
        st.divider()

# --- 排行榜抓取 (V101: 暴力修正 "8299O" 問題) ---
@st.cache_data(ttl=60) 
def get_rank_v93_accurate(limit=20):
    try:
        tickers = [f"{code}.TW" for code in TW_STOCK_INFO.keys()] + \
                  [f"{code}.TWO" for code in TW_STOCK_INFO.keys()]
        data = yf.download(tickers, period="1d", group_by='ticker', progress=False, threads=True)
        result_list = []
        for ticker in tickers:
            try:
                # 【V101 關鍵修正】暴力清洗代碼，只保留數字
                code = re.sub(r"\D", "", ticker) 
                if ticker not in data.columns.levels[0]: continue
                df_stock = data[ticker]
                if df_stock.empty: continue
                latest = df_stock.iloc[-1]
                price = latest['Close']
                volume = latest['Volume'] 
                if pd.isna(price) or pd.isna(volume) or price <= 0: continue
                turnover_yi = (price * volume) / 100000000
                if turnover_yi < 1: continue 
                open_price = latest['Open']
                if pd.notna(open_price) and open_price > 0: change_pct = ((price - open_price) / open_price) * 100
                else: change_pct = 0.0
                info = TW_STOCK_INFO.get(code, (code, "其他"))
                name = info[0]; sector = info[1]
                market = "上櫃" if ".TWO" in ticker else "上市"
                result_list.append({"代號": code, "名稱": name, "股價": float(price), "漲跌幅%": float(change_pct), "成交值(億)": float(turnover_yi), "市場": market, "族群": sector})
            except: continue
        if not result_list: return "目前無法取得市場數據"
        df_rank = pd.DataFrame(result_list)
        df_rank = df_rank.sort_values(by="成交值(億)", ascending=False).reset_index(drop=True)
        df_rank.index = df_rank.index + 1
        df_rank.insert(0, '排名', df_rank.index)
        df_rank['成交值(億)'] = df_rank['成交值(億)'].round(2)
        df_rank['股價'] = df_rank['股價'].round(1)
        df_rank['漲跌幅%'] = df_rank['漲跌幅%'].round(2)
        return df_rank.head(limit)
    except Exception as e: return f"System Error: {str(e)}"

# --- 【V102 專業版】繪製 大盤指數 K 線圖 ---
def plot_market_index(index_type='上市', period='6mo'):
    ticker_map = {'上市': '^TWII', '上櫃': '^TWOII'}
    ticker = ticker_map.get(index_type, '^TWII')
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty: return None, f"無法取得 {index_type} 指數資料"

        # 計算均線 (新增 MA10)
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean() # 新增
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 建立雙軸圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                            subplot_titles=(f'{index_type}指數', '成交量'), 
                            row_width=[0.2, 0.8]) # 調整高度比例

        # K線圖 (Row 1)
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'
        ), row=1, col=1)

        # 均線 (Row 1) - 專業配色與線條
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#9C27B0', width=1.5), name='MA5 (週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#FFC107', width=1.5), name='MA10 (雙週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#2196F3', width=1.5), name='MA20 (月)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#4CAF50', width=1.5), name='MA60 (季)'), row=1, col=1)

        # 成交量 (Row 2)
        colors = ['#ef5350' if row['Open'] - row['Close'] <= 0 else '#26a69a' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)

        # 專業版面設定
        fig.update_layout(
            height=600, # 增加高度
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='white', plot_bgcolor='#FAFAFA', # 極淡灰背景
            font=dict(family="Arial, sans-serif", size=12, color='#333333'),
            legend=dict(
                orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01, # 圖例移至內部左上
                bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="#E0E0E0", borderwidth=1
            ),
            xaxis_rangeslider_visible=False,
            hovermode='x unified' # 【關鍵】統一顯示十字準線資訊
        )
        
        # 細緻格線設定
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

def render_stock_tags(stock_str):
    if pd.isna(stock_str) or not stock_str: return "<span style='color:#bdc3c7; font-size:1.2rem; font-weight:600;'>（無標的）</span>"
    html = ""
    stocks = str(stock_str).split('、')
    for s in stocks:
        if not s: continue
        if "(CB)" in s: name = s.replace("(CB)", ""); html += f"<div class='stock-tag stock-tag-cb'>{name}<span class='cb-badge'>CB</span></div>"
        else: html += f"<div class='stock-tag'>{s}</div>"
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

# --- 【V100 修正】計算月度風雲榜 (使用新版 NAME_TO_SECTOR 反查) ---
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
        
        # 【V100 更新】使用 Name-Based 字典反查
        def find_sector(stock_name):
            clean_name = stock_name.replace("(CB)", "").strip()
            # 直接查名詞表
            return NAME_TO_SECTOR.get(clean_name, "其他")
            
        counts['Industry'] = counts['stock'].apply(find_sector)
        
        all_stats.append(counts)
        
    if not all_stats: return pd.DataFrame()
    final_df = pd.concat(all_stats)
    final_df = final_df.sort_values(['Month', 'Strategy', 'Count'], ascending=[False, True, False])
    return final_df

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

    # 全球市場報價牆 (V103修復版)
    render_global_markets()

    # K線圖區塊
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

    # --- 【V100 更新】策略選股月度風雲榜 ---
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
            
            col_config = {
                "stock": "股票名稱",
                "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1),
                "Industry": st.column_config.TextColumn("族群", help="所屬產業類別")
            }
            
            if i < 3:
                with cols1[i]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
            else:
                with cols2[i-3]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
    else:
        st.info("累積足夠資料後，將在此顯示統計排行。")

    # --- 權值股排行 (V93邏輯 + V101暴力清洗) ---
    st.markdown("---")
    st.header("🔥 今日市場重點監控 (權值股/熱門股 成交值排行)")
    st.caption("資料來源：Yahoo Finance (監控前 200 大活躍股，即時運算) | 單位：億元")
    
    with st.spinner("正在計算最新成交資料..."):
        rank_df = get_rank_v93_accurate(20)
        if isinstance(rank_df, pd.DataFrame) and not rank_df.empty:
            max_turnover = rank_df['成交值(億)'].max()
            safe_max = int(max_turnover) if max_turnover > 0 else 1
            st.dataframe(rank_df, hide_index=True, use_container_width=True, column_config={"排名": st.column_config.NumberColumn("#", width="small"), "代號": st.column_config.TextColumn("代號"), "名稱": st.column_config.TextColumn("名稱", width="medium"), "股價": st.column_config.NumberColumn("股價", format="$%.1f"), "漲跌幅%": st.column_config.NumberColumn("漲跌幅", format="%.2f%%", help="日漲跌幅估算"), "成交值(億)": st.column_config.ProgressColumn("成交值 (億)", format="$%.2f億", min_value=0, max_value=safe_max), "市場": st.column_config.TextColumn("市場", width="small"), "族群": st.column_config.TextColumn("族群")})
        else: st.warning(f"⚠️ 無法抓取資料：{rank_df}")

# --- 6. 頁面視圖：管理後台 (後台) ---
def show_admin_panel():
    st.title("⚙️ 資料管理後台")
    if not GOOGLE_API_KEY: st.error("❌ 未設定 API Key"); return

    with st.expander("🛠️ API 診斷工具 (若遇到 404 Error 請按此)"):
        if st.button("🔍 列出所有可用模型"):
            try:
                models = genai.list_models()
                st.write("您的 API Key 可存取以下模型：")
                for m in models:
                    if 'generateContent' in m.supported_generation_methods:
                        st.code(m.name)
                st.info("請將上述列表中，支援 vision/flash 的模型名稱填入程式碼中的 `model_name`。")
            except Exception as e:
                st.error(f"查詢失敗: {e}")
    
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
                            for item in data:
                                found.extend(find_valid_records(item))
                        elif isinstance(data, dict):
                            if "col_01" in data:
                                found.append(data)
                            else:
                                for val in data.values():
                                    found.extend(find_valid_records(val))
                        return found

                    raw_data = find_valid_records(raw_data)
                    
                    with st.expander("🕵️‍♂️ 開發者除錯資訊 (若資料空白請點我)"):
                        st.write("解析出的資料筆數:", len(raw_data))
                        st.write("原始 JSON 內容:", json.loads(json_text)) 

                    if not isinstance(raw_data, list):
                        raw_data = []

                    processed_list = []
                    for item in raw_data:
                        if not isinstance(item, dict):
                            continue 
                        
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
