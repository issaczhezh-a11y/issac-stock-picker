import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 字典配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 投研实验室", "search_label": "🔍 个股透视",
        "pe": "最高 P/E", "peg": "最高 PEG", "roe": "最低 ROE%", "fcf": "最低 FCF",
        "scan_btn": "开始批量扫描", "match_only": "🔍 只看符合条件的股票",
        "snapshot": "📊 参数快照", "report": "深度研报", "verdict": "🏆 最终评级"
    },
    "EN": {
        "title": "🍎 Issac Investment Lab", "search_label": "🔍 Ticker Search",
        "pe": "Max P/E", "peg": "Max PEG", "roe": "Min ROE%", "fcf": "Min FCF",
        "scan_btn": "Start Scan", "match_only": "🔍 Matches Only",
        "snapshot": "📊 Metrics Snapshot", "report": "Deep Report", "verdict": "🏆 Final Verdict"
    }
}

st.set_page_config(page_title="Issac Lab", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# --- 2. 侧边栏 ---
search_q = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t["pe"], value=25.0)
t_peg = st.sidebar.number_input(t["peg"], value=1.2)
m_roe = st.sidebar.number_input(t["roe"], value=15.0)
m_fcf = st.sidebar.number_input(t["fcf"], value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox("Market Range", ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t["scan_btn"])

# --- 3. 核心逻辑 ---
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
        sh, d_e = (inf.get('shortPercentOfFloat') or 0)*100, (inf.get('debtToEquity') or 0)
        ok = (0 < pe < t_pe and 0 <= peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {"Symbol":s, "Price":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "Debt%":round(d_e,1), "Short%":f"{sh:.1f}%", "Vol%":f"{v_r:+.1f}%", "Match":"✅" if ok else "❌", "_p":p, "_m":m200, "_sh":sh, "_v":v_r, "_sum":inf.get('longBusinessSummary', "N/A"), "_ind":inf.get('industry', "N/A")}
    except: return None

def show_rpt(s):
    st.subheader(f"{t['snapshot']} - {s['Symbol']}")
    # 🎯 物理级列过滤：只允许白名单显示的列
    white_list = ["Symbol", "Price", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "Debt%", "Short%", "Vol%", "Match"]
    st.dataframe(pd.DataFrame([s])[white_list], use_container_width=True, hide_index=True)
    
    with st.expander(f"📑 {s['Symbol']} - {t['report']}", expanded=True):
        st.write(f"**Industry:** `{s['_ind']}`")
        st.write(f"**Business:** {s['_sum'][:1000]}...")
        st.info("🔥 Elite Moat" if s['ROE%'] > 30 else "✅ Solid Moat")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG", s['PEG'])
        c2.metric("ROE", f"{s['ROE%']}%")
        c3.metric("FCF", f"${s['FCF$B']}B")
        st.markdown("---")
        r1, r2 = st.columns(2)
        if s['_sh'] > 5: r1.error(f"⚠️ High Shorting: {s['_sh']:.1f}%")
        else: r1.success("✅ Stable Sentiment")
        if s['_p'] < s['_m']: r2.error("❌ Bearish (Below MA200)")
        else: r2.success("📈 Bullish (Above MA200)")
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        st.success(f"### {t['verdict']}: {['C','B','A','A+'][score]}")

# --- 4. 互斥展示逻辑 ---
if search_q:
    st.divider()
    res = fetch(search_q)
    if res: show_rpt(res)
    else: st.error("Ticker not found.")
else:
    # 只有没搜个股时，才处理批量扫描逻辑
    if scan_btn:
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r: 
            tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
        batch = []
        bar = st.progress(0)
        for i, ticker in enumerate(tks):
            item = fetch(str(ticker).replace('.','-'))
            if item: batch.append(item)
            bar.progress((i+1)/len(tks))
        st.session_state.batch_res = batch

    if 'batch_res' in st.session_state:
        st.divider()
        df = pd.DataFrame(st.session_state.batch_res)
        white_list = ["Symbol", "Price", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "Debt%", "Short%", "Vol%", "Match"]
        m_df = df[df["Match"]=="✅"][white_list]
        if not m_df.empty:
            sel = st.selectbox("Select Target:", m_df["Symbol"].tolist())
            show_rpt(df[df["Symbol"]==sel].iloc[0])
        st.dataframe(m_df if st.checkbox(t["match_only"], value=True) else df[white_list], use_container_width=True, hide_index=True)
