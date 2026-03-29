import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from lang_config import LANG 

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

WHITE_LIST = ["Symbol", "Price", "Match", "P/E", "PEG", "ROE%", "Short%", "Upside"]

# --- 2. 侧边栏 (修复 scan_range 缺失问题) ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
t_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
m_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
m_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)

st.sidebar.divider()
# 🎯 重新归位的批量选择与按钮
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
        
        # 基础数据抓取
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        
        # 🎯 相对强度 (RS) 计算
        spy_tk = yf.Ticker("^GSPC")
        h_3m = tk.history(period="3mo")
        h_spy_3m = spy_tk.history(period="3mo")
        rs_diff, rs_is_leader = 0, True
        if len(h_3m) >= 60 and len(h_spy_3m) >= 60:
            s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
            spy_ret = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
            rs_diff = s_ret - spy_ret
            rs_is_leader = rs_diff > 0

        # 🎯 财报日期
        cal = tk.calendar
        days_to_earnings, earn_date = 999, "N/A"
        if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
            try:
                ed = cal.loc['Earnings Date'].iloc[0]
                earn_date = ed.strftime('%Y-%m-%d')
                days_to_earnings = (ed - pd.Timestamp.now()).days
            except: pass

        # 🎯 历史 ROE 对比
        prev_roe = "N/A"
        try:
            prev_ni = tk.yearly_financials.loc['Net Income'].iloc[1]
            prev_eq = tk.yearly_balance_sheet.loc['Stockholders Equity'].iloc[1]
            if prev_eq > 0: prev_roe = round((prev_ni / prev_eq) * 100, 1)
        except: pass

        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "Match": "✅" if ok else "❌", "P/E": inf.get('forwardPE', 0), 
            "PEG": round(peg, 4), "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), 
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%", "Upside": f"{upside:+.1f}%", 
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside, 
            "_inst": (inf.get('heldPercentInstitutions') or 0) * 100, "_sl": m200_val * 0.97,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_rs_diff": rs_diff, "_rs_is_l": rs_is_leader,
            "_e_days": days_to_earnings, "_e_date": earn_date, "_prev_roe": prev_roe,
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 财报警示
    if 0 <= s['_e_days'] <= 7:
        st.error(t['earnings_label'].format(days=s['_e_days'], date=s['_e_date']))
        st.divider()

    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 2. 趋势图
    with st.expander(t['chart_title'], expanded=True):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
        fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
        fig.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # 3. RS 对比柱状图
    st.markdown(f"### {t['rs_title']}")
    fig_rs = go.Figure(go.Bar(x=[s['Symbol'], t['rs_label_spy']], y=[s['_s_ret'], s['_spy_ret']], marker_color=['#00d1ff', '#cccccc']))
    fig_rs.update_layout(template="plotly_dark", height=250, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_rs, use_container_width=True)
    if s['_rs_is_l']: st.success(t['rs_desc_leader'].format(diff=s['_rs_diff']))
    else: st.error(t['rs_desc_laggard'].format(diff=abs(s['_rs_diff'])))

    # 4. 深度报告
    with st.expander(t['report_title'], expanded=True):
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**Industry**: `{s['_ind']}` | **Business**: {s['_sum'][:800]}...")
        st.info(t['moat_elite'] if s['ROE%'] > 35 else (t['moat_wide'] if s['ROE%'] > 18 else t['moat_narrow']))
        
        st.markdown(f"#### {t['fin_title']}")
        c1, c2 = st.columns(2)
        c1.metric("PEG Ratio", s['PEG'])
        c2.metric("Target Price", f"${round(s['_target'], 2)}" if s['_target'] else "N/A", delta=s['Upside'])
        st.write(t['consistency_label'].format(curr=s['ROE%'], prev=s['_prev_roe']))
        
        st.markdown("---")
        st.markdown(f"#### {t['risk_title']}")
        r1, r2 = st.columns(2)
        inst_held = s['_inst']
        r1.caption(f"Sentiment: Inst Held {inst_held:.1f}% | Short: {s['Short%']}")
        if s['Price'] < s['MA200']: r2.error(t['trend_bear'])
        else: r2.success(t['trend_bull'])
        st.warning(f"🛡️ **{t['stop_loss_label']}**: `${round(s['_sl'], 2)}`")

        st.divider()
        base_score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_up_val'] > 15 else 0)
        if s['Price'] < s['_sl']:
            v_idx = 1 # B (观望)
            st.error(f"### {t['verdict_title']}：{t['verdicts'][v_idx]} (Trend Broken)")
        else:
            v_idx = min(base_score + (1 if s['Price'] > s['MA200'] else 0), 3)
            st.success(f"### {t['verdict_title']}：{t['verdicts'][v_idx]}")
            st.info(f"💡 {t['strategy_label']}：{t['strategies'][v_idx]}")

# --- 5. 执行 ---
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
    m_df = df[df["Match"]=="✅"][WHITE_LIST]
    if not m_df.empty:
        sel = st.selectbox("Select Target Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df, use_container_width=True, hide_index=True)
