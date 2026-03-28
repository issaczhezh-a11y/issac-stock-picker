import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 核心字典 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资筛选器", "sidebar_header": "筛选设置",
        "ma200_label": "📈 仅限 MA200 上方", "pe_label": "最高 P/E",
        "peg_label": "最高 PEG", "fcf_label": "最低 FCF (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高负债率 (%)",
        "index_label": "📊 扫描范围", "scan_btn": "开始扫描",
        "matching_only": "🔍 只看符合条件的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "量比(7D)", "col_short": "做空率", "col_res": "结果",
        "last_up": "⏱️ 最后更新: "
    },
    "EN": {
        "title": "🍎 Issac Picker Pro", "sidebar_header": "Settings",
        "ma200_label": "📈 Above MA200 Only", "pe_label": "Max P/E",
        "peg_label": "Max PEG", "fcf_label": "Min FCF ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt (%)",
        "index_label": "📊 Select Index", "scan_btn": "Start Scan",
        "matching_only": "🔍 Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "Vol/7D", "col_short": "Short %", "col_res": "Result",
        "last_up": "⏱️ Last Updated: "
    }
}

st.set_page_config(page_title="Issac Picker", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# 侧边栏参数
above_m200_check = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe, target_peg = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0), st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf, min_roe = st.sidebar.number_input(t["fcf_label"], value=1.0), st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

@st.cache_data
def get_tk(idx_name):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_name == "S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        df = pd.read_html(resp)[0 if idx_name == "S&P 500" else 4]
    return [str(s).replace('.', '-') for s in df.iloc[:, 0].tolist()]

idx_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tk(idx_mode)

if 'res' not in st.session_state: st.session_state.res, st.session_state.up_t = None, None

# --- 扫描逻辑 ---
if st.button(t["scan_btn"]):
    data = []
    with st.spinner('Performing Institutional Analysis...'):
        for s in tickers:
            try:
                tk = yf.Ticker(s)
                h = tk.history(period="1y")
                if len(h) < 35: continue
                cur_p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
                v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
                diff = h['Close'].diff()
                gain, loss = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + (gain/loss))) if loss != 0 else 50
                ema12, ema26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
                macd_v = ema12 - ema26
                macd_txt = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
                inf = tk.info
                pe, peg = inf.get('forwardPE'), inf.get('pegRatio') or inf.get('trailingPegRatio')
                roe, fcf, debt = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9, inf.get('debtToEquity') or 0
                sh = (inf.get('shortPercentOfFloat') or 0)*100
                f_m = (pe and 0 < pe < target_pe) and (peg is not None and peg < target_peg) and (roe > min_roe) and (fcf > min_fcf) and (debt < max_debt)
                ok = "✅ 符合" if (f_m and cur_p > m200 if above_m200_check else f_m) else "❌ 不符"
                data.append({t["col_code"]:s, t["col_price"]:round(cur_p, 2), t["col_ma200"]:round(m200, 2), t["col_pe"]:pe, t["col_peg"]:peg, t["col_roe"]:round(roe,1), t["col_fcf"]:round(fcf,1), t["col_debt"]:round(debt,1), t["col_rsi"]:round(rsi,1), t["col_macd"]:macd_txt, t["col_short"]:f"{sh:.1f}%", t["col_vol"]:f"{v_r:+.1f}%", t["col_res"]:ok, "h_p":cur_p, "h_m":m200, "h_sh":sh, "h_v":v_r})
            except: pass
    st.session_state.res = data
    st.session_state.up_t = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 展示逻辑 ---
if st.session_state.res:
    df = pd.DataFrame(st.session_state.res)
    st.caption(f"{t['last_up']} {st.session_state.up_t}")
    clean_df = df.drop(columns=["h_p", "h_m", "h_sh", "h_v"])
    m_df = clean_df[clean_df[t["col_res"]].str.contains("✅")]
    
    if not m_df.empty:
        st.subheader("🏙️ Issac AI 机构级研报中心")
        sel = st.selectbox("🎯 选择个股进行深度透视:", m_df[t["col_code"]].tolist())
        s = df[df[t["col_code"]] == sel].iloc[0]
        
        with st.expander(f"📜 {sel} - 综合投资评级报告 (Confidential)", expanded=True):
            # 1. 估值与盈利 (Valuation & Moat)
            st.markdown("#### 🏛️ 第一支柱：财务护城河 (Fundamentals)")
            c1, c2, c3 = st.columns(3)
            c1.metric("PEG / 性价比", s[t['col_peg']] if s[t['col_peg']] else "N/A", delta="Underpriced" if s[t['col_peg']] and s[t['col_peg']] < 0.7 else None)
            c2.metric("ROE / 资本回报", f"{s[t['col_roe']]}%", delta="Elite" if s[t['col_roe']] > 25 else None)
            c3.metric("FCF / 现金流", f"${s[t['col_fcf']]}B", delta="Cash Cow" if s[t['col_fcf']] > 5 else None)
            
            # 深度文字研判
            peg_eval = "其 PEG 处于极低水平，意味着市场尚未完全定价其增长动能。" if s[t['col_peg']] and s[t['col_peg']] < 0.7 else "估值处于合理中枢。"
            roe_eval = f"ROE ({s[t['col_roe']]}%) 显示管理层具备卓越的资本运作效率，具备典型的强者恒强特征。" if s[t['col_roe']] > 25 else "盈利能力稳健。"
            st.info(f"**核心逻辑：** {peg_eval} {roe_eval} 自由现金流达 ${s[t['col_fcf']]}B，为未来的分红和研发提供了深厚的护城河。")

            # 2. 筹码与风险 (Risk & Shorting)
            st.markdown("---")
            st.markdown("#### 🚩 第二支柱：筹码博弈与风险 (Bears & Sentiment)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if s['h_sh'] > 5: st.error(f"⚠️ **空头集结**: 做空率达 {s['h_sh']:.1f}%。尽管基本面好，但抛压沉重，需警惕阴跌。")
                else: st.success(f"✅ **筹码稳固**: 做空率仅为 {s['h_sh']:.1f}%，机构持股信心较强。")
            with col_r2:
                if s['h_p'] < s['h_m']: st.error(f"❌ **趋势破位**: 股价低于 MA200 牛熊线，属于典型的‘左侧捞底’，风险等级：高。")
                else: st.success(f"📈 **多头趋势**: 股价运行于 MA200 上方，技术面支撑强劲。")

            # 3. 量能与择时 (Timing & Volume)
            st.markdown("---")
            st.markdown("#### 📉 第三支柱：量价共振 (Technical Timing)")
            v_status = "🔥 **大资金介入**: 7日均量激增，极大概率有机构扫货。" if s['h_v'] > 50 else ("💤 **洗盘/盘整**: 缩量震荡中，等待方向选择。" if s['h_v'] < -30 else "量能平稳换手。")
            st.write(f"· **7日量比**: `{s[t['col_vol']]}` — {v_status}")
            st.write(f"· **强弱指标**: RSI `{s[t['col_rsi']]}` ({'超卖反弹点' if s[t['col_rsi']] < 35 else '中性'}) | MACD `{s[t['col_macd']]}`")

            # 4. 最终结论 (Final Verdict)
            st.divider()
            score = (1 if s[t['col_peg']] and s[t['col_peg']] < 0.7 else 0) + (1 if s[t['col_roe']] > 25 else 0) + (1 if s['h_p'] > s['h_m'] else 0)
            rating = ["Wait (C) - 观望", "Hold (B) - 持有", "Buy (A) - 建议买入", "STRONG BUY (A+) - 强力推荐"][score]
            st.success(f"### 🏆 JPMorgan 级终极评级: {rating}")
            st.info(f"💡 **Issac 操盘策略：** {['目前趋势不明，建议离场观望。','基本面扎实但缺少动能，适合底仓观察。','优质资产，趋势已成，建议逢低分批建仓。','极品资产，量价护城河齐备，建议果断布局！'][score]}")

    st.dataframe(m_df if st.checkbox(t["matching_only"], value=True) else clean_df, use_container_width=True, hide_index=True)
