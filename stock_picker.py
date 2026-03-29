import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 界面与字典 ---
st.set_page_config(page_title="Issac 投研终端", layout="wide")
st.title("🍎 Issac 机构级投研研究终端")

# 侧边栏
st.sidebar.header("🔍 深度搜索与筛选")
search_ticker = st.sidebar.text_input("个股深度透视 (如: NVDA, TSLA, PLTR)", "").upper().strip()
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
        # 技术指标
        diff = h['Close'].diff()
        g, l = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (g/l))) if l != 0 else 50
        # 财务数据
        pe, peg = inf.get('forwardPE', 0), (inf.get('pegRatio') or inf.get('trailingPegRatio') or 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0)*100
        
        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {"代码":s, "价格":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "负债率":round(debt,1), "做空率":f"{sh:.1f}%", "量比":f"{v_r:+.1f}%", "RSI":round(rsi,1), "结果":"✅ 符合" if ok else "❌ 不符", "_p":p, "_m":m200, "_sh":sh, "_v":v_r}
    except: return None

# --- 3. JPMorgan 级深度报告组件 ---
def show_deep_report(s):
    with st.expander(f"📑 {s['代码']} - JPMorgan 机构级深度投研报告", expanded=True):
        st.markdown("### 🏛️ 第一支柱：核心护城河分析")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG / 性价比", s['PEG'], delta="价值洼地" if s['PEG'] < 0.8 else None)
        c2.metric("ROE / 盈利效率", f"{s['ROE%']}%", delta="顶级印钞机" if s['ROE%'] > 30 else None)
        c3.metric("FCF / 现金流", f"${s['FCF$B']}B", delta="现金充沛" if s['FCF$B'] > 5 else None)
        
        roe_eval = "其 ROE 显示管理层具备极高的资本运作效率，行业壁垒深厚。" if s['ROE%'] > 25 else "盈利能力在行业中表现稳健。"
        st.info(f"**基本面深度点评：** 该股 PEG 为 `{s['PEG']}`，{roe_eval} 拥有 `${s['FCF$B']}B` 的自由现金流，为其未来的分红、股份回购或业务扩张提供了极强的安全边际。")

        st.markdown("---")
        st.markdown("### 🚩 第二支柱：筹码博弈与风险预警")
        r1, r2 = st.columns(2)
        with r1:
            if s['_sh'] > 5: st.error(f"⚠️ **空头警示**：做空率达 {s['_sh']:.1f}%。空头势力活跃，警惕股价阴跌。")
            else: st.success(f"✅ **筹码分布**：做空率仅为 {s['_sh']:.1f}%，筹码结构极其稳定。")
        with r2:
            if s['_p'] < s['_m']: st.error(f"❌ **趋势信号**：当前价格处于 MA200 牛熊线下方，属于弱势区间。")
            else: st.success(f"📈 **多头信号**：股价稳立于 200 日均线上方，处于强势上升通道。")

        st.markdown("---")
        st.markdown("### 📉 第三支柱：量价择时与动能")
        v_status = "🔥 **大资金介入**：量比显著放大，极大概率有机构扫货。" if s['_v'] > 50 else ("💤 **洗盘盘整**：成交低迷，正在蓄势。" if s['_v'] < -30 else "量能换手平稳。")
        st.write(f"· **7日量比对照**: `{s['量比']}` — {v_status}")
        st.write(f"· **技术指标**: RSI `{s['RSI']}` ({'超卖反弹预警' if s['RSI'] < 35 else '中性'})")

        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        verdict = ["Wait (C) - 建议观望", "Hold (B) - 建议持有", "Buy (A) - 逢低建仓", "STRONG BUY (A+) - 强力推荐"][score]
        st.success(f"### 🏆 最终评级：{verdict}")
        st.info(f"💡 **操盘建议：** {['目前趋势不明，建议等待底部放量信号。','基本面扎实但缺少动能，适合底仓观察。','优质资产，趋势已成，建议分批分仓布局。','极品资产，量价护城河齐备，建议果断持股或加仓！'][score]}")

# --- 4. 逻辑执行 ---
if search_ticker:
    st.subheader(f"🔍 实时透视: {search_ticker}")
    res = get_analysis(search_ticker)
    if res: show_deep_report(res)
    else: st.error("未找到该股票代码，或数据抓取失败。")

st.divider()
idx = st.sidebar.selectbox("自动扫描股票池", ["S&P 500", "Nasdaq 100"])
if st.sidebar.button("开始批量扫描"):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx=="S&P 500" else 4].iloc[:, 0].tolist()
    
    batch = []
    bar = st.progress(0)
    for i, s in enumerate(tks):
        item = get_analysis(str(s).replace('.','-'))
        if item: batch.append(item)
        bar.progress((i+1)/len(tks))
    st.session_state.batch_res = batch

if 'batch_res' in st.session_state:
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["结果"]=="✅ 符合"]
    if not m_df.empty:
        sel = st.selectbox("选择要分析的个股:", m_df["代码"].tolist())
        show_deep_report(df[df["代码"]==sel].iloc[0])
    st.dataframe(m_df if st.checkbox("只显示符合条件的股票", value=True) else df.drop(columns=["_p","_m","_sh","_v"]), use_container_width=True, hide_index=True)
