import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone
import time
from lang_config import LANG 

# --- 1. 设置 ---
st.set_page_config(page_title="Issac Terminal Pro", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG.get(lang_choice, LANG["CN"])
st.title(t.get("title", "Issac Terminal"))

WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "Inst%", "P/E", "Match"]

# --- 2. 侧边栏 ---
st.sidebar.header(t.get("sidebar_header", "Settings"))
search_ticker = st.sidebar.text_input(t.get("search_label", "Ticker"), "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input("Max PE", value=50.0)
t_peg = st.sidebar.number_input("Max PEG", value=2.0)
m_roe = st.sidebar.number_input("Min ROE", value=5.0)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox("Scan Range", ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button("Start Scan")

# --- 3. 宏观风控 (带缓存) ---
@st.cache_data(ttl=3600)
def get_macro():
    try:
        vix = yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1]
        tnx = yf.Ticker("^TNX").history(period="5d")['Close'].iloc[-1]
        spy_h = yf.Ticker("SPY").history(period="1y")
        spy_p, spy_ma200 = spy_h['Close'].iloc[-1], spy_h['Close'].rolling(200).mean().iloc[-1]
        score = int(np.clip(100 - (vix * 2.5) + (25 if spy_p > spy_ma200 else -10), 0, 100))
        mood = "mood_panic" if score < 35 else ("mood_fear" if score < 60 else "mood_greed")
        return {"vix": round(vix, 2), "tnx": round(tnx, 2), "mood": mood, "score": score, "panic": score < 35}
    except: return None

# --- 4. 核心分析引擎 (潜行模式) ---
@st.cache_data(ttl=1800)
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        # 🎯 潜行第一步：只拿 1 年历史价格（最不容易被封）
        h = tk.history(period="1y")
        if h.empty: return None
        
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1] if not m200_s.isna().all() else p
        
        # 🎯 潜行第二步：尝试拿轻量级 Info，失败就用 N/A 填充
        try:
            inf = tk.info
            is_throttled = False if inf and 'symbol' in inf else True
        except:
            inf = {}
            is_throttled = True
            
        # 容错提取
        pe = inf.get('forwardPE') or inf.get('trailingPE') or 0
        peg = inf.get('pegRatio') or 0
        roe = (inf.get('returnOnEquity') or 0) * 100
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        cash, debt = (inf.get('totalCash', 0))/1e9, (inf.get('totalDebt', 0))/1e9
        
        # 🎯 潜行第三步：财报日期（只拿最稳的原始时间戳）
        n_date, n_days = "N/A", 999
        try:
            raw_ts = inf.get('nextEarningsDate')
            if raw_ts:
                dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                n_date, n_days = dt.strftime('%Y-%m-%d'), (dt - datetime.now(timezone.utc)).days
        except: pass

        # RS 强度
        h_3m = tk.history(period="3mo")
        s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100 if not h_3m.empty else 0
        spy_ret = 5.0 # 默认标普 3 个月回报，防 SPY 接口也断流

        ok = (roe > m_roe or is_throttled) # 如果被限流，默认显示
        
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": round(pe, 2) if pe > 0 else "N/A", "ROE%": round(roe, 1) if roe > 0 else "N/A", 
            "Inst%": f"{inst:.1f}%" if inst > 0 else "N/A", "PEG": round(peg, 2) if peg > 0 else "N/A",
            "FCF$B": round((inf.get('freeCashflow', 0)/1e9), 1), "Debt%": round(inf.get('debtToEquity', 0), 1),
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_inst": inst, "_cash": cash, "_debt": debt,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_n_e": n_date, "_n_d": n_days, "_throttled": is_throttled,
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "No Summary Available.")
        }
    except: return None

def render_report(s):
    # 1. 宏观提示
    macro = get_macro()
    if macro:
        st.markdown(f"### {t.get('macro_title')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("VIX", macro['vix'])
        m2.metric("10Y Yield", f"{macro['tnx']}%")
        m3.subheader(t.get(macro['mood']))
    
    # 限流警示
    if s['_throttled']:
        st.warning(t.get('throttled_msg'))

    # 2. 评分
    score = 0
    score += 30 if s['Price'] > s['MA200'] else 0
    score += 20 if s['_s_ret'] > s['_spy_ret'] else 0
    score += 50 if not s['_throttled'] and s['ROE%'] != "N/A" and s['ROE%'] > 15 else 20 # 限流时给予基础分
    
    st.divider()
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    c2.metric(t.get('score_label'), f"{score}/100", delta=f"{score-50}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 3. 核心趋势图 (即便限流也必须出)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t.get('chart_close'), line=dict(color='#00d1ff')))
    fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t.get('chart_ma200'), line=dict(color='#ffaa00', dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 4. 财报雷达 (增加备用链接)
    st.markdown(f"### {t.get('earnings_radar_title')}")
    col_e1, col_e2 = st.columns(2)
    col_e1.info(f"📅 **预计日期**: `{s['_n_e']}`")
    col_e2.markdown(f"🔗 [Yahoo Finance 实时财报直达](https://finance.yahoo.com/quote/{s['Symbol']}/analysis)")

    # 5. 详细研报
    st.markdown(f"# {t.get('report_title')}")
    with st.expander(t.get('moat_title'), expanded=True):
        st.write(f"**{t.get('industry')}**: `{s['_ind']}`")
        st.write(s['_sum'][:800] + "...")
    
    with st.expander(t.get('fin_title'), expanded=True):
        f1, f2 = st.columns(2)
        f1.metric("Cash (Total)", f"${s['_cash']:.1f}B")
        f2.metric("Debt (Total)", f"${s['_debt']:.1f}B")
        st.write(f"ROE: **{s['ROE%']}%** | P/E: **{s['P/E']}** | PEG: **{s['PEG']}**")

    st.divider()
    v_idx = 1 if s['Price'] < s['MA200']*0.97 or (macro and macro['panic']) else (3 if score > 70 else (2 if score > 40 else 1))
    st.success(f"## {t.get('verdict_title')}：{t.get('verdicts')[v_idx]}")
    st.info(f"💡 {t.get('strategy_label')}：{t.get('strategies')[v_idx]}")

# --- 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker not found on Yahoo database. Please check the Symbol.")

if scan_btn:
    # 批量扫描依然走缓存逻辑
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
    batch_res, bar = [], st.progress(0)
    for i, ticker in enumerate(tks[:50]): # 限制扫描数量防封
        item = get_analysis(str(ticker).replace('.','-'))
        if item: batch_res.append(item)
        bar.progress((i+1)/50)
    st.session_state.batch_res = batch_res
