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

# 自动同步展示列
WHITE_LIST = ["Symbol", "Price", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "Debt%", "Short%", "Upside", "Match"]

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
        
        # 数据抓取
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        
        # 三大增强指标
        rev_growth = (inf.get('revenueGrowth') or 0) * 100
        m_cap = inf.get('marketCap', 1)
        fcf_yield = (inf.get('freeCashflow', 0) / m_cap) * 100
        stop_loss = m200_val * 0.97 # 缓冲 3%
        
        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "P/E": inf.get('forwardPE', 0), 
            "PEG": round(peg, 4), "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), 
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%", "Upside": f"{upside:+.1f}%", "Match": "✅" if ok else "❌",
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside, "_inst": inst,
            "_rev_g": rev_growth, "_fcf_y": fcf_yield, "_sl": stop_loss,
            "_sum": inf.get('longBusinessSummary', "N/A"), "_ind": inf.get('industry', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 参数展示
    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    # 2. 趋势图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
    fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_title=t['chart_date'], yaxis_title=t['chart_close'])
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"📜 {s['Symbol']} - {t['report_title']}", expanded=True):
        # 护城河
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**{t['industry']}**: `{s['_ind']}`")
        st.write(f"**{t['summary']}**: {s['_sum'][:800]}...")
        st.info(t['moat_elite'] if s['ROE%'] > 35 else (t['moat_wide'] if s['ROE%'] > 18 else t['moat_narrow']))

        st.markdown("---")
        # 成长动能
        st.markdown(f"### {t['growth_title']}")
        g1, g2, g3 = st.columns(3)
        g1.metric(t['cagr_label'], f"{s['_rev_g']:.1f}%", delta="High Growth" if s['_rev_g'] > 15 else None)
        g2.metric(t['fcf_yield_label'], f"{s['_fcf_y']:.2f}%", delta="Cash Cow" if s['_fcf_y'] > 5 else None)
        g3.metric("FCF", f"${s['FCF$B']}B")

        # 财务评价
        st.markdown(f"### {t['fin_title']}")
        c1, c2 = st.columns(2)
        c1.metric("PEG", s['PEG'])
        c2.metric("Target Price", f"${round(s['_target'], 2)}" if s['_target'] else "N/A", delta=s['Upside'])
        d_status = t['debt_healthy'] if s['Debt%'] < 40 else (t['debt_mid'] if s['Debt%'] < 100 else t['debt_high'])
        st.write(t['debt_audit'].format(val=s['Debt%'], status=d_status))
        st.write(t['upside_desc'].format(target=s['_target'], upside=s['Upside']))

        st.markdown("---")
        # 风险与风控
        st.markdown(f"### {t['risk_title']}")
        r1, r2 = st.columns(2)
        inst_msg = t['inst_high'].format(inst=s['_inst']) if s['_inst'] > 75 else t['inst_mid'].format(inst=s['_inst'])
        r1.success(t['chip_dist'].format(msg=inst_msg, sh=s['Short%']))
        if s['Price'] < s['MA200']: r2.error(t['trend_bear'])
        else: r2.success(t['trend_bull'])

        st.warning(f"🛡️ **{t['stop_loss_label']}**: `${round(s['_sl'], 2)}`")
        st.caption(t['stop_loss_note'])

        st.divider()
        # 🎯 核心逻辑优化：加入技术面一票否决权
        base_score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_up_val'] > 15 else 0)
        
        # 如果价格低于止损位（均线下方缓冲位），强制锁定评级
        if s['Price'] < s['_sl']:
            final_v = 1 # 观望/持有
            st.error(f"### {t['verdict_title']}：{t['verdicts'][final_v]} (Momentum Broken)")
            st.error("🚨 **Issac Risk Warning**: 公司基本面虽强，但股价已跌破关键防御位（MA200）。目前处于空头趋势，A/A+ 评级已暂时锁定。建议等待重回均线上方。")
        else:
            trend_score = 1 if s['Price'] > s['MA200'] else 0
            final_v = min(base_score + trend_score, 3)
            st.success(f"### {t['verdict_title']}：{t['verdicts'][final_v]}")
            st.info(f"💡 {t['strategy_label']}：{t['strategies'][final_v]}")

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
    m_df = df[df["Match"].str.contains("✅")][WHITE_LIST]
    if not m_df.empty:
        st.subheader("🏙️ Batch Scan Results")
        sel = st.selectbox("Select Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df if st.checkbox(t["match_only"], value=True) else df[WHITE_LIST], use_container_width=True, hide_index=True)
