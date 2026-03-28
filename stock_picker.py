import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 配置与字典 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资筛选器", "sidebar_header": "筛选设置",
        "ma200_label": "📈 仅限 MA200 上方", "pe_label": "最高 P/E",
        "peg_label": "最高 PEG", "fcf_label": "最低 FCF (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高负债率 (%)",
        "index_label": "📊 扫描范围", "scan_btn": "开始扫描",
        "matching_only": "🔍 只看符合条件的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "量比(7D)", "col_short": "做空率", "col_res": "结果",
        "last_up": "⏱️ 最后更新: "
    },
    "EN": {
        "title": "🍎 Issac-Style Picker", "sidebar_header": "Settings",
        "ma200_label": "📈 Above MA200 Only", "pe_label": "Max P/E",
        "peg_label": "Max PEG", "fcf_label": "Min FCF ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt (%)",
        "index_label": "📊 Select Index", "scan_btn": "Start Scan",
        "matching_only": "🔍 Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "Vol/7D", "col_short": "Short %", "col_res": "Result",
        "last_up": "⏱️ Last Updated: "
    }
}

st.set_page_config(page_title="Issac Picker", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# 侧边栏参数
above_ma200 = st.sidebar.checkbox(t["ma200_label"], value=False)
t_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
t_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
m_fcf = st.sidebar.number_input(t["fcf_label"], value=1.0)
t_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
m_debt = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

@st.cache_data
def get_tk(idx_name):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_name == "S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        df = pd.read_html(resp)[0 if idx_name == "S&P 500" else 4]
    return [str(s).replace('.', '-') for s in df.iloc[:, 0].tolist()]

idx_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tk(idx_mode)

if 'res' not in st.session_state: st.session_state.res, st.session_state.up_t = None, None

# --- 4. 扫描 ---
if st.button(t["scan_btn"]):
    data = []
    with st.spinner('Analyzing...'):
        for s in tickers:
            try:
                tk = yf.Ticker(s)
                h = tk.history(period="1y")
                if len(h) < 35: continue
                cur_p, m200 = float(h['Close'].iloc[-1]), float(h['Close'].rolling(200).mean().iloc[-1])
                v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
                diff = h['Close'].diff()
                rsi = 100 - (100 / (1 + (diff.where(diff > 0, 0).rolling(14).mean() / -diff.where(diff < 0, 0).rolling(14).mean()))).iloc[-1]
                ema12, ema26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
                macd = "▲ 金叉" if (ema12 - ema26).iloc[-1] > (ema12 - ema26).ewm(span=9).mean().iloc[-1] else "▼ 死叉"
                inf = tk.info
                pe, peg, roe = float(inf.get('forwardPE', 0)), float(inf.get('pegRatio', 0.1)), float(inf.get('returnOnEquity', 0)) * 100
                fcf, debt, sh = float(inf.get('freeCashflow', 0))/1e9, float(inf.get('debtToEquity', 0)), float(inf.get('shortPercentOfFloat', 0))*100
                f_m = (0 < pe < t_pe and 0 <= peg < t_peg and roe > t_roe and fcf > m_fcf and debt < m_debt)
                ok = "✅ 符合" if (f_m and cur_p > m200 if above_ma200 else f_m) else "❌ 不符"
                data.append({t["col_code"]:s, t["col_price"]:f"${cur_p:.2f}", t["col_ma200"]:f"${m200:.2f}", t["col_pe"]:pe, t["col_peg"]:peg, t["col_roe"]:round(roe,1), t["col_fcf"]:round(fcf,1), t["col_debt"]:round(debt,1), t["col_rsi"]:round(rsi,1), t["col_macd"]:macd, t["col_short"]:f"{sh:.1f}%", t["col_vol"]:f"{v_r:+.1f}%", t["col_res"]:ok, "_p":cur_p, "_m":m200, "_sh":sh})
            except: pass
    st.session_state.res = data
    st.session_state.up_t = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示与 AI 报告 ---
if st.session_state.res:
    df = pd.DataFrame(st.session_state.res)
    st.caption(f"{t['last_up']} {st.session_state.up_t}")
    m_df = df[df[t["col_res"]].str.contains("✅")]
    if not m_df.empty:
        st.subheader("🤖 Issac AI Deep Dive")
        sel = st.selectbox("🎯 Target:", m_df[t["col_code"]].tolist())
        s = m_df[m_df[t["col_code"]] == sel].iloc[0]
        with st.expander(f"📑 {sel} - Deep Report", expanded=True):
            if s['_sh'] > 5: st.error(f"⚠️ High Short: {s['_sh']:.1f}%")
            if s['_p'] < s['_m']: st.warning("❌ Below MA200: Weak Trend")
            c1, c2, c3 = st.columns(3)
            c1.metric("PEG", s[t['col_peg']])
            c2.metric("ROE", f"{s[t['col_roe']]}%")
            c3.metric("FCF", f"${s[t['col_fcf']]}B")
            st.write(f"指标状态: RSI {s[t['col_rsi']]}, MACD {s[t['col_macd']]}, 量比 {s[t['col_vol']]}")
    st.dataframe(m_df if st.checkbox(t["matching_only"], value=True) else df, use_container_width=True, hide_index=True)
