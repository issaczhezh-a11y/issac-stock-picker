import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 界面与配置 ---
st.set_page_config(page_title="Issac 投研终端", layout="wide")
st.title("🍎 Issac 机构级投研研究终端")

# 侧边栏
st.sidebar.header("🔍 深度搜索与筛选")
search_ticker = st.sidebar.text_input("个股深度透视 (输入代码并回车)", "").upper().strip()
st.sidebar.divider()
target_pe = st.sidebar.slider("最高 P/E", 5.0, 100.0, 30.0)
target_peg = st.sidebar.slider("最高 PEG", 0.1, 3.0, 1.2)
min_roe = st.sidebar.slider("最低 ROE (%)", 0.0, 50.0, 15.0)
min_fcf = st.sidebar.number_input("最低 FCF (10亿$)", value=0.5)

# --- 2. 核心分析函数 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        # 财务数据
        pe, peg = inf.get('forwardPE', 0), (inf.get('pegRatio') or inf.get('trailingPegRatio') or 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0)*100
        # 🎯 新增：业务简介
        summary = inf.get('longBusinessSummary', "暂无公司业务简介。")
        industry = inf.get('industry', "未知行业")

        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {"代码":s, "价格":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "负债率":round(debt,1), "做空率":f"{sh:.1f}%", "量比":f"{v_r:+.1f}%", "结果":"✅ 符合" if ok else "❌ 不符", "_p":p, "_m":m200, "_sh":sh, "_v":v_r, "_summary":summary, "_industry":industry}
    except: return None

# --- 3. JPMorgan 级深度报告组件 ---
def show_deep_report(s, title_prefix=""):
    st.subheader(f"{title_prefix} {s['代码']} 核心参数快照")
    display_cols = [c for c in s.keys() if not c.startswith('_')]
    st.dataframe(pd.DataFrame([s])[display_cols], use_container_width=True, hide_index=True)

    with st.expander(f"📑 {s['代码']} - 机构级深度投研报告", expanded=True):
        # 🎯 新增模块：商业模式与护城河
        st.markdown(f"### 🏰 商业模式与竞争壁垒 (Moat Analysis)")
        st.write(f"**所属行业：** `{s['_industry']}`")
        st.write(f"**公司简介：** {s['_summary'][:500]}...") # 截取前500字防止过长
        
        # 逻辑判断护城河
        moat_eval = ""
        if s['ROE%'] > 30 and s['FCF$B'] > 5:
            moat_eval = "🔥 **核心竞争力：** 该公司 ROE 极高且现金流极其充沛，显示其拥有**独一无二的技术或品牌垄断力**，极难被对手取代。属于行业‘标准制定者’。"
        elif s['ROE%'] > 15:
            moat_eval = "✅ **竞争优势：** 盈利能力高于行业平均水平，拥有较强的用户粘性或技术门槛，具备一定的不可替代性。"
        else:
            moat_eval = "⚠️ **取代风险：** 盈利能力尚可但护城河不够深，需警惕行业竞争加剧导致的市场份额流失。"
        st.info(moat_eval)

        st.markdown("---")
        st.markdown("### 🏛️ 第一支柱：核心财务评估")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG / 性价比", s['PEG'], delta="价值洼地" if s['PEG'] < 0.8 else None)
        c2.metric("ROE / 盈利效率", f"{s['ROE%']}%", delta="顶级印钞机" if s['ROE%'] > 30 else None)
        c3.metric("FCF / 现金流", f"${s['FCF$B']}B")

        st.markdown("---")
        st.markdown("### 🚩 第二支柱：风险预警 & 趋势")
        r1, r2 = st.columns(2)
        with r1:
            if s['_sh'] > 5: st.error(f"⚠️ **空头警示**：做空率达 {s['_sh']:.1f}%。")
            else: st.success(f"✅ **筹码稳固**：做空率仅为 {s['_sh']:.1f}%。")
        with r2:
            if s['_p'] < s['_m']: st.error(f"❌ **趋势信号**：价格处于 MA200 下方。")
            else: st.success(f"📈 **多头信号**：股价稳立于 200 日线上方。")

        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        verdict = ["Wait (C) - 建议观望", "Hold (B) - 建议持有", "Buy (A) - 逢低建仓", "STRONG BUY (A+) - 强力推荐"][score]
        st.success(f"### 🏆 终极评级：{verdict}")

# --- 4. 主逻辑控制 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: show_deep_report(res, title_prefix="🔍 搜索个股:")
    else: st.error("未找到代码或数据抓取失败。")
else:
    st.divider()
    idx = st.sidebar.selectbox("批量扫描范围", ["S&P 500", "Nasdaq 100"])
    if st.sidebar.button("开始批量扫描"):
        import urllib.request
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r: 
            tks = pd.read_html(r)[0 if idx=="S&P 500" else 4].iloc[:, 0].tolist()
        
        batch = []
        bar = st.progress(0)
        for i, s_code in enumerate(tks):
            item = get_analysis(str(s_code).replace('.','-'))
            if item: batch.append(item)
            bar.progress((i+1)/len(tks))
        st.session_state.batch_res = batch

    if 'batch_res' in st.session_state:
        df = pd.DataFrame(st.session_state.batch_res)
        clean_df = df[[c for c in df.columns if not c.startswith('_')]]
        m_df = clean_df[clean_df["结果"]=="✅ 符合"]
        if not m_df.empty:
            st.subheader("🏙️ 批量扫描结果研判")
            sel = st.selectbox("选择个股进行研判:", m_df["代码"].tolist())
            s_data = df[df["代码"] == sel].iloc[0]
            show_deep_report(s_data)
        st.dataframe(m_df if st.checkbox("只显示符合条件的股票", value=True) else clean_df, use_container_width=True, hide_index=True)
