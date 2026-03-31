import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import time
from lang_config import LANG 

# --- 1. 设置 ---
st.set_page_config(page_title="Issac Terminal Pro", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG.get(lang_choice, LANG["CN"])
st.title(t.get("title", "Issac Terminal"))

WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "Inst%", "P/E", "PEG", "Match"]

# --- 2. 侧边栏 ---
st.sidebar.header(t.get("sidebar_header", "Settings"))
search_ticker = st.sidebar.text_input(t.get("search_label", "Ticker"), "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t.get("pe_label", "Max PE"), value=35.0, help=t.get("pe_help", ""))
t_peg = st.sidebar.number_input(t.get("peg_label", "Max PEG"), value=1.5, help=t.get("peg_help", ""))
m_roe = st.sidebar.number_input(t.get("roe_label", "Min ROE"), value=10.0, help=t.get("roe_help", ""))
m_fcf = st.sidebar.number_input(t.get("fcf_label", "Min FCF"), value=0.1, help=t.get("fcf_help", ""))
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t.get("scan_range", "Scan Range"), ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t.get("scan_btn", "Scan"))

# --- 3. 宏观风控引擎 ---
@st.cache_data(ttl=3600)
def get_macro_radar():
    try:
        v_h = yf.Ticker("^VIX").history(period="5d")
        vix = v_h['Close'].iloc[-1] if not v_h.empty else 20.0
        t_h = yf.Ticker("^TNX").history(period="5d")
        tnx = t_h['Close'].iloc[-1] if not t_h.empty else 4.0
        spy_h = yf.Ticker("SPY").history(period="1y")
        spy_p = spy_h['Close'].iloc[-1]
        spy_ma200 = spy_h['Close'].rolling(200).mean().iloc[-1]
        
        base_score = max(0, 100 - (vix * 2.5)) 
        trend_bonus = 25 if spy_p > spy_ma200 else -10
        m_score = int(np.clip(base_score + trend_bonus, 0, 100))
        
        if m_score < 30: mood, status, logic_key = "mood_panic", "CRASH", "macro_logic_panic"
        elif m_score < 55: mood, status, logic_key = "mood_fear", "CAUTION", "macro_logic_fear"
        else: mood, status, logic_key = "mood_greed", "BULL", "macro_logic_greed"
        return {"vix": round(vix, 2), "tnx": round(tnx, 2), "mood": mood, "status": status, "score": m_score, "logic": logic_key}
    except: return None

# --- 4. 终极抗封锁分析引擎 ---
@st.cache_data(ttl=1800)
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        # 第一层：基础价格数据（最稳）
        h = tk.history(period="1y")
        if h.empty: return None
        
        # 第二层：基本信息字段（暴力兜底逻辑）
        inf = tk.info
        if not inf: inf = {}
        
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1] if not m200_s.isna().all() else p
        
        # 🎯 RKLB 修复：处理亏损公司
        pe_curr = inf.get('forwardPE') or inf.get('trailingPE') or 0
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe = (inf.get('returnOnEquity', 0)) * 100
        fcf = (inf.get('freeCashflow', 0)) / 1e9
        inst = (inf.get('heldPercentInstitutions', 0)) * 100
        cash, debt = (inf.get('totalCash', 0))/1e9, (inf.get('totalDebt', 0))/1e9
        
        # 🎯 第三层：深度财报嗅探
        n_date, n_days, p_date, p_act, p_est, p_surp = "N/A", 999, "N/A", "N/A", "N/A", "0.0"
        try:
            # 优先嗅探原始字段
            raw_ts = inf.get('nextEarningsDate')
            if raw_ts:
                dt_obj = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                n_date = dt_obj.strftime('%Y-%m-%d')
                n_days = (dt_obj - datetime.now(timezone.utc)).days
            
            # 如果 N/A 尝试 calendar
            if n_date == "N/A":
                cal = tk.calendar
                if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
                    c_dt = cal.loc['Earnings Date'].iloc[0]
                    n_date, n_days = c_dt.strftime('%Y-%m-%d'), (pd.to_datetime(c_dt).replace(tzinfo=None)-datetime.now()).days
        except: pass

        # 深度 ROE 审计
        prev_roe = "N/A"
        try:
            fin = tk.financials
            if not fin.empty:
                idx = 1 if len(fin.columns) > 1 else 0
                prev_roe = round((fin.loc['Net Income'].iloc[idx] / tk.balance_sheet.loc['Stockholders Equity'].iloc[idx]) * 100, 1)
        except: pass

        # RS 对比
        h_3m = tk.history(period="3mo")
        s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100 if not h_3m.empty else 0
        spy_ret = ((yf.Ticker("^GSPC").history(period="3mo")['Close'].iloc[-1] / yf.Ticker("^GSPC").history(period="3mo")['Close'].iloc[0]) - 1) * 100

        # 符合性判定：放宽门槛，如果 PE 为 0 也允许通过搜索
        ok = (pe_curr < t_pe and peg < t_peg and roe > m_roe)
        
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": round(pe_curr, 2) if pe_curr > 0 else "N/A", "PEG": round(peg, 4), "ROE%": round(roe, 1), "Inst%": f"{inst:.1f}%",
            "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), "Upside": f"{((inf.get('targetMeanPrice', p)/p)-1)*100:+.1f}%",
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": inf.get('targetMeanPrice'),
            "_inst": inst, "_cash": cash, "_debt": debt, "_s_ret": s_ret, "_spy_ret": spy_ret,
            "_n_e": n_date, "_n_d": n_days, "_p_e": p_date, "_p_act": p_act, "_p_est": p_est, "_p_s": p_surp,
            "_prev_roe": prev_roe, "_fcf_m": ((inf.get('freeCashflow', 0) / inf.get('totalRevenue', 1)) * 100),
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 宏观
    macro = get_macro_radar()
    if macro:
        st.markdown(f"### {t.get('macro_title', 'Macro')}")
        m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
        m1.metric(t.get("vix_label", "VIX"), macro['vix'])
        m2.metric(t.get("tnx_label", "10Y"), f"{macro['tnx']}%")
        m3.metric("Issac Macro Score", f"{macro['score']}/100")
        m4.subheader(t.get(macro['mood'], ""))
        with st.expander(t.get('macro_explainer_title', '').format(mood=t.get(macro['mood']))):
            st.write(t.get(macro['logic'], ""))
            st.info(t.get('macro_val_desc', ""))

    # 2. 评分
    score = 0
    score += 25 if s['Price'] > s['MA200'] else 0
    score += 25 if s['ROE%'] > 25 else (15 if s['ROE%'] > 10 else 0)
    score += 20 if (isinstance(s['P/E'], (int, float)) and s['P/E'] < 25) else 0
    score += 15 if s['_s_ret'] > s['_spy_ret'] else 0
    score += 15 if s['Debt%'] < 80 else 0

    st.divider()
    c_l, c_r = st.columns([3, 1])
    c_l.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    c_r.metric(t.get('score_label'), f"{score}/100", delta=f"{score-50}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 3. 趋势图
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t.get('chart_close'), line=dict(color='#00d1ff', width=2)))
        fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t.get('chart_ma200'), line=dict(color='#ffaa00', width=2, dash='dash')))
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig_rs = go.Figure(go.Bar(x=[s['Symbol'], "SPY"], y=[s['_s_ret'], s['_spy_ret']], marker_color=['#00d1ff', '#444444']))
        fig_rs.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_rs, use_container_width=True)

    # 4. 财报雷达
    st.markdown(f"### {t.get('earnings_radar_title')}")
    er1, er2 = st.columns(2)
    # 🎯 强制财报显现逻辑
    n_days_txt = f"(约 {s['_n_d']} 天后)" if s['_n_d'] < 400 else ""
    er1.info(f"📅 **下个财报日**: `{s['_n_e']}` {n_days_txt}")
    er2.markdown(f"📊 **上季财报回顾**")
    er2.write(f"EPS 实测: `{s['_p_act']}` vs 预期: `{s['_p_est']}`")

    # 5. 研报
    st.markdown(f"# {t.get('report_title')}")
    with st.expander(t.get('moat_title'), expanded=True):
        m_txt = t.get('moat_elite') if s['ROE%'] > 35 else (t.get('moat_wide') if s['ROE%'] > 15 else t.get('moat_narrow'))
        st.info(f"**{t.get('industry')}**: `{s['_ind']}` | {m_txt}")
        st.write(s['_sum'][:1200])
    with st.expander(t.get('fin_title'), expanded=True):
        f1, f2, f3 = st.columns(3)
        f1.metric("Cash (Liquidity)", f"${s['_cash']:.1f}B")
        f2.metric("Total Debt", f"${s['_debt']:.1f}B")
        f3.metric("FCF Margin", f"{s['_fcf_m']:.1f}%")
        st.write(f"ROE 稳定性: **{s['ROE%']}%** (当前) vs **{s['_prev_roe']}%** (上年)")
        d_st = t.get('debt_healthy') if s['Debt%'] < 40 else (t.get('debt_mid') if s['Debt%'] < 100 else t.get('debt_high'))
        st.write(f"杠杆审计: 负债比 **{s['Debt%']}%** — {d_st}")
    with st.expander(t.get('risk_title'), expanded=True):
        st.success(f"✅ 机构持仓: **{s['_inst']:.1f}%**")
        if s['Price'] < s['MA200']: st.error(t.get('trend_bear'))
        else: st.success(t.get('trend_bull'))
        st.warning(f"🛡️ **{t.get('stop_loss_label')}**: `${round(s['_m']*0.97, 2)}` | {t.get('stop_loss_note')}")
    
    st.divider()
    v_idx = 1 if s['Price'] < s['MA200']*0.97 or (macro and macro['status'] == "CRASH") else (3 if score > 75 else (2 if score > 50 else 1))
    st.success(f"## {t.get('verdict_title')}：{t.get('verdicts')[v_idx]}")
    st.info(f"💡 {t.get('strategy_label')}：{t.get('strategies')[v_idx]}")

# --- 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker Found, but Yahoo is Throttling. Please wait 10s and try AAPL first.")

if scan_btn:
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
    batch_res, bar = [], st.progress(0)
    for i, ticker in enumerate(tks):
        item = get_analysis(str(ticker).replace('.','-'))
        if item: batch_res.append(item)
        bar.progress((i+1)/len(tks))
    st.session_state.batch_res = batch_res

if 'batch_res' in st.session_state:
    st.divider()
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["Match"]=="✅"]
    if not m_df.empty:
        st.subheader("🏙️ Batch Scan Results")
        sel = st.selectbox("View Report:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[WHITE_LIST] if not m_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
