import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 界面与多语言配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端",
        "search_label": "🔍 个股深度透视 (输入代码并回车)",
        "sidebar_header": "⚙️ 专家级筛选参数",
        "pe_label": "最高 P/E (建议 < 25)",
        "peg_label": "最高 PEG (建议 < 1.2)",
        "roe_label": "最低 ROE % (建议 > 15)",
        "fcf_label": "最低 FCF $B (建议 > 0.5)",
        "scan_btn": "开始批量扫描",
        "match_only": "🔍 只看符合条件的股票",
        "verdict_title": "🏆 终极评级",
        "strategy_label": "💡 操盘建议"
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal",
        "search_label": "🔍 Manual Ticker Search (Enter to Search)",
        "sidebar_header": "⚙️ Expert Filter Settings",
        "pe_label": "Max P/E (Ref < 25)",
        "peg_label": "Max PEG (Ref < 1.2)",
        "roe_label": "Min ROE % (Ref > 15)",
        "fcf_label": "Min FCF $B (Ref > 0.5)",
        "scan_btn": "Start Batch Scan",
        "match_only": "🔍 Show Matches Only",
        "verdict_title": "🏆 Final Verdict",
        "strategy_label": "💡 Trading Strategy"
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# --- 2. 侧边栏：专家级输入栏目 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()

# 改为数字输入框，并给出建议值
target_pe = st.sidebar.number_input(t["pe_label"], value=25.0, step=1.0)
target_peg = st.sidebar.number_input(t["peg_label"], value=1.2, step=0.1)
min_roe = st.sidebar.number_input(t["roe_label"], value=15.0, step=1.0)
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5, step=0.1)

# --- 3. 核心抓取与分析函数 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        # 财务数据
        pe = inf.get('forwardPE', 0)
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio') or 0
        roe = (inf.get('returnOnEquity') or 0) * 100
        fcf = (inf.get('freeCashflow') or 0) / 1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0) * 100
        summary = inf.get('longBusinessSummary', "N/A")
        industry = inf.get('industry', "N/A")

        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {"代码":s, "价格":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "负债率":round(debt,1), "做空率":f"{sh:.1f}%", "量比":f"{v_r:+.1f}%", "结果":"✅ 符合" if ok else "❌ 不符", "_p":p, "_m":m200, "_sh":sh, "_v":v_r, "_summary":summary, "_industry":industry}
    except: return None

# --- 4. 深度报告展示组件 ---
def show_deep_report(s):
    st.subheader(f"📊 {s['代码']} 核心参数快照")
    display_cols = [c for c in s.keys() if not c.startswith('_')]
    st.dataframe(pd.DataFrame([s])[display_cols], use_container_width=True, hide_index=True)

    with st.expander(f"📑 {s['代码']} - 深度投研报告", expanded=True):
        st.markdown(f"### 🏰 商业模式与护城河")
        st.write(f"**行业:** `{s['_industry']}`")
        st.write(f"**业务简介:** {s['_summary'][:500]}...")
        
        if s['ROE%'] > 30: moat = "🔥 **核心竞争力：** 极高 ROE 显示其拥有极强的市场垄断力或技术壁垒。"
        elif s['ROE%'] > 15: moat = "✅ **竞争优势：** 盈利能力稳健，具备一定的不可替代性。"
        else: moat = "⚠️ **提醒：** 护城河尚浅，需关注竞争对手动态。"
        st.info(moat)

        st.markdown("---")
        st.markdown("### 🏛️ 核心财务评估")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG / 性价比", s['PEG'], delta="价值洼地" if s['PEG'] < 0.8 else None)
        c2.metric("ROE / 盈利效率", f"{s['ROE%']}%", delta="高回报" if s['ROE%'] > 25 else None)
        c3.metric("FCF / 现金流", f"${s['FCF$B']}B")

        st.markdown("---")
        st.markdown("### 🚩 风险与趋势")
        r1, r2 = st.columns(2)
        with r1:
            if s['_sh'] > 5: st.error(f"⚠️ **空头警示**：做空率 {s['_sh']:.1f}%，抛压大。")
            else: st.success(f"✅ **筹码稳固**：做空率低。")
        with r2:
            if s['_p'] < s['_m']: st.error(f"❌ **趋势信号**：价格在均线下方。")
            else: st.success(f"📈 **多头信号**：股价稳立于均线上方。")

        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        verdict_list = ["Wait (C)", "Hold (B)", "Buy (A)", "STRONG BUY (A+)"]
        strategy_list = ["建议等待放量信号。", "适合底仓观察。", "建议分批布局。", "建议果断加仓！"]
        st.success(f"### {t['verdict_title']}：{verdict_list[score]}")
        st.info(f"{t['strategy_label']}：{strategy_list[score]}")

# --- 5. 主逻辑 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: show_deep_report(res)
    else: st.error("未找到代码。")
else:
    st.divider()
    idx = st.sidebar.selectbox("批量扫描范围", ["S&P 500", "Nasdaq 100"])
    if st.sidebar.button(t["scan_btn"]):
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r: 
            tks = pd.read_html(r)[0 if idx=="S&P 500" else 4].iloc[:, 0].tolist()
        
        batch = []
        bar = st.progress(0)
        for i, code in enumerate(tks):
            item = get_analysis(str(code).replace('.','-'))
            if item: batch.append(item)
            bar.progress((i+1)/len(tks))
        st.session_state.batch_res = batch

    if 'batch_res' in st.session_state:
        df = pd.DataFrame(st.session_state.batch_res)
        clean_df = df[[c for c in df.columns if not c.startswith('_')]]
        m_df = clean_df[clean_df["结果"]=="✅ 符合"]
        if not m_df.empty:
            sel = st.selectbox("选择批量扫描出的个股研判:", m_df["代码"].tolist())
            show_deep_report(df[df["代码"] == sel].iloc[0])
        st.dataframe(m_df if st.checkbox(t["match_only"], value=True) else clean_df, use_container_width=True, hide_index=True)
