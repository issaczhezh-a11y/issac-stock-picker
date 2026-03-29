import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 1. 真·智库级多语言字典 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端", "search_label": "🔍 个股透视 (回车搜索)",
        "sidebar_header": "⚙️ 专家级筛选参数", "pe_label": "最高 P/E (建议 < 25)",
        "peg_label": "最高 PEG (建议 < 1.2)", "roe_label": "最低 ROE % (建议 > 15)",
        "fcf_label": "最低 FCF $B (建议 > 0.5)", "scan_range": "📊 批量扫描范围",
        "scan_btn": "开始批量扫描", "match_only": "🔍 只看符合条件的股票",
        "snapshot_title": "📊 核心参数快照", "report_title": "深度投资研报 (Confidential)",
        "moat_title": "🏰 商业模式与护城河深度透视", "fin_title": "🏛️ 盈利质量与财务安全评价",
        "risk_title": "🚩 筹码博弈、趋势与风险预警", "verdict_title": "🏆 JPMorgan 级终极研判",
        "strategy_label": "💡 机构级操盘建议", "industry": "细分行业", "summary": "核心业务概选",
        "chart_title": "📈 股价与 200 日均线 (MA200) 趋势对比",
        "chart_close": "收盘价", "chart_ma200": "200日均线", "chart_date": "日期",
        "strategies": ["⚠️ 趋势极弱且量价背离，建议场外等候。","⚖️ 缺乏动能，仅适合极轻仓观察。","✅ 趋势确立，建议分批分仓布局。","🔥 极品资产，量价齐飞，建议果断持股或加仓！"]
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal", "search_label": "🔍 Manual Ticker Search (Enter)",
        "sidebar_header": "⚙️ Expert Filter Settings", "pe_label": "Max P/E (Ref < 25)",
        "peg_label": "Max PEG (Ref < 1.2)", "roe_label": "Min ROE % (Ref > 15)",
        "fcf_label": "Min FCF $B (Ref > 0.5)", "scan_range": "📊 Auto-Scan Range",
        "scan_btn": "Start Batch Scan", "match_only": "🔍 Show Matches Only",
        "snapshot_title": "📊 Core Metrics Snapshot", "report_title": "Deep Institutional Report",
        "moat_title": "🏰 Business Model & Moat Insight", "fin_title": "🏛️ Fundamentals & Financial Safety",
        "risk_title": "🚩 Risk, Sentiment & Trend Radar", "verdict_title": "🏆 Institutional Verdict",
        "strategy_label": "💡 Trading Strategy", "industry": "Industry", "summary": "Business Summary",
        "chart_title": "📈 Price vs 200D Moving Average (MA200)",
        "chart_close": "Closing Price", "chart_ma200": "MA200 Line", "chart_date": "Date",
        "strategies": ["Wait for bottom signals.", "Monitor closely.", "Accumulate on dips.", "Strong conviction, add position!"]
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# --- 2. 侧边栏参数 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
target_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
target_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
min_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
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
        m200_series = h['Close'].rolling(200).mean()
        m200_val = m200_series.iloc[-1]
        
        # 数据抓取
        pe = inf.get('forwardPE', 0)
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio') or 0
        roe = (inf.get('returnOnEquity') or 0) * 100
        fcf = (inf.get('freeCashflow') or 0) / 1e9
        debt = inf.get('debtToEquity', 0)
        sh = (inf.get('shortPercentOfFloat') or 0) * 100
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        inst_held = (inf.get('heldPercentInstitutions') or 0) * 100
        
        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {
            "代码": s, "价格": round(p, 2), "MA200": round(m200_val, 2), "P/E": pe, "PEG": peg, 
            "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "负债%": round(debt, 1), 
            "做空%": f"{sh:.1f}%", "上涨空间": f"{upside:+.1f}%", "结果": "✅ 符合" if ok else "❌ 不符",
            "_p": p, "_m": m200_val, "_h": h, "_m_series": m200_series, "_target": target, "_upside": upside, "_inst": inst_held,
            "_summary": inf.get('longBusinessSummary', "N/A"), "_industry": inf.get('industry', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 顶部快照
    st.subheader(f"{t['snapshot_title']} - {s['代码']}")
    d_cols = ["代码", "价格", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "负债%", "做空%", "上涨空间", "结果"]
    st.dataframe(pd.DataFrame([s])[d_cols], use_container_width=True, hide_index=True)
    
    # 2. 动态趋势图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
    fig.add_trace(go.Scatter(x=s['_m_series'].index, y=s['_m_series'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
    fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_title=t['chart_date'], yaxis_title=t['chart_close'])
    st.plotly_chart(fig, use_container_width=True)

    # 3. 智库级深度研报
    with st.expander(f"📜 {s['代码']} - {t['report_title']}", expanded=True):
        # 第一部分：护城河
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**{t['industry']}**: `{s['_industry']}`")
        st.write(f"**{t['summary']}**: {s['_summary'][:1000]}...")
        if s['ROE%'] > 35: moat_eval = "💎 **护城河评级：顶级 (Elite Moat)**。该公司的 ROE 极高，显示出强大的行业话语权和品牌溢价能力。"
        elif s['ROE%'] > 18: moat_eval = "🛡️ **护城河评级：宽阔 (Wide Moat)**。拥有成熟的竞争壁垒，盈利质量高且稳定。"
        else: moat_eval = "🚧 **护城河评级：较窄 (Narrow Moat)**。虽有盈利能力，但面临行业内激烈的价格竞争。"
        st.info(moat_eval)

        st.markdown("---")
        # 第二部分：财务安全
        st.markdown(f"### {t['fin_title']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG (性价比)", s['PEG'], delta="极佳" if s['PEG'] < 0.7 else None)
        c2.metric("分析师均价", f"${round(s['_target'], 2)}" if s['_target'] else "N/A", delta=s['上涨空间'])
        c3.metric("FCF (现金流)", f"${s['FCF$B']}B")
        
        debt_status = "🟢 财务极其稳健" if s['负债%'] < 40 else ("🟡 杠杆适中" if s['负债%'] < 100 else "🔴 财务压力偏高")
        st.write(f"· **杠杆审计**: 负债权益比 `{s['负债%']}%` — {debt_status}")
        st.write(f"· **成长空间**: 分析师一致预期目标价为 `${s['_target']}`，潜在获利空间约 `{s['上涨空间']}`。")

        st.markdown("---")
        # 第三部分：筹码博弈
        st.markdown(f"### {t['risk_title']}")
        r1, r2 = st.columns(2)
        with r1:
            inst_msg = f"机构持仓达 {s['_inst']:.1f}%，筹码高度集中。" if s['_inst'] > 75 else f"机构持仓约 {s['_inst']:.1f}%，散户参与度适中。"
            st.success(f"✅ **筹码分布**：{inst_msg} (做空率: {s['做空%']})")
        with r2:
            if s['_p'] < s['_m']: st.error("❌ **趋势雷达**：当前股价处于 MA200 牛熊分界线下方，需警惕下行风险。")
            else: st.success("📈 **趋势雷达**：股价获得 200 日均线有力支撑，目前处于右侧多头行情。")

        st.divider()
        # 第四部分：结论
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0) + (1 if s['_upside'] > 15 else 0)
        v_idx = min(score, 3)
        st.success(f"### {t['verdict_title']}：{['观望 (C)','持有 (B)','买入 (A)','强力买入 (A+)'][v_idx]}")
        st.info(f"💡 **{t['strategy_label']}**：{t['strategies'][v_idx]}")

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
    m_df = df[df["结果"].str.contains("✅")]
    if not m_df.empty:
        st.subheader("🏙️ 批量扫描结果研判中心")
        sel = st.selectbox("选择扫描出的标的进行深度透视:", m_df["代码"].tolist())
        target_s = df[df["代码"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df if st.checkbox(t["match_only"], value=True) else df, use_container_width=True, hide_index=True)
