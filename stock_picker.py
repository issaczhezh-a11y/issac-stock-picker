import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone
from lang_config import LANG 

# --- 1. 设置 ---
st.set_page_config(page_title="Issac Terminal Pro", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG.get(lang_choice, LANG["CN"])
st.title(t.get("title", "Issac Terminal"))

WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "Inst%", "P/E", "Match"]

# --- 2. 侧边栏 (Issac 定制推荐参数) ---
st.sidebar.header(t.get("sidebar_header", "Settings"))
search_ticker = st.sidebar.text_input(t.get("search_label", "Ticker"), "").upper().strip()
st.sidebar.divider()
# 🎯 按照 Issac 要求更新推荐值：PE 20, PEG 1, ROE 15, FCF 1B
t_pe = st.sidebar.number_input(t.get("pe_label"), value=20.0, help=t.get("pe_help"))
t_peg = st.sidebar.number_input(t.get("peg_label"), value=1.0, help=t.get("peg_help"))
m_roe = st.sidebar.number_input(t.get("roe_label"), value=15.0, help=t.get("roe_help"))
m_fcf = st.sidebar.number_input(t.get("fcf_label"), value=1.0, help=t.get("fcf_help"))
st.sidebar.divider()
idx_mode = st.sidebar.selectbox("Scan Range", ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button("Start Scan")

# --- 3. 宏观风控引擎 ---
@st.cache_data(ttl=3600)
def get_macro():
    try:
        v_h = yf.Ticker("^VIX").history(period="5d")
        vix = v_h['Close'].iloc[-1] if not v_h.empty else 20.0
        t_h = yf.Ticker("^TNX").history(period="5d")
        tnx = t_h['Close'].iloc[-1] if not t_h.empty else 4.0
        spy_h = yf.Ticker("SPY").history(period="1y")
        spy_p, spy_m = spy_h['Close'].iloc[-1], spy_h['Close'].rolling(200).mean().iloc[-1]
        score = int(np.clip(100 - (vix * 2.5) + (25 if spy_p > spy_m else -10), 0, 100))
        mood = "mood_panic" if score < 35 else ("mood_fear" if score < 60 else "mood_greed")
        logic = "macro_logic_panic" if score < 35 else ("macro_logic_fear" if score < 60 else "macro_logic_greed")
        return {"vix": round(vix, 2), "tnx": round(tnx, 2), "mood": mood, "score": score, "logic": logic, "panic": score < 35}
    except: return None

# --- 4. 深度分析引擎 ---
@st.cache_data(ttl=1800)
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if h.empty: return None
        
        try: inf = tk.info
        except: inf = {}
        
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1] if not m200_s.isna().all() else p
        
        # 指标提取
        pe = inf.get('forwardPE') or inf.get('trailingPE') or 0
        peg = inf.get('pegRatio') or 0
        roe = (inf.get('returnOnEquity') or 0) * 100
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        cash, debt = (inf.get('totalCash', 0))/1e9, (inf.get('totalDebt', 0))/1e9
        rev = inf.get('totalRevenue', 1)
        fcf = inf.get('freeCashflow', 0)
        fcf_margin = (fcf / rev) * 100 if rev > 1 else 0
        
        # 财报日期
        n_date, n_days, p_date, p_act, p_est, p_surp = "N/A", 999, "N/A", "N/A", "N/A", "0.0"
        try:
            raw_ts = inf.get('nextEarningsDate')
            if raw_ts:
                dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                n_date, n_days = dt.strftime('%Y-%m-%d'), (dt - datetime.now(timezone.utc)).days
            e_hist = tk.get_earnings_dates(limit=4)
            if e_hist is not None and not e_hist.empty:
                e_hist.index = pd.to_datetime(e_hist.index).tz_convert('UTC')
                pst = e_hist[e_hist.index <= datetime.now(timezone.utc)].sort_index(ascending=False)
                if not pst.empty:
                    p_date, p_act, p_est = pst.index[0].strftime('%Y-%m-%d'), pst['Reported EPS'].iloc[0], pst['EPS Estimate'].iloc[0]
                    if pd.notnull(p_act) and pd.notnull(p_est) and p_est != 0: p_surp = round(((p_act/p_est)-1)*100, 1)
        except: pass

        # ROE 稳定性
        prev_roe = "N/A"
        try:
            fin = tk.financials
            if not fin.empty:
                idx = 1 if len(fin.columns) > 1 else 0
                prev_roe = round((fin.loc['Net Income'].iloc[idx] / tk.balance_sheet.loc['Stockholders Equity'].iloc[idx]) * 100, 1)
        except: pass

        # RS 强度
        h_3m = tk.history(period="3mo")
        s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100 if not h_3m.empty else 0
        spy_ret = 5.5

        # 判定：遵循 Issac 设置的侧边栏动态参数
        ok = (0 < pe < t_pe and peg < t_peg and roe > m_roe and (fcf/1e9) > m_fcf)
        
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": round(pe, 2) if pe > 0 else "N/A", "ROE%": round(roe, 1), "Inst%": f"{inst:.1f}%", "PEG": round(peg, 2),
            "FCF$B": round(fcf/1e9, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), "FCF_M": fcf_margin,
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_inst": inst, "_cash": cash, "_debt": debt,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_n_e": n_date, "_n_d": n_days, "_p_e": p_date,
            "_p_act": p_act, "_p_est": p_est, "_p_s": p_surp, "_prev_roe": prev_roe,
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "No Summary.")
        }
    except: return None

def render_report(s):
    # 1. 宏观
    macro = get_macro()
    if macro:
        st.markdown(f"### {t.get('macro_title')}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t.get("vix_label"), macro['vix'], help=t.get("vix_help"))
        m2.metric(t.get("tnx_label"), f"{macro['tnx']}%", help=t.get("tnx_help"))
        m3.metric("Issac Macro Score", f"{macro['score']}/100")
        m4.subheader(t.get(macro['mood']))
        with st.expander(t.get('macro_explainer_title').format(mood=t.get(macro['mood']))):
            st.write(t.get(macro['logic']))
            st.info(t.get('macro_val_desc'))
            st.write(t.get('macro_hist_desc'))

    st.divider()
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    # 评分算法
    score = int(np.clip((30 if s['Price'] > s['MA200'] else 0) + (30 if s['ROE%'] > 15 else 10) + (20 if s['_s_ret'] > s['_spy_ret'] else 0) + (20 if s['Debt%'] < 80 else 0), 0, 100))
    c2.metric(t.get('score_label'), f"{score}/100", delta=f"{score-50}", help=t.get("score_help"))
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 趋势图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t.get('chart_close'), line=dict(color='#00d1ff')))
    fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t.get('chart_ma200'), line=dict(color='#ffaa00', dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 4. 财报雷达
    st.markdown(f"### {t.get('earnings_radar_title')}")
    er1, er2 = st.columns(2)
    n_days_txt = f"(约 {s['_n_d']} 天后)" if s['_n_d'] < 400 else ""
    er1.info(f"📅 **预计下个财报日**: `{s['_n_e']}` {n_days_txt}")
    with er2:
        sur_c = "green" if (isinstance(s['_p_s'], (int, float)) and s['_p_s'] > 0) else "red"
        st.markdown(f"**{t.get('prev_earn_label').format(date=s['_p_e'])}**")
        st.write(f"EPS 实测: `{s['_p_act']}` vs 预期: `{s['_p_est']}` ➔ 惊喜度: :{sur_c}[{s['_p_s']}%]")

    # 5. 详细研报
    st.markdown(f"# {t.get('report_title')}")
    with st.expander(t.get('moat_title'), expanded=True):
        moat_txt = t.get('moat_elite') if s['ROE%'] > 35 else (t.get('moat_wide') if s['ROE%'] > 15 else t.get('moat_narrow'))
        st.info(f"**{t.get('industry')}**: `{s['_ind']}` | {moat_txt}")
        st.write(s['_sum'][:1200] + "...")

    with st.expander(t.get('fin_title'), expanded=True):
        f1, f2, f3 = st.columns(3)
        f1.metric(t.get("cash_label"), f"${s['_cash']:.1f}B", help=t.get("cash_help"))
        f2.metric(t.get("debt_label"), f"${s['_debt']:.1f}B", help=t.get("debt_help"))
        f3.metric(t.get("fcf_m_label"), f"{s['FCF_M']:.1f}%", help=t.get("fcf_m_help"))
        st.markdown("---")
        st.write(t.get('consistency_label').format(curr=s['ROE%'], prev=s['_prev_roe']))
        d_st = t.get('debt_healthy') if s['Debt%'] < 40 else (t.get('debt_mid') if s['Debt%'] < 100 else t.get('debt_high'))
        st.write(t.get('debt_audit').format(val=s['Debt%'], status=d_st))

    with st.expander(t.get('risk_title'), expanded=True):
        st.success(t.get('inst_label').format(inst=s['_inst']))
        if s['Price'] < s['MA200']: st.error(t.get('trend_bear'))
        else: st.success(t.get('trend_bull'))
        st.warning(f"🛡️ **{t.get('stop_loss_label')}**: `${round(s['_m']*0.97, 2)}` | {t.get('stop_loss_note')}")
    
    st.divider()
    v_idx = 1 if s['Price'] < s['MA200']*0.97 or (macro and macro['panic']) else (3 if score > 75 else (2 if score > 50 else 1))
    st.success(f"## {t.get('verdict_title')}：{t.get('verdicts')[v_idx]}")
    st.info(f"💡 {t.get('strategy_label')}：{t.get('strategies')[v_idx]}")

# --- 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker Found, but Yahoo is Throttling. Please try AAPL or retry in 10s.")

if scan_btn:
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
    batch_res, bar = [], st.progress(0)
    for i, ticker in enumerate(tks[:50]): # 限制扫描防封
        item = get_analysis(str(ticker).replace('.','-'))
        if item: batch_res.append(item)
        bar.progress((i+1)/50)
    st.session_state.batch_res = batch_res

if 'batch_res' in st.session_state:
    st.divider()
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["Match"]=="✅"]
    if not m_df.empty:
        st.subheader("🏙️ Batch Scan Results")
        sel = st.selectbox("Select Target Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[WHITE_LIST] if not m_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
