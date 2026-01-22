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
import math
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 修正 Pydantic 錯誤
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

# --- 1. 頁面與 CSS (V200: Google Sheets 雲端旗艦版) ---
st.set_page_config(layout="wide", page_title="StockTrack V200", page_icon="💰")

st.markdown("""
<style>
    /* 全域設定 */
    .stApp { background-color: #F0F2F6 !important; color: #333333 !important; font-family: 'Helvetica', 'Arial', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #333333; }
    
    /* 標題區 */
    .title-box { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
    .title-box h1 { color: #FFFFFF !important; font-size: 36px !important; margin-bottom: 10px !important; }
    .title-box p { color: #E0E0E0 !important; font-size: 18px !important; }
    
    /* 全球指數卡片 */
    .market-card-item { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; height: 120px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-content-top { padding: 10px 15px 0; flex: 1; }
    .card-title-text { font-weight: bold; color: #555; font-size: 0.9rem; }
    .card-price-num { font-size: 1.4rem; font-weight: 800; color: #222; }
    .card-price-chg { font-size: 0.8rem; font-weight: 600; }
    .color-up { color: #dc2626; } .color-down { color: #059669; } .color-flat { color: #6b7280; }
    .card-chart-bottom { height: 40px; width: 100%; opacity: 0.8; }
    .market-dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }

    /* 股票標籤 */
    .stock-tag { display: inline-block; background-color: #FFFFFF; color: #2c3e50 !important; border: 2px solid #bdc3c7; padding: 10px 18px; margin: 8px; border-radius: 10px; font-weight: 800; font-size: 1.6rem; box-shadow: 0 3px 6px rgba(0,0,0,0.1); vertical-align: middle; text-align: center; min-width: 140px; }
    .cb-badge { background-color: #e67e22; color: #FFFFFF !important; font-size: 0.6em; padding: 2px 6px; border-radius: 4px; margin-left: 5px; vertical-align: text-top; }
    .turnover-val { display: block; font-size: 0.8em; font-weight: 900; color: #d35400; margin-top: 4px; padding-top: 4px; border-top: 1px dashed #ccc; font-family: 'Arial', sans-serif; }

    .stDataFrame table { text-align: center !important; }
    .stDataFrame th { font-size: 18px !important; color: #000000 !important; background-color: #E6E9EF !important; text-align: center !important; font-weight: 900 !important; }
    .stDataFrame td { font-size: 18px !important; color: #333333 !important; background-color: #FFFFFF !important; text-align: center !important; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 設定 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    else:
        GOOGLE_API_KEY = ""
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
    model_name_to_use = "gemini-2.0-flash"
    model = genai.GenerativeModel(
        model_name=model_name_to_use,
        generation_config=generation_config,
    )

# --- Google Sheets 連線設定 ---
def get_gsheet_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client

# --- 通用讀取函式 (除錯版) ---
def load_data_from_gsheet(worksheet_name):
    try:
        client = get_gsheet_connection()
        target_sheet = st.secrets["sheet_name"]
        sheet = client.open(target_sheet)
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # 日期欄位正規化
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df = df.sort_values('date', ascending=False)
        elif '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            df = df.dropna(subset=['日期']).sort_values('日期')
            
        return df
    except Exception as e:
        # st.error(f"讀取 {worksheet_name} 錯誤: {e}") # 暫時隱藏錯誤，避免畫面太亂
        return pd.DataFrame()

# --- 通用寫入函式 ---
def save_data_to_gsheet(df, worksheet_name):
    try:
        client = get_gsheet_connection()
        sheet = client.open(st.secrets["sheet_name"])
        ws = sheet.worksheet(worksheet_name)
        
        df_save = df.copy()
        if 'date' in df_save.columns:
            df_save['date'] = pd.to_datetime(df_save['date']).dt.strftime('%Y-%m-%d')
        if '日期' in df_save.columns:
            df_save['日期'] = pd.to_datetime(df_save['日期']).dt.strftime('%Y-%m-%d')
            
        df_save = df_save.fillna('')
        
        ws.clear()
        data_to_upload = [df_save.columns.values.tolist()] + df_save.values.tolist()
        ws.update(data_to_upload)
        
        return True, "✅ 資料已同步至 Google Sheets！"
    except Exception as e:
        return False, f"❌ 寫入失敗: {e}"

# --- 資料庫操作相容函式 ---
def load_db():
    target_sheet = "Daily_Main"
    try:
        df = load_data_from_gsheet(target_sheet)
        if not df.empty:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            numeric_cols = ['part_time_count', 'worker_strong_count', 'worker_trend_count']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            if 'manual_turnover' not in df.columns: df['manual_turnover'] = ""
            df['manual_turnover'] = df['manual_turnover'].astype(str).replace('nan', '')
            return df.sort_values('date', ascending=False)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 讀取主資料庫失敗 ({target_sheet}): {e}")
        return pd.DataFrame()

def save_batch_data(records_list):
    current_df = load_db()
    if isinstance(records_list, list): new_data = pd.DataFrame(records_list)
    else: new_data = records_list
    
    if not new_data.empty:
        new_data['date'] = pd.to_datetime(new_data['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        if 'manual_turnover' not in new_data.columns: new_data['manual_turnover'] = ""
        
        if not current_df.empty:
            current_df = current_df[~current_df['date'].isin(new_data['date'])]
            final_df = pd.concat([current_df, new_data], ignore_index=True)
        else: final_df = new_data
        
        final_df = final_df.sort_values('date', ascending=False)
        ok, msg = save_data_to_gsheet(final_df, "Daily_Main")
        if not ok: st.error(msg)
        return final_df
    return current_df

def save_full_history(df_to_save):
    if not df_to_save.empty:
        df_to_save['date'] = pd.to_datetime(df_to_save['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_to_save = df_to_save.sort_values('date', ascending=False)
        ok, msg = save_data_to_gsheet(df_to_save, "Daily_Main")
        if not ok: st.error(msg)

# --- 3. 核心資料庫 (MASTER_STOCK_DB) ---
MASTER_STOCK_DB = {
    "1560": ("中砂", "再生晶圓/鑽石碟"), "3045": ("台灣大", "電信"), 
    "3551": ("世禾", "半導體設備"), "3715": ("定穎投控", "PCB"),
    "2404": ("漢唐", "無塵室/廠務"), "3402": ("漢科", "廠務設備"),
    "2887": ("台新新光", "金融"), "6830": ("汎銓", "電子上游IC"),
    "2330": ("台積電", "晶圓代工"), "2317": ("鴻海", "組裝"), "2454": ("聯發科", "IC設計")
}
NAME_TO_CODE = {name: code for code, (name, _) in MASTER_STOCK_DB.items()}
ALIAS_MAP = {"台新金": "台新新光", "新光金": "台新新光"}

def smart_get_code_and_sector(stock_input):
    raw = str(stock_input).strip().replace("(CB)", "").replace("*", "")
    if raw in ALIAS_MAP: raw = ALIAS_MAP[raw]
    code = NAME_TO_CODE.get(raw)
    if not code and raw.isdigit() and raw in MASTER_STOCK_DB: code = raw
    sector = "其他"
    name = raw
    if code and code in MASTER_STOCK_DB:
        name, sector = MASTER_STOCK_DB[code]
    return code, name, sector

def smart_get_code(stock_name):
    code, _, _ = smart_get_code_and_sector(stock_name)
    return code

# --- Helper Functions ---
def calculate_wind_streak(df, target_date_str):
    """計算風度連續天數"""
    try:
        # 統一欄位名稱
        date_col = 'date' if 'date' in df.columns else '日期'
        wind_col = 'wind' if 'wind' in df.columns else '風度'
        
        if date_col not in df.columns or wind_col not in df.columns:
            return 1
            
        # 轉換日期並排序 (新到舊)
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col, ascending=False)
        target_dt = pd.to_datetime(target_date_str)
        
        # 篩選小於等於目標日期的資料
        df = df[df[date_col] <= target_dt]
        if df.empty: return 1
        
        target_wind = df.iloc[0][wind_col]
        streak = 0
        for w in df[wind_col]:
            if w == target_wind: streak += 1
            else: break
        return streak
    except:
        return 1

def fetch_official_tw_index_data():
    """從證交所 API 獲取即時指數"""
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw&json=1&delay=0"
        r = requests.get(f"{url}&_={int(time.time()*1000)}", timeout=5)
        res = {}
        if r.status_code == 200:
            data = r.json()
            for i in data.get('msgArray', []):
                if i['c'] == 't00': k = '^TWII'
                elif i['c'] == 'o00': k = '^TWOII'
                else: continue
                try:
                    p = float(i.get('z', 0))
                    y = float(i.get('y', 0))
                    if p > 0 and y > 0:
                        res[k] = {'price': p, 'change': p-y, 'pct_change': (p-y)/y*100}
                except: pass
        return res
    except: return {}

def get_index_live_data(yf_ticker, official_key):
    """整合官方 API 與 Yahoo Finance 的指數獲取函式"""
    # 1. 嘗試官方 API
    official_data = fetch_official_tw_index_data()
    if official_key in official_data:
        return official_data[official_key]
    
    # 2. 備援：Yahoo Finance
    try:
        t = yf.Ticker(yf_ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            price_now = hist['Close'].iloc[-1]
            price_prev = hist['Close'].iloc[-2]
            change = price_now - price_prev
            pct = (change / price_prev) * 100
            return {'price': price_now, 'change': change, 'pct_change': pct}
    except: pass
    
    return {'price': 0, 'change': 0, 'pct_change': 0}

@st.cache_data(ttl=300)
def prefetch_turnover_data(stock_list_str, target_date, manual_override_json=None):
    if not stock_list_str: return {}
    unique_names = set()
    for s in stock_list_str:
        if pd.isna(s): continue
        for n in str(s).split('、'):
            if n.strip(): unique_names.add(n.strip().replace("(CB)", ""))
            
    result_map = {}
    if manual_override_json:
        try:
            manual_data = json.loads(manual_override_json)
            for k, v in manual_data.items():
                result_map[k] = float(v)
                code, _, _ = smart_get_code_and_sector(k)
                if code: result_map[code] = float(v)
        except: pass

    to_fetch = [n for n in unique_names if n not in result_map]
    if not to_fetch: return result_map

    tickers = []
    code_map = {}
    for name in to_fetch:
        code, _, _ = smart_get_code_and_sector(name)
        if code:
            tickers.append(f"{code}.TW"); tickers.append(f"{code}.TWO")
            code_map[code] = name

    if tickers:
        try:
            data = yf.download(tickers, period="5d", group_by='ticker', progress=False, threads=False)
            for code, name in code_map.items():
                val = 0
                for s in ['.TW', '.TWO']:
                    t = f"{code}{s}"
                    try:
                        if t in data.columns.levels[0]:
                            row = data[t].iloc[-1]
                            v = (row['Close'] * row['Volume']) / 1e8
                            if v > 0: val = v; break
                    except: pass
                if val > 0: result_map[name] = val; result_map[code] = val
        except: pass
    return result_map

def make_sparkline_svg(data_list, color_hex, width=200, height=50):
    if not data_list or len(data_list) < 2: return ""
    valid = [x for x in data_list if pd.notna(x)]
    if len(valid) < 2: return ""
    mn, mx = min(valid), max(valid)
    rng = mx - mn if mx != mn else 1
    pts = []
    step = width / (len(valid) - 1)
    for i, v in enumerate(valid):
        x = i * step
        y = height - 5 - ((v - mn) / rng * (height - 10))
        pts.append(f"{x:.1f},{y:.1f}")
    
    pts_str = " ".join(pts)
    c = color_hex.lstrip('#')
    rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
    fill = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.15)"
    stroke = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},1)"
    path = f"M {pts[0]} L {pts_str} L {width},{height} L 0,{height} Z"
    return f'<svg viewBox="0 0 {width} {height}" style="width:100%;height:{height}px;overflow:hidden;"><path d="{path}" fill="{fill}" stroke="none"/><polyline points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="2"/></svg>'

@st.cache_data(ttl=20)
def get_global_market_data_with_chart():
    indices = {"^TWII": "🇹🇼 加權", "^TWOII": "🇹🇼 櫃買", "^N225": "🇯🇵 日經", "^DJI": "🇺🇸 道瓊", "^IXIC": "🇺🇸 那斯達克", "^SOX": "🇺🇸 費半", "BTC-USD": "₿ BTC", "ETH-USD": "Ξ ETH"}
    market_data = []
    
    for k, name in indices.items():
        try:
            # 優先使用整合函式
            data_info = get_index_live_data(k, k) # 對於非台股，key=key即可
            
            # 抓取趨勢圖用的歷史資料
            t = yf.Ticker(k)
            hist = t.history(period="5d", interval="60m")
            
            price = data_info.get('price', 0)
            chg = data_info.get('change', 0)
            pct = data_info.get('pct_change', 0)
            
            if price == 0 and not hist.empty:
                price = hist['Close'].iloc[-1]
                prev = t.info.get('previousClose', price)
                chg = price - prev
                pct = (chg / prev) * 100
                
            if price != 0:
                trend = hist['Close'].dropna().tolist() if not hist.empty else []
                color = "#DC2626" if chg > 0 else ("#059669" if chg < 0 else "#6B7280")
                market_data.append({"name": name, "price": f"{price:,.2f}", "change": chg, "pct_change": pct, "color_hex": color, "trend": trend})
        except: pass
    return market_data

def render_global_markets():
    st.markdown("### 🌏 全球指數與加密貨幣")
    mkts = get_global_market_data_with_chart()
    if not mkts: st.info("⏳ 讀取中..."); return
    
    cards = []
    for m in mkts:
        svg = make_sparkline_svg(m['trend'], m['color_hex'], height=50)
        arrow = "▲" if m['change'] > 0 else "▼" if m['change'] < 0 else "-"
        cls = "up" if m['change'] > 0 else "down" if m['change'] < 0 else "flat"
        cards.append(f"""
        <div class="market-card-item">
            <div class="card-content-top">
                <div class="card-header-flex"><span class="card-title-text">{m['name']}</span></div>
                <div class="card-price-flex">
                    <div class="card-price-num">{m['price']}</div>
                    <div class="card-price-chg color-{cls}">{arrow} {abs(m['change']):.2f} ({abs(m['pct_change']):.2f}%)</div>
                </div>
            </div>
            <div class="card-chart-bottom">{svg}</div>
        </div>
        """)
    st.markdown(f'<div class="market-dashboard-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

# --- [V7.0] 趨勢轉折策略型儀表板 ---
def plot_wind_gauge_bias_driven(
    taiex_wind, taiex_streak, taiex_bias, taiex_prev_wind, 
    tpex_wind, tpex_streak, tpex_bias, tpex_prev_wind,
    taiex_data, tpex_data
):
    BLOCK_COUNT = 10
    BLOCK_WIDTH = 100 / BLOCK_COUNT
    
    c_green_list = ['#2E8B57', '#3CB371', '#66CDAA', '#8FBC8F'] 
    c_gray_list  = ['#546E7A', '#78909C']
    c_red_list   = ['#FF8A80', '#FF5252', '#FF1744', '#D50000']
    block_colors_final = c_green_list + c_gray_list + c_red_list

    c_green_base = '#2ecc71' 
    c_gray_base  = '#95a5a6'
    c_red_base   = '#e74c3c'
    c_yellow_warn = '#f1c40f'
    
    COLOR_TAIEX_PTR = "#29B6F6"
    COLOR_TPEX_PTR  = "#FFA726"

    def calc_score(bias_rate, streak_days):
        target_block = 0
        if bias_rate < -4.0:             target_block = 0
        elif -4.0 <= bias_rate < -3.0:   target_block = 1
        elif -3.0 <= bias_rate < -2.0:   target_block = 2
        elif -2.0 <= bias_rate < -1.0:   target_block = 3
        elif -1.0 <= bias_rate < 0.0:    target_block = 4
        elif 0.0 <= bias_rate <= 1.0:    target_block = 5
        elif 1.0 < bias_rate <= 2.0:     target_block = 6
        elif 2.0 < bias_rate <= 3.0:     target_block = 7
        elif 3.0 < bias_rate <= 4.0:     target_block = 8
        else:                            target_block = 9
        base_score = target_block * BLOCK_WIDTH
        capped_days = min(streak_days, 10)
        days_offset = (capped_days / 10.0) * BLOCK_WIDTH
        return max(0, min(100, base_score + days_offset))

    score_taiex = calc_score(taiex_bias, taiex_streak)
    score_tpex  = calc_score(tpex_bias, tpex_streak)

    def get_strategy_card(bias_val, wind_str, prev_wind_str):
        curr = str(wind_str).strip()
        prev = str(prev_wind_str).strip()
        
        if "強風" in prev and "強風" not in curr:
            return "⚠️ <b>趨勢轉弱｜轉為觀望</b><br><span style='font-size:14px; opacity:0.9'>高檔動能衰退，原趨勢改變，停止積極操作</span>", c_yellow_warn
        if "無風" in prev and "陣風" in curr:
            return "🌱 <b>起風訊號｜小量試單</b><br><span style='font-size:14px; opacity:0.9'>底部初現轉折，嚴設停損，小部位嘗試</span>", c_green_base
        
        if bias_val > 2.0:
            return "🚀 <b>強風主昇｜積極操作</b><br><span style='font-size:14px; opacity:0.8'>趨勢強勁，勝率最高，順勢擴大部位</span>", c_red_base
        elif bias_val > 0.5:
            return "🌊 <b>亂流盤堅｜偏多操作</b><br><span style='font-size:14px; opacity:0.8'>多頭架構震盪向上，拉回找買點</span>", c_red_base
        elif -1.0 <= bias_val <= 0.5:
            return "⚖️ <b>循環交界｜區間震盪</b><br><span style='font-size:14px; opacity:0.8'>多空拉鋸，延續性差，多看少做</span>", c_gray_base
        else:
            if "陣風" in curr:
                return "📉 <b>陣風修正｜保守觀望</b><br><span style='font-size:14px; opacity:0.8'>乖離過大但趨勢仍空，搶反彈宜快進快出</span>", c_green_base
            else:
                return "🛡️ <b>無風盤跌｜現金為王</b><br><span style='font-size:14px; opacity:0.8'>趨勢向下，動能不足，避免進場接刀</span>", c_green_base

    if tpex_bias > taiex_bias:
        main_bias, main_wind, main_prev = tpex_bias, tpex_wind, tpex_prev_wind
    else:
        main_bias, main_wind, main_prev = taiex_bias, taiex_wind, taiex_prev_wind
        
    strategy_title, strategy_color = get_strategy_card(main_bias, main_wind, main_prev)

    fig = go.Figure()
    R_OUTER_RING = 1.08; R_MAIN_ARC = 1.00; R_TICK_IN = 0.88; R_LABEL = 1.25
    def get_xy(r, deg): rad = math.radians(deg); return r*math.cos(rad), r*math.sin(rad)

    rx, ry = [], []; 
    for s in range(181): x,y=get_xy(R_OUTER_RING, 180-s); rx.append(x); ry.append(y)
    fig.add_trace(go.Scatter(x=rx, y=ry, mode='lines', line=dict(color='#444444', width=1), hoverinfo='skip', showlegend=False))

    for i in range(BLOCK_COUNT):
        start_a = 180 - (i*BLOCK_WIDTH/100*180); end_a = 180 - ((i+1)*BLOCK_WIDTH/100*180)
        xp, yp = [], []; 
        for s in range(11): ang=start_a+(end_a-start_a)*(s/10); x,y=get_xy(R_MAIN_ARC, ang); xp.append(x); yp.append(y)
        col = block_colors_final[i]
        fig.add_trace(go.Scatter(x=xp, y=yp, mode='lines', line=dict(color=col, width=18), opacity=0.3, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=xp, y=yp, mode='lines', line=dict(color=col, width=6), opacity=1.0, showlegend=False, hoverinfo='skip'))

    def add_label(txt, sub, pct, c):
        lx, ly = get_xy(R_LABEL, 180 - pct/100*180); rot = 90 - (180 - pct/100*180)
        fig.add_annotation(x=lx, y=ly, text=txt, showarrow=False, font=dict(size=15, color=c, weight="bold"), textangle=rot, yshift=10)
        fig.add_annotation(x=lx, y=ly, text=sub, showarrow=False, font=dict(size=11, color="#AAAAAA"), textangle=rot, yshift=-10)
    
    add_label("無風 / 陣風", "保守｜試單", 20, c_green_base)
    add_label("循環交界", "震盪｜觀望", 50, c_gray_base)
    add_label("強風 / 亂流", "積極｜順勢", 80, c_red_base)

    def draw_ptr(score, c, lbl):
        rad = math.radians(180 - score/100*180)
        tx, ty = get_xy(0.82, 180 - score/100*180); bx, by = get_xy(0.72, 180 - score/100*180)
        dx, dy = -math.sin(rad)*0.07, math.cos(rad)*0.07
        fig.add_trace(go.Scatter(x=[tx, bx+dx, bx-dx, tx], y=[ty, by+dy, by-dy, ty], fill='toself', fillcolor=c, line=dict(color='#FFF', width=1), mode='lines', name=lbl, showlegend=False, hoverinfo='skip'))
    
    draw_ptr(score_tpex, COLOR_TPEX_PTR, "櫃買")
    draw_ptr(score_taiex, COLOR_TAIEX_PTR, "加權")

    def draw_info(xc, title, d, c):
        p = d.get('price',0); ch=d.get('change',0); pct=d.get('pct_change',0)
        pc = "#FF2D00" if ch>0 else ("#00E676" if ch<0 else "#FFF")
        arr = "▲" if ch>0 else ("▼" if ch<0 else "")
        fig.add_annotation(x=xc, y=0.45, text=f"● {title}", showarrow=False, font=dict(size=14, color=c, weight="bold"))
        fig.add_annotation(x=xc, y=0.30, text=f"{p:,.0f}" if p>1000 else f"{p:,.2f}", showarrow=False, font=dict(size=24, color=pc, family="Arial Black"))
        fig.add_annotation(x=xc, y=0.18, text=f"{arr} {abs(ch):.2f} ({abs(pct):.2f}%)", showarrow=False, font=dict(size=13, color=pc, weight="bold"))

    draw_info(-0.4, "加權指數", taiex_data, COLOR_TAIEX_PTR)
    draw_info(0.4, "櫃買指數", tpex_data, COLOR_TPEX_PTR)

    fig.add_shape(type="line", x0=-0.8, y0=0.05, x1=0.8, y1=0.05, line=dict(color="#333", width=1, dash="dot"), layer="below")
    fig.add_annotation(
        x=0, y=-0.18, text=strategy_title, showarrow=False,
        font=dict(size=18, color=strategy_color, family="Microsoft JhengHei"),
        align="center", bgcolor="rgba(20,20,20,0.8)", bordercolor=strategy_color, borderwidth=2, borderpad=12
    )
    
    fig.add_annotation(x=-0.5, y=-0.45, text=f"加權: {taiex_wind} ({taiex_streak}天)", showarrow=False, font=dict(size=12, color=COLOR_TAIEX_PTR))
    fig.add_annotation(x=0.5, y=-0.45, text=f"櫃買: {tpex_wind} ({tpex_streak}天)", showarrow=False, font=dict(size=12, color=COLOR_TPEX_PTR))

    fig.update_layout(
        xaxis=dict(range=[-1.5, 1.5], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.5, 1.3], visible=False, fixedrange=True),
        paper_bgcolor='#1a1a1a', plot_bgcolor='#1a1a1a', height=420, margin=dict(t=30, b=10, l=10, r=10), template='plotly_dark'
    )
    return fig

# --- 5. 頁面: 戰情儀表板 ---
def show_dashboard():
    df = load_db()
    if df.empty:
        st.info("📭 目前沒有每日戰情資料，請至後台新增。")
        return

    st.sidebar.header("📅 歷史回顧")
    dates = pd.to_datetime(df['date']).dt.date
    pick = st.sidebar.date_input("選擇日期", value=dates.max(), min_value=dates.min(), max_value=dates.max())
    s_date = pick.strftime("%Y-%m-%d")
    selected_date = s_date # Alias for compatibility
    
    day_df = df[df['date'] == s_date]
    if day_df.empty:
        st.error(f"❌ 找不到 {s_date} 的資料")
        return
    day_data = day_df.iloc[0]
    
    c1, c2 = st.columns([8, 1.5])
    with c1: 
        st.markdown(f"## 📅 {s_date} 風箏戰情室")
    with c2: 
        if st.button("🔄 更新數據"):
            get_global_market_data_with_chart.clear()
            st.rerun()
        
    render_global_markets()
    st.divider()

    # --- 整合使用者提供的邏輯 ---
    st.markdown("### 🌬️ 每日風度與風箏數")

    wind_status = day_data['wind']
    # wind_streak = calculate_wind_streak(df, selected_date) # 註：此變數未被使用，但保留計算邏輯
    
    # 1. 獲取 櫃買指數 (TPEx)
    tpex_info = get_index_live_data("^TWOII", "^TWOII")
    
    # 2. 獲取 加權指數 (TAIEX)
    taiex = get_index_live_data("^TWII", "^TWII")

    try:
        twii = yf.Ticker("^TWII") 
        hist = twii.history(period="5d")
        if not hist.empty:
            price_now = hist['Close'].iloc[-1]
            price_prev = hist['Close'].iloc[-2]
            change = price_now - price_prev
            pct = (change / price_prev) * 100
            taiex = {'price': price_now, 'change': change, 'pct_change': pct}
    except Exception: pass

    # A. 加權指數 (TAIEX)
    df_taiex = load_data_from_gsheet("TAIEX")
    taiex_w_status = "無資料"
    taiex_w_prev = "無資料" # [新增] 前日風度
    taiex_w_streak = 0
    taiex_w_bias = 0.0
    
    if not df_taiex.empty:
        if '日期' in df_taiex.columns:
            df_taiex['date'] = df_taiex['日期'].dt.strftime('%Y-%m-%d')
        if '風度' in df_taiex.columns:
            df_taiex['wind'] = df_taiex['風度']
            
        latest_taiex = df_taiex.iloc[-1]
        taiex_w_status = str(latest_taiex['風度']).strip()
        taiex_w_streak = calculate_wind_streak(df_taiex, latest_taiex['日期'].strftime("%Y-%m-%d"))
        try: taiex_w_bias = float(str(latest_taiex['乖離率']).replace('%', '').strip())
        except: taiex_w_bias = 0.0
        
        # [新增] 抓取前一筆資料的風度
        if len(df_taiex) >= 2:
            taiex_w_prev = str(df_taiex.iloc[-2]['風度']).strip()

    # B. 櫃買指數 (TPEx)
    df_tpex = load_data_from_gsheet("TPEx")
    tpex_w_status = "無資料"
    tpex_w_prev = "無資料" # [新增] 前日風度
    tpex_w_streak = 0
    tpex_w_bias = 0.0
    
    if not df_tpex.empty:
        if '日期' in df_tpex.columns:
            df_tpex['date'] = df_tpex['日期'].dt.strftime('%Y-%m-%d')
        if '風度' in df_tpex.columns:
            df_tpex['wind'] = df_tpex['風度']

        latest_tpex = df_tpex.iloc[-1]
        tpex_w_status = str(latest_tpex['風度']).strip()
        tpex_w_streak = calculate_wind_streak(df_tpex, latest_tpex['日期'].strftime("%Y-%m-%d"))
        try: tpex_w_bias = float(str(latest_tpex['乖離率']).replace('%', '').strip())
        except: tpex_w_bias = 0.0
        
        # [新增] 抓取前一筆資料的風度
        if len(df_tpex) >= 2:
            tpex_w_prev = str(df_tpex.iloc[-2]['風度']).strip()

    # --- 繪圖 ---
    col_gauge, col_cards = st.columns([4, 6], gap="large") 
    
    with col_gauge:
        gauge_fig = plot_wind_gauge_bias_driven(
            taiex_w_status, taiex_w_streak, taiex_w_bias, taiex_w_prev,
            tpex_w_status, tpex_w_streak, tpex_w_bias, tpex_w_prev,
            taiex, tpex_info
        )
        st.markdown('<div style="background-color:#1a1a1a; border-radius:20px; padding:10px; box-shadow:0 8px 16px rgba(0,0,0,0.2);">', unsafe_allow_html=True)
        st.plotly_chart(gauge_fig, use_container_width=True, height=380, config={'displayModeBar': False, 'responsive': True}, key="main_gauge")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cards:
        st.markdown("""
        <style>
            div.kite-metrics-grid { 
                display: grid; 
                grid-template-columns: repeat(3, 1fr); 
                gap: 15px; 
                align-items: stretch; 
            }
            @media (max-width: 768px) { div.kite-metrics-grid { grid-template-columns: 1fr; } }
            
            .kite-box { 
                background-color: #FFFFFF; 
                border-radius: 16px; 
                padding: 20px 10px; 
                text-align: center; 
                border: 1px solid #EEEEEE; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.06); 
                display: flex; 
                flex-direction: column; 
                justify-content: center; 
                align-items: center; 
                height: 160px;
                transition: transform 0.2s;
            }
            .kite-box:hover { transform: translateY(-5px); }
            .k-label { font-size: 1.15rem; color: #555; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.5px; }
            .k-value { font-size: 3.2rem; font-weight: 900; color: #2c3e50; line-height: 1.0; font-family: 'Arial', sans-serif; }
        </style>
        """, unsafe_allow_html=True)
        
        cards_html = f"""
        <div class="kite-metrics-grid">
            <div class="kite-box" style="border-top: 6px solid #f39c12;">
                <div class="k-label">🪁 打工型風箏</div>
                <div class="k-value">{day_data["part_time_count"]}</div>
            </div>
            <div class="kite-box" style="border-top: 6px solid #3498db;">
                <div class="k-label">💪 上班族強勢週</div>
                <div class="k-value">{day_data["worker_strong_count"]}</div>
            </div>
            <div class="kite-box" style="border-top: 6px solid #9b59b6;">
                <div class="k-label">📈 上班族週趨勢</div>
                <div class="k-value">{day_data["worker_trend_count"]}</div>
            </div>
        </div>
        """
        st.markdown(cards_html, unsafe_allow_html=True)

    st.divider()

    # 策略選股名單
    st.markdown("### 🎯 策略選股名單")
    def show_stock_list(title, stock_str, color_theme="blue"):
        if pd.isna(stock_str) or str(stock_str).strip() == "": return
        stocks = [s.strip() for s in str(stock_str).split('、') if s.strip()]
        if not stocks: return
        st.markdown(f"#### {title} ({len(stocks)}檔)")
        turnover_map = prefetch_turnover_data(stocks, s_date, day_data.get('manual_turnover', '{}'))
        cols = st.columns(6)
        for i, stock in enumerate(stocks):
            code = smart_get_code(stock)
            t_val = turnover_map.get(stock, turnover_map.get(code, 0))
            clean_name = stock.replace("(CB)", "")
            cb_badge = '<span class="cb-badge">CB</span>' if "(CB)" in stock else ""
            t_html = f'<span class="turnover-val">💰 {t_val:.1f}億</span>' if t_val > 0 else ""
            html = f"""<div class="stock-tag" style="border-color:{color_theme}; color:#333;">{clean_name}{cb_badge}{t_html}</div>"""
            cols[i % 6].markdown(html, unsafe_allow_html=True)
        st.markdown("")

    show_stock_list("⚡ 打工仔 (強勢)", day_data['worker_strong_list'], "#e74c3c")
    show_stock_list("📈 打工仔 (趨勢)", day_data['worker_trend_list'], "#3498db")
    show_stock_list("🛡️ 慣老闆 (拉回)", day_data['boss_pullback_list'], "#2ecc71")
    show_stock_list("💰 慣老闆 (抄底)", day_data['boss_bargain_list'], "#f1c40f")
    show_stock_list("🔥 營收強勢", day_data['top_revenue_list'], "#9b59b6")

# --- 6. 頁面: 管理後台 ---
def auto_update_index_history(df, ticker_symbol):
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        stock = yf.Ticker(ticker_symbol, session=session)
        hist = pd.DataFrame()
        for i in range(3):
            try:
                hist = stock.history(period="3mo")
                if not hist.empty: break
                time.sleep(1)
            except: time.sleep(2)
        
        if hist.empty: return df, "❌ 無法取得 Yahoo 報價 (Rate Limit)，請稍後再試。"
        
        last = hist.iloc[-1]
        d_str = last.name.strftime('%Y-%m-%d')
        close = float(last['Close'])
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        if pd.isna(ma20): ma20 = close 
        bias = (close - ma20) / ma20 * 100
        
        current_dates = df['日期'].astype(str).values if '日期' in df.columns else []
        if d_str in current_dates: return df, f"⚠️ {d_str} 資料已存在，無需更新。"
        
        wind = "無風"
        if bias > 2: wind = "強風"
        elif bias > 0.5: wind = "亂流"
        elif bias < -2: wind = "陣風"
        
        new_row = pd.DataFrame([{"日期": d_str, "收": round(close, 2), "風度": wind, "20MA": round(ma20, 2), "乖離率": f"{bias:.2f}%"}])
        df = pd.concat([df, new_row], ignore_index=True)
        if '日期' in df.columns:
            df['dt_temp'] = pd.to_datetime(df['日期'])
            df = df.sort_values('dt_temp').drop(columns=['dt_temp'])
        return df, f"✅ 已新增 {d_str}: {wind} (乖離 {bias:.2f}%)"
    except Exception as e: return df, f"❌ 更新錯誤: {str(e)}"

def render_history_manager(tab, sheet_name, ticker):
    with tab:
        st.subheader(f"📂 {sheet_name} 歷史資料")
        df = load_data_from_gsheet(sheet_name)
        
        if df.empty:
            st.warning(f"⚠️ {sheet_name} 目前沒有資料或讀取失敗。")
            st.info("💡 請確認：\n1. Google Sheet 是否已共用給機器人 Email？\n2. 該分頁的第一列是否已填入欄位名稱？(日期, 收, 風度, 20MA, 乖離率)")
            if st.button(f"🔄 我已設定好，重新讀取 {sheet_name}"):
                load_data_from_gsheet.clear()
                st.rerun()
            return

        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button(f"⚡ 自動抓取今日數據", key=f"btn_{sheet_name}"):
                new_df, msg = auto_update_index_history(df, ticker)
                if "✅" in msg:
                    save_data_to_gsheet(new_df, sheet_name)
                    st.success(msg); time.sleep(1); st.rerun()
                else: st.warning(msg)
        
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{sheet_name}", height=350)
        if st.button(f"💾 儲存 {sheet_name} 變更", key=f"sv_{sheet_name}"):
            ok, m = save_data_to_gsheet(edited, sheet_name)
            if ok: st.success(m); time.sleep(1); st.rerun()
            else: st.error(m)

def show_admin_panel():
    st.title("⚙️ 資料管理後台 (Google Sheets)")
    if not GOOGLE_API_KEY: st.error("❌ 未設定 API Key"); return

    t1, t2, t3, t4 = st.tabs(["📈 櫃買歷史", "📊 加權歷史", "📥 新增每日資料", "📝 主資料庫編輯"])
    render_history_manager(t1, "TPEx", "^TWOII")
    render_history_manager(t2, "TAIEX", "^TWII")
    
    with t3:
        st.subheader("📥 新增每日戰情資料")
        if 'preview_df' not in st.session_state: st.session_state.preview_df = None
        uploaded_file = st.file_uploader("上傳每日截圖", type=["png", "jpg", "jpeg"])
        
        if uploaded_file and st.button("🤖 開始 AI 解析", type="primary"):
            # 簡化展示 AI 解析 (需使用者填入 Gemini 邏輯)
            st.info("AI 解析功能需配合 Gemini API 實作") 
            # 這裡應呼叫 ai_analyze_v86 並處理回傳

        if st.session_state.preview_df is not None:
            st.markdown("#### 👇 確認匯入資料")
            edited_new = st.data_editor(st.session_state.preview_df, num_rows="dynamic", use_container_width=True)
            if st.button("✅ 存入 Google Sheets", type="primary"):
                save_batch_data(edited_new)
                st.success(f"成功匯入 {len(edited_new)} 筆資料！")
                st.session_state.preview_df = None
                time.sleep(1); st.rerun()

    with t4:
        st.subheader("📝 完整資料庫編輯")
        df_main = load_db()
        if df_main.empty:
            st.warning("⚠️ Daily_Main 目前沒有資料。請確認 Google Sheet 分頁名稱與第一列標題。")
            st.code("date, wind, part_time_count, worker_strong_count, worker_trend_count, worker_strong_list, worker_trend_list, boss_pullback_list, boss_bargain_list, top_revenue_list, last_updated, manual_turnover")
        else:
            ed_main = st.data_editor(df_main, num_rows="dynamic", use_container_width=True, height=500)
            if st.button("💾 儲存主資料庫變更"):
                ok, m = save_data_to_gsheet(ed_main, "Daily_Main")
                if ok: st.success(m); time.sleep(1); st.rerun()
                else: st.error(m)

# --- 7. 主程式 ---
def main():
    if 'is_admin' not in st.session_state: st.session_state.is_admin = False
    
    with st.sidebar:
        st.title("導航")
        page = st.radio("前往", ["📊 戰情儀表板", "⚙️ 管理後台"])
        if page == "⚙️ 管理後台" and not st.session_state.is_admin:
            pwd = st.text_input("密碼", type="password")
            if pwd == "8899abc168": st.session_state.is_admin = True; st.rerun()
            else: st.stop()
            
    if page == "📊 戰情儀表板": show_dashboard()
    else: show_admin_panel()

if __name__ == "__main__":
    main()
