import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- 1. 真·全语境多语言字典 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端", "search_label": "🔍 个股透视 (回车搜索)",
        "sidebar_header": "⚙️ 专家级筛选参数", "pe_label": "最高 P/E (建议 < 25)",
        "peg_label": "最高 PEG (建议 < 1.2)", "roe_label": "最低 ROE % (建议 > 15)",
        "fcf_label": "最低 FCF $B (建议 > 0.5)", "scan_range": "📊 批量扫描范围",
        "scan_btn": "开始批量扫描", "match_only": "🔍 只看符合条件的股票",
        "snapshot_title": "📊 核心参数快照", "report_title": "深度投研报告",
        "chart_title": "📈 股价与 200 日均线 (MA200) 趋势对比",
        "chart_close": "收盘价", "chart_ma200": "200日均线", "chart_date": "日期",
        "moat_title": "🏰 商业模式与护城河透视", "fin_title": "🏛️ 财务与估值空间",
        "risk_title": "🚩 筹码博弈与趋势雷达", "verdict_title": "🏆 终极研判",
        "strategy_label": "💡 操盘策略",
        "strategies": ["⚠️ 趋势极弱，场外等候。","⚖️ 缺乏动能，底仓观察。","✅ 趋势向好，逢低建仓。","🔥 极品资产，果断持有！"]
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal", "search_label": "🔍 Manual Ticker Search (Enter)",
        "sidebar_header": "⚙️ Expert Filter Settings", "pe_label": "Max P/E (Ref < 25)",
        "peg_label": "Max PEG (Ref < 1.2)", "roe_label": "Min ROE % (Ref > 15)",
        "fcf_label": "Min FCF $B (Ref > 0.5)", "scan_range": "📊 Auto-Scan Range",
        "scan_btn": "Start Batch Scan", "match_only": "🔍 Show Matches Only",
        "snapshot_title": "📊 Core Metrics Snapshot", "report_title": "Deep Research Report",
        "chart_title": "📈 Price vs 200D Moving Average (MA200)",
        "chart_close": "Closing Price", "chart_ma200": "MA200 Line", "chart_date": "Date",
        "moat_title": "🏰 Business Model & Moat Analysis", "fin_title": "🏛️ Fundamentals & Valuation",
        "risk_title": "🚩 Risk & Trend Radar", "verdict_title": "🏆 Institutional Verdict",
        "strategy_label": "💡 Strategy",
        "strategies": ["Wait for bottom.", "Monitor only.", "Accumulate on dips.", "High conviction buy."]
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# --- 2. 侧边栏 ---
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

# --- 3. 核心引擎 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean()
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        pe, peg = inf.get('forwardPE', 0), (inf.get('pegRatio') or inf.get('trailingPegRatio') or 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0)*100
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        inst_held = (inf.get('heldPercentInstitutions') or 0) * 100
        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {
            "代码":s, "价格":round(p,2), "MA200":round(m200.iloc[-1],2), "P/E":pe, "PEG":peg, 
            "ROE%":round(roe,1), "FCF$B":round(fcf,1), "负债%":round(debt,1), 
            "做空%":f"{sh:.1f}%", "上涨空间":f"{upside:+.1f}%", "结果":"✅ 符合" if ok else "❌ 不符",
            "_h":h, "_m_series":m200, "_target":target, "_upside":upside, "_inst":inst_held,
            "_summary":inf.get('longBusinessSummary', "N/A"), "_industry":inf.get('industry', "N/A")
        }
    except: return None

def render_report(s):
    # 1. 顶部快照
    st.subheader(f"{t['snapshot_title']} - {s['代码']}")
    display_cols = ["代码", "价格", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "负债%", "做空%", "上涨空间", "结果"]
    st.dataframe(pd.DataFrame([s])[display_cols], use_container_width=True, hide_index=True)
    
    # 2. 🎯 Plotly 可视化趋势图
    st.markdown(f"### {t['chart_title']}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2)))
    fig.add_trace(go.Scatter(x=s['_m_series'].index, y=s['_m_series'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
    fig.update_layout(
        template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=t['chart_date'], yaxis_title=t['chart_close']
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. 深度报告
    with st.expander(f"📑 {s['代码']} - {t['report_title']}", expanded=True):
        st.markdown(f"#### {t['moat_title']}")
        st.write(f"**{t['industry']}:** `{s['_industry']}`")
        st.write(f"**{t['summary']}:** {s['_summary'][:800]}...")
        
        st.markdown(f"#### {t['fin_title']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG", s['PEG'], delta="Value" if s['PEG'] < 0.7 else None)
        c2.metric("ROE", f"{s['ROE%']}%")
        c3.metric("FCF", f"${s['FCF$B']}B")
        
        st.markdown(f"#### 🎯 分析师预期与持仓")
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("目标价均值", f"${s['_target']}" if s['_target'] else "N/A")
        col_t2.metric("潜在空间", s['上涨空间'], delta="Huge" if s['_upside'] > 20 else None)
        st.write(f"· **机构持仓**: `{s['_inst']:.1f}%` — {'筹码极其稳固' if s['_inst'] > 75 else '分布均衡'}")

        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['价格'] > s['MA200'] else 0) + (1 if s['_upside'] > 15 else 0)
        verdict_idx = min(score, 3)
        st.success(f"### {t['verdict_title']}: {['C','B','A','A+'][verdict_idx]}")
        st.info(f"💡 {t['strategy_label']}：{t['strategies'][verdict_idx]}")

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
    display_cols = ["代码", "价格", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "负债%", "做空%", "上涨空间", "结果"]
    m_df = df[df["结果"].str.contains("✅")]
    if not m_df.empty:
        st.subheader("🏙️ 批量扫描结果中心")
        sel = st.selectbox("选择扫描出的标的进行透视:", m_df["代码"].tolist())
        target_s = df[df["代码"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[display_cols] if st.checkbox(t["match_only"], value=True) else df[display_cols], use_container_width=True, hide_index=True)
