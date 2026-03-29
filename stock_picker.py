import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 1. 双语字典 (已更新为 Issac 专属评级) ---
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端", "search_label": "🔍 个股透视 (回车搜索)",
        "sidebar_header": "⚙️ 专家级筛选参数", "pe_label": "最高 P/E (建议 < 25)",
        "peg_label": "最高 PEG (建议 < 1.2)", "roe_label": "最低 ROE % (建议 > 15)",
        "fcf_label": "最低 FCF $B (建议 > 0.5)", "scan_range": "📊 批量扫描范围",
        "scan_btn": "开始批量扫描", "match_only": "🔍 只看符合条件的股票",
        "snapshot_title": "📊 核心参数快照", "report_title": "深度投资研报 (Confidential)",
        "moat_title": "🏰 商业模式与护城河深度透视", "fin_title": "🏛️ 盈利质量与财务安全评价",
        "risk_title": "🚩 筹码博弈、趋势与风险预警", "verdict_title": "🏆 Issac 级终极研判",
        "strategy_label": "💡 机构级操盘策略", "industry": "细分行业", "summary": "业务简介",
        "chart_title": "📈 股价与 200 日均线 (MA200) 趋势对比",
        "chart_close": "收盘价", "chart_ma200": "200日均线", "chart_date": "日期",
        "moat_elite": "💎 **护城河评级：顶级 (Elite Moat)**。该公司的 ROE 极高，显示出强大的行业话语权。",
        "moat_wide": "🛡️ **护城河评级：宽阔 (Wide Moat)**。拥有成熟竞争壁垒，盈利质量高。",
        "moat_narrow": "🚧 **护城河评级：较窄 (Narrow Moat)**。面临行业激烈竞争，需警惕利润缩水。",
        "debt_healthy": "🟢 财务极其稳健", "debt_mid": "🟡 杠杆适中", "debt_high": "🔴 财务压力偏高",
        "debt_audit": "· **杠杆审计**: 负债权益比 `{val}%` — {status}",
        "upside_desc": "· **成长空间**: 分析师预期均价为 `${target}`，潜在获利空间 `{upside}`。",
        "inst_high": "机构持仓达 {inst:.1f}%，筹码高度集中。",
        "inst_mid": "机构持仓约 {inst:.1f}%，散户参与度适中。",
        "chip_dist": "✅ **筹码分布**：{msg} (做空率: {sh})",
        "trend_bear": "❌ **趋势雷达**：当前股价处于 MA200 牛熊分界线下方。",
        "trend_bull": "📈 **趋势雷达**：股价获得 200 日均线支撑，处于多头行情。",
        "verdicts": ["观望 (C)","持有 (B)","买入 (A)","强力买入 (A+)"],
        "strategies": ["⚠️ 趋势极弱，建议场外等候。","⚖️ 缺乏动能，仅适合极轻仓观察。","✅ 趋势确立，建议分批分仓布局。","🔥 极品资产，量价齐飞，建议果断持股！"]
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal", "search_label": "🔍 Manual Ticker Search (Enter)",
        "sidebar_header": "⚙️ Expert Filter Settings", "pe_label": "Max P/E (Ref < 25)",
        "peg_label": "Max PEG (Ref < 1.2)", "roe_label": "Min ROE % (Ref > 15)",
        "fcf_label": "Min FCF $B (Ref > 0.5)", "scan_range": "📊 Auto-Scan Range",
        "scan_btn": "Start Batch Scan", "match_only": "🔍 Show Matches Only",
        "snapshot_title": "📊 Core Metrics Snapshot", "report_title": "Deep Institutional Report",
        "moat_title": "🏰 Business Model & Moat Insight", "fin_title": "🏛️ Fundamentals & Financial Safety",
        "risk_title": "🚩 Risk, Sentiment & Trend Radar", "verdict_title": "🏆 Issac Level Verdict",
        "strategy_label": "💡 Strategy", "industry": "Industry", "summary": "Business Summary",
        "chart_title": "📈 Price vs 200D Moving Average (MA200)",
        "chart_close": "Close Price", "chart_ma200": "MA200 Line", "chart_date": "Date",
        "moat_elite": "💎 **Moat Rating: Elite**. Exceptionally high ROE indicates strong market dominance.",
        "moat_wide": "🛡️ **Moat Rating: Wide**. Mature competitive barriers with high earnings quality.",
        "moat_narrow": "🚧 **Moat Rating: Narrow**. Facing stiff competition; monitor profit margins.",
        "debt_healthy": "🟢 Extremely Healthy", "debt_mid": "🟡 Moderate Leverage", "debt_high": "🔴 High Financial Pressure",
        "debt_audit": "· **Debt Audit**: D/E Ratio `{val}%` — {status}",
        "upside_desc": "· **Growth Upside**: Analyst target is `${target}`, potential gain `{upside}`.",
        "inst_high": "Institutions hold {inst:.1f}%, highly concentrated ownership.",
        "inst_mid": "Institutions hold {inst:.1f}%, balanced retail participation.",
        "chip_dist": "✅ **Sentiment**: {msg} (Short Ratio: {sh})",
        "trend_bear": "❌ **Trend Radar**: Price is below MA200 (Bearish).",
        "trend_bull": "📈 **Trend Radar**: Price is supported by MA200 (Bullish).",
        "verdicts": ["Wait (C)", "Hold (B)", "Buy (A)", "STRONG BUY (A+)"],
        "strategies": ["Wait for bottom signals.", "Monitor closely.", "Accumulate on dips.", "High conviction hold."]
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

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
        
        # 🎯 修复 PEG
        peg = inf.get('pegRatio')
        if peg is None or peg == 0: peg = inf.get('trailingPegRatio', 0)
        
        roe = (inf.get('returnOnEquity') or 0) * 100
        fcf = (inf.get('freeCashflow') or 0) / 1e9
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        
        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_s.iloc[-1], 2), "P/E": inf.get('forwardPE', 0), 
            "PEG": round(peg, 4), "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), 
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%", "Upside": f"{upside:+.1f}%", "Match": "✅" if ok else "❌",
            "_p": p, "_m": m200_s.iloc[-1], "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside, "_inst": inst,
            "_sum": inf.get('longBusinessSummary', "N/A"), "_ind": inf.get('industry', "N/A")
        }
    except: return None

def render_report(s):
    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
    fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_title=t['chart_date'], yaxis_title=t['chart_close'])
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"📜 {s['Symbol']} - {t['report_title']}", expanded=True):
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**{t['industry']}**: `{s['_ind']}`")
        st.write(f"**{t['summary']}**: {s['_sum'][:800]}...")
        st.info(t['moat_elite'] if s['ROE%'] > 35 else (t['moat_wide'] if s['ROE%'] > 18 else t['moat_narrow']))

        st.markdown("---")
        st.markdown(f"### {t['fin_title']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG", s['PEG'], delta="Value" if s['PEG'] < 0.7 else None)
        c2.metric("Target Price", f"${round(s['_target'], 2)}" if s['_target'] else "N/A", delta=s['Upside'])
        c3.metric("FCF", f"${s['FCF$B']}B")
        
        d_status = t['debt_healthy'] if s['Debt%'] < 40 else (t['debt_mid'] if s['Debt%'] < 100 else t['debt_high'])
        st.write(t['debt_audit'].format(val=s['Debt%'], status=d_status))
        st.write(t['upside_desc'].format(target=s['_target'], upside=s['Upside']))

        st.markdown("---")
        st.markdown(f"### {t['risk_title']}")
        r1, r2 = st.columns(2)
        inst_msg = t['inst_high'].format(inst=s['_inst']) if s['_inst'] > 75 else t['inst_mid'].format(inst=s['_inst'])
        r1.success(t['chip_dist'].format(msg=inst_msg, sh=s['Short%']))
        if s['_p'] < s['_m']: r2.error(t['trend_bear'])
        else: r2.success(t['trend_bull'])

        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0) + (1 if s['_up_val'] > 15 else 0)
        v_idx = min(score, 3)
        st.success(f"### {t['verdict_title']}：{t['verdicts'][v_idx]}")
        st.info(f"💡 {t['strategy_label']}：{t['strategies'][v_idx]}")

# --- 4. 逻辑流 ---
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
