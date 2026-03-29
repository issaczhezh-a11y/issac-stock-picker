import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone
from lang_config import LANG 

# --- 1. 设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "Inst%", "P/E", "PEG", "Match"]

# --- 2. 侧边栏 ---
st.sidebar.header(t.get("sidebar_header"))
search_ticker = st.sidebar.text_input(t.get("search_label"), "").upper().strip()
st.sidebar.divider()
t_pe, t_peg = st.sidebar.number_input(t.get("pe_label"), value=25.0), st.sidebar.number_input(t.get("peg_label"), value=1.2)
m_roe, m_fcf = st.sidebar.number_input(t.get("roe_label"), value=15.0), st.sidebar.number_input(t.get("fcf_label"), value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t.get("scan_range"), ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t.get("scan_btn"))

# --- 3. 分析引擎 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if h.empty or len(h) < 200: return None
        inf = tk.info
        p = h['Close'].iloc[-1]
        m200_val = h['Close'].rolling(200).mean().iloc[-1]
        
        # A. 基础资产
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        cash, debt = (inf.get('totalCash') or 0)/1e9, (inf.get('totalDebt') or 0)/1e9
        
        # B. 估值水位
        pe_curr = inf.get('forwardPE') or inf.get('trailingPE', 0)
        pe_pct = "N/A"
        try:
            hist_pe = h['Close'] / (inf.get('trailingEps', 1))
            pe_pct = round((hist_pe < pe_curr).mean() * 100, 1)
        except: pass

        # C. ROE 审计
        prev_roe = "N/A"
        try:
            y_fin = tk.financials
            if not y_fin.empty:
                idx = 1 if len(y_fin.columns) > 1 else 0
                prev_roe = round((y_fin.loc['Net Income'].iloc[idx] / tk.balance_sheet.loc['Stockholders Equity'].iloc[idx]) * 100, 1)
        except: pass

        # D. 🎯 暴力抓取财报逻辑 (修复 N/A)
        n_date, n_days, p_date, p_act, p_est, p_surp = "N/A", 999, "N/A", "N/A", "N/A", "0.0"
        try:
            # 路径 1: 从 tk.calendar 提取 (最稳)
            cal = tk.calendar
            if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
                c_date = cal.loc['Earnings Date'].iloc[0]
                n_date = c_date.strftime('%Y-%m-%d')
                n_days = (pd.to_datetime(c_date).replace(tzinfo=None) - datetime.now()).days
            
            # 路径 2: 抓取历史胜率
            e_dates = tk.get_earnings_dates(limit=8)
            if e_dates is not None and not e_dates.empty:
                e_dates.index = pd.to_datetime(e_dates.index).tz_convert('UTC')
                pst = e_dates[e_dates.index <= datetime.now(timezone.utc)].sort_index(ascending=False)
                if not pst.empty:
                    p_date = pst.index[0].strftime('%Y-%m-%d')
                    p_act, p_est = pst['Reported EPS'].iloc[0], pst['EPS Estimate'].iloc[0]
                    if pd.notnull(p_act) and pd.notnull(p_est) and p_est != 0:
                        p_surp = round(((p_act / p_est) - 1) * 100, 1)
        except: pass

        # RS
        s_ret, spy_ret = 0, 0
        try:
            h_3m = tk.history(period="3mo")
            h_spy_3m = yf.Ticker("^GSPC").history(period="3mo")
            s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
            spy_ret = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
        except: pass

        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": pe_curr, "PEG": round(peg, 4), "ROE%": round(roe, 1), "Inst%": f"{inst:.1f}%",
            "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), "Upside": f"{((inf.get('targetMeanPrice', p)/p)-1)*100:+.1f}%",
            "_p": p, "_m": m200_val, "_h": h, "_m_s": h['Close'].rolling(200).mean(), "_target": inf.get('targetMeanPrice'),
            "_inst": inst, "_cash": cash, "_debt": debt, "_pe_pct": pe_pct,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_n_e": n_date, "_n_d": n_days,
            "_p_e": p_date, "_p_act": p_act, "_p_est": p_est, "_p_s": p_surp,
            "_prev_roe": prev_roe, "_fcf_m": ((inf.get('freeCashflow', 0) / inf.get('totalRevenue', 1)) * 100),
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

def render_report(s):
    st.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
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
    
    st.markdown(f"### {t.get('earnings_radar_title')}")
    er1, er2 = st.columns(2)
    er1.info(t.get('next_earn_label', 'Next: {date}').format(date=s['_n_e'], days=s['_n_d']))
    sur_c = "green" if (isinstance(s['_p_s'], (int, float)) and s['_p_s'] > 0) else "red"
    er2.markdown(f"**{t.get('prev_earn_label', 'Last: {date}').format(date=s['_p_e'])}**")
    er2.write(t.get('eps_vs_est', 'Act: {act}').format(act=s['_p_act'], est=s['_p_est'], surp=f":{sur_c}[{s['_p_s']}]"))

    st.markdown(f"# {t.get('report_title')}")
    with st.expander(t.get('moat_title'), expanded=True):
        moat_txt = t.get('moat_elite') if s['ROE%'] > 35 else (t.get('moat_wide') if s['ROE%'] > 18 else t.get('moat_narrow'))
        st.info(f"**{t.get('industry')}**: `{s['_ind']}` | {moat_txt}")
        st.write(s['_sum'][:1200] + "...")
    with st.expander(t.get('fin_title'), expanded=True):
        f1, f2, f3 = st.columns(3)
        f1.metric("Cash", f"${s['_cash']:.1f}B")
        f2.metric("Total Debt", f"${s['_debt']:.1f}B")
        f3.metric("FCF Margin", f"{s['_fcf_m']:.1f}%")
        st.write(t.get('cash_label').format(val=s['_cash']))
        st.write(t.get('debt_val_label').format(val=s['_debt']))
        st.write(t.get('consistency_label', 'ROE: {curr}%').format(curr=s['ROE%'], prev=s['_prev_roe']))
        d_st = t.get('debt_healthy') if s['Debt%'] < 40 else (t.get('debt_mid') if s['Debt%'] < 100 else t.get('debt_high'))
        st.write(t.get('debt_audit').format(val=s['Debt%'], status=d_st))
        pe_stat = "Underpriced" if (isinstance(s['_pe_pct'], (int, float)) and s['_pe_pct'] < 25) else "Normal"
        st.write(t.get('pe_percentile_label').format(val=s['_pe_pct'], status=pe_stat))
    with st.expander(t.get('risk_title'), expanded=True):
        r1, r2 = st.columns(2)
        r1.success(t.get('inst_label').format(inst=s['_inst'], msg="Confidence High" if s['_inst']>70 else "Balanced"))
        if s['Price'] < s['MA200']: r2.error(t.get('trend_bear'))
        else: r2.success(t.get('trend_bull'))
        st.warning(f"🛡️ **{t.get('stop_loss_label')}**: `${round(s['_m']*0.97, 2)}` | {t.get('stop_loss_note')}")
    st.divider()
    score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['Price'] > s['MA200'] else 0)
    v_idx = min(score, 3)
    st.success(f"## {t.get('verdict_title')}：{t.get('verdicts')[v_idx]}")
    st.info(f"💡 {t.get('strategy_label')}：{t.get('strategies')[v_idx]}")

# --- 4. 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker not found. Data provider delay.")

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
        sel = st.selectbox("Select Target:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[WHITE_LIST] if not m_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
