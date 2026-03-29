import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
from lang_config import LANG 

# --- 1. 设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "P/E", "PEG", "FCF$B", "Debt%", "Upside", "Match"]

# --- 2. 侧边栏 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
t_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
m_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
m_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t["scan_range"], ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t["scan_btn"])

# --- 3. 分析引擎 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1]
        
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        rev = inf.get('totalRevenue', 1)
        fcf_m = (inf.get('freeCashflow', 0) / rev) * 100
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        
        # 🎯 3.1 深度 ROE 审计逻辑
        prev_roe = "N/A"
        try:
            yearly_fin = tk.financials
            yearly_bs = tk.balance_sheet
            # 找到最近完整财年的数据 (通常是第0列或第1列)
            if not yearly_fin.empty and not yearly_bs.empty:
                # 为了避开 TTM，我们取第1个索引（即上一个完整年度）
                net_income = yearly_fin.loc['Net Income'].iloc[0]
                equity = yearly_bs.loc['Stockholders Equity'].iloc[0]
                # 如果第0列看起来像当年的，我们尝试取第1列作为上一年对比
                if len(yearly_fin.columns) > 1:
                    net_income = yearly_fin.loc['Net Income'].iloc[1]
                    equity = yearly_bs.loc['Stockholders Equity'].iloc[1]
                prev_roe = round((net_income / equity) * 100, 1) if equity > 0 else "N/A"
        except: pass

        # 🎯 3.2 财报胜率雷达逻辑
        next_e_date, next_e_days = "N/A", 999
        prev_e_date, prev_eps_est, prev_eps_act, prev_surp = "N/A", "N/A", "N/A", "N/A"
        
        try:
            e_dates = tk.earnings_dates
            if not e_dates.empty:
                # 下个财报
                future = e_dates[e_dates.index > datetime.now(timezone.utc)]
                if not future.empty:
                    next_e_obj = future.index[0]
                    next_e_date = next_e_obj.strftime('%Y-%m-%d')
                    next_e_days = (next_e_obj - datetime.now(timezone.utc)).days
                
                # 上个财报
                past = e_dates[e_dates.index < datetime.now(timezone.utc)]
                if not past.empty:
                    prev_e_obj = past.index[0]
                    prev_e_date = prev_e_obj.strftime('%Y-%m-%d')
                    prev_eps_est = past['EPS Estimate'].iloc[0]
                    prev_eps_act = past['Reported EPS'].iloc[0]
                    if pd.notnull(prev_eps_act) and pd.notnull(prev_eps_est) and prev_eps_est != 0:
                        prev_surp = round(((prev_eps_act / prev_eps_est) - 1) * 100, 1)
        except: pass

        # RS
        spy_tk = yf.Ticker("^GSPC")
        h_3m, h_spy_3m = tk.history(period="3mo"), spy_tk.history(period="3mo")
        s_ret, spy_ret, rs_diff, rs_is_l = 0, 0, 0, True
        if len(h_3m) >= 60 and len(h_spy_3m) >= 60:
            s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
            spy_ret = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
            rs_diff, rs_is_l = s_ret - spy_ret, s_ret > spy_ret

        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": inf.get('forwardPE', 0), "PEG": round(peg, 4), "ROE%": round(roe, 1), 
            "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), "Upside": f"{upside:+.1f}%",
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%",
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside,
            "_inst": (inf.get('heldPercentInstitutions') or 0) * 100, "_sl": m200_val * 0.97,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_rs_diff": rs_diff, "_rs_is_l": rs_is_l,
            "_next_e": next_e_date, "_next_days": next_e_days,
            "_prev_e": prev_e_date, "_p_est": prev_eps_est, "_p_act": prev_eps_act, "_p_surp": prev_surp,
            "_prev_roe": prev_roe, "_fcf_m": fcf_m,
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 顶部快照
    st.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 2. 图表区
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
    
    # 3. 🎯 核心增强：财报胜率雷达
    st.markdown(f"### {t.get('earnings_radar_title')}")
    er1, er2 = st.columns(2)
    with er1:
        st.info(t.get('next_earn_label').format(date=s['_next_e'], days=s['_next_days']))
    with er2:
        surp_color = "green" if (isinstance(s['_p_surp'], (int, float)) and s['_p_surp'] > 0) else "red"
        st.markdown(f"**{t.get('prev_earn_label').format(date=s['_prev_e'])}**")
        st.write(t.get('eps_vs_est').format(act=s['_p_act'], est=s['_p_est'], surp=f":{surp_color}[{s['_p_surp']}]"))

    # 4. 智库研报主体
    st.markdown(f"# {t.get('report_title')}")
    with st.expander(t.get('moat_title'), expanded=True):
        m_txt = t.get('moat_elite') if s['ROE%'] > 35 else (t.get('moat_wide') if s['ROE%'] > 18 else t.get('moat_narrow'))
        st.info(f"**{t.get('industry')}**: `{s['_ind']}` | {m_txt}")
        st.write(s['_sum'][:1000] + "...")

    with st.expander(t.get('fin_title'), expanded=True):
        f1, f2, f3 = st.columns(3)
        f1.metric("ROE (Profitability)", f"{s['ROE%']}%", delta=f"Prev Year: {s['_prev_roe']}%" if s['_prev_roe'] != "N/A" else None)
        f2.metric("PEG (Value)", s['PEG'])
        f3.metric("FCF Margin", f"{s['_fcf_m']:.1f}%")
        
        st.write(t.get('consistency_label').format(curr=s['ROE%'], prev=s['_prev_roe']))
        d_stat = t.get('debt_healthy') if s['Debt%'] < 40 else (t.get('debt_mid') if s['Debt%'] < 100 else t.get('debt_high'))
        st.write(t.get('debt_audit').format(val=s['Debt%'], status=d_stat))
        st.write(t.get('upside_desc').format(target=s['_target'] if s['_target'] else 'N/A', upside=s['Upside']))

    with st.expander(t.get('risk_title'), expanded=True):
        r1, r2 = st.columns(2)
        r1.success(f"✅ **Sentiments**: Inst Held {s['_inst']:.1f}% | Short: {s['Short%']}")
        if s['Price'] < s['MA200']: r2.error(t.get('trend_bear'))
        else: r2.success(t.get('trend_bull'))
        st.warning(f"🛡️ **{t.get('stop_loss_label')}**: `${round(s['_sl'], 2)}` | {t.get('stop_loss_note')}")

    # 终极判研
    st.divider()
    up_v = float(s['Upside'].replace('%','')) if '%' in s['Upside'] else 0
    score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if up_v > 15 else 0)
    if s['Price'] < s['_sl']:
        st.error(f"## {t.get('verdict_title')}：{t.get('verdicts')[1]} (Momentum Broken)")
    else:
        v_idx = min(score + (1 if s['Price'] > s['MA200'] else 0), 3)
        st.success(f"## {t.get('verdict_title')}：{t.get('verdicts')[v_idx]}")
        st.info(f"💡 {t.get('strategy_label')}：{t.get('strategies')[v_idx]}")

# --- 4. 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker not found.")

if scan_btn:
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
    batch_res = []
    bar = st.progress(0)
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
        sel = st.selectbox("Select Target Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[WHITE_LIST] if not m_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
