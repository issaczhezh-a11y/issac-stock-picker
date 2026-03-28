import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 字典配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资研究终端", "sidebar_header": "筛选设置",
        "search_label": "🔍 个股深度搜索 (输入代码)", "ma200_label": "📈 仅限 MA200 上方",
        "pe_label": "最高 P/E", "peg_label": "最高 PEG", "fcf_label": "最低 FCF (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高负债率 (%)",
        "index_label": "📊 自动扫描范围", "scan_btn": "开始批量扫描",
        "matching_only": "🔍 只看符合条件的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "量比(7D)", "col_short": "做空率", "col_res": "结果",
        "last_up": "⏱️ 最后更新: "
    },
    "EN": {
        "title": "🍎 Issac Investment Terminal", "sidebar_header": "Settings",
        "search_label": "🔍 Manual Ticker Search", "ma200_label": "📈 Above MA200 Only",
        "pe_label": "Max P/E", "peg_label": "Max PEG", "fcf_label": "Min FCF ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt (%)",
        "index_label": "📊 Auto-Scan Range", "scan_btn": "Start Batch Scan",
        "matching_only": "🔍 Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "Vol/7D", "col_short": "Short %", "col_res": "Result",
        "last_up": "⏱️ Last Updated: "
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# --- 2. 侧边栏：手动搜索 & 批量筛选 ---
st.sidebar.subheader(t["search_label"])
manual_search = st.sidebar.text_input("Example: TSLA, BABA, NVDA", "").upper().strip()

st.sidebar.divider()
st.sidebar.subheader(t["sidebar_header"])
above_m200_check = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 100.0, 25.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.2) 
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
min_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt = st.sidebar.slider(t["debt_label"], 0.0, 300.0, 100.0)

# --- 3. 核心工具函数 ---
def get_stock_data(symbol, t_pe, t_peg, m_roe, m_fcf, m_debt, m200_check):
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period="1y")
        if len(h) < 35: return None
        
        cur_p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        
        diff = h['Close'].diff()
        g, l = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (g/l))) if l != 0 else 50
        
        e12, e26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
        macd_v = e12 - e26
        macd_txt = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
        
        inf = tk.info
        pe, peg = inf.get('forwardPE'), inf.get('pegRatio') or inf.get('trailingPegRatio')
        roe, fcf, debt = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9, inf.get('debtToEquity') or 0
        sh = (inf.get('shortPercentOfFloat') or 0)*100
        
        f_m = (pe and 0 < pe < t_pe) and (peg is not None and peg < t_peg) and (roe > m_roe) and (fcf > m_fcf) and (debt < m_debt)
        ok = "✅ 符合" if (f_m and cur_p > m200 if m200_check else f_m) else "❌ 不符"
        
        return {
            t["col_code"]:symbol, t["col_price"]:round(cur_p, 2), t["col_ma200
