import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 配置 ---
LANG = {"CN": {"title": "🍎 Issac 投研终端", "search": "🔍 个股搜索 (如: TSLA)", "scan": "📊 批量扫描", "res": "结果"}, 
        "EN": {"title": "🍎 Issac Terminal", "search": "🔍 Manual Search", "scan": "📊 Batch Scan", "res": "Result"}}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# 侧边栏参数
search_ticker = st.sidebar.text_input(t["search"], "").upper().strip()
st.sidebar.divider()
target_pe = st.sidebar.slider("Max P/E", 5.0, 100.0, 25.0)
target_peg = st.sidebar.slider("Max PEG", 0.1, 3.0, 1.2)
min_roe = st.sidebar.slider("Min ROE (%)", 0.0, 50.0, 15.0)
min_fcf = st.sidebar.number_input("Min FCF ($B)", value=0.5)

# --- 2. 核心抓取函数 (极其稳健) ---
def fetch(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        pe, peg = inf.get('forwardPE', 0), (inf.get('pegRatio') or inf.get('trailingPegRatio') or 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        sh = (inf.get('shortPercentOfFloat') or 0)*100
        # 判定
        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {"Symbol":s, "Price":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "Short%":f"{sh:.1f}%", "Vol%":f"{v_r:+.1f}%", "Status":"✅" if ok else "❌", "_p":p, "_m":m200, "_sh":sh, "_v":v_r}
    except: return None

# --- 3. 报告展示组件 ---
def show_rpt(s):
    with st.expander(f"📑 {s['Symbol']} - JPMorgan Institutional Report", expanded=True):
        if s['_sh'] > 5: st.error(f"⚠️ High Short Ratio: {s['_sh']:.1f}%")
        if s['_p'] < s['_m']: st.warning("❌ Bearish: Price below MA200")
        else: st.success("📈 Bullish: Price above MA200")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG", s['PEG'], delta="Value" if s['PEG']<0.8 else None)
        c2.metric("ROE", f"{s['ROE%']}%")
        c3.metric("FCF", f"${s['FCF$B']}B")
        st.write(f"**Analysis:** PE `{s['P/E']}` | Vol Ratio `{s['Vol%']}` | FCF ${s['FCF$B']}B")
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        st.success(f"🏆 Final Verdict: {['Wait (C)','Hold (B)','Buy (A)','STRONG BUY (A+)'][score]}")

# --- 4. 逻辑执行 ---
# A. 手动搜索
if search_ticker:
    res = fetch(search_ticker)
    if res: show_rpt(res)
    else: st.error("Ticker Not Found.")

# B. 批量扫描
st.divider()
idx = st.sidebar.selectbox("Index", ["S&P 500", "Nasdaq 100"])
if st.sidebar.button(t["scan"]):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx=="S&P 500" else 4].iloc[:, 0].tolist()
    
    batch = []
    bar = st.progress(0)
    for i, s in enumerate(tks):
        item = fetch(str(s).replace('.','-'))
        if item: batch.append(item)
        bar.progress((i+1)/len(tks))
    st.session_state.batch_res = batch

if 'batch_res' in st.session_state:
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["Status"]=="✅"]
    if not m_df.empty:
        sel = st.selectbox("Select Match:", m_df["Symbol"].tolist())
        show_rpt(df[df["Symbol"]==sel].iloc[0])
    st.dataframe(m_df if st.checkbox("Show Matches Only", value=True) else df.drop(columns=["_p","_m","_sh","_v"]), use_container_width=True, hide_index=True)
