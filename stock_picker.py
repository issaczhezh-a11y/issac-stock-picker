import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 配置 ---
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
        "last_up": "⏱️ 最后更新 (多伦多): "
    },
    "EN": {
        "title": "🍎 Issac-Style Picker Pro", "sidebar_header": "Settings",
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

st.set_page_config(page_title="Issac Picker Pro", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

above_ma200 = st.sidebar.checkbox(t["ma200_label"], value=False)
t_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
t_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
m_fcf = st.sidebar.number_input(t["fcf_label"], value=1.0)
t_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
m_debt = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

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

# --- 4. 扫描 ---
if st.button(t["scan_btn"]):
    data = []
    with st.spinner('Analyzing...'):
        for s in tickers:
            try:
                tk = yf.Ticker(s)
                h = tk.history(period="1y")
                if len(h) < 35: continue
                cur_p, m200 = float(h['Close'].iloc[-1]), float(h['Close'].rolling(200).mean().iloc[-1])
                v_avg = h['Volume'].iloc[-8:-1].mean()
                v_r = ((h['Volume'].iloc[-1] / v_avg) - 1) * 100 if v_avg > 0 else 0
                
                diff = h['Close'].diff()
                gain, loss = diff.where(diff > 0, 0).rolling(14).mean(), -diff.where(diff < 0, 0).rolling(14).mean()
                rsi = 100 - (100 / (1 + (gain.iloc[-1]/loss.iloc[-1]))) if loss.iloc[-1] != 0 else 50
                
                ema12, ema26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
                macd_v = ema12 - ema26
                macd_s = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
                
                inf = tk.info
                pe, peg, roe = float(inf.get('forwardPE', 0)), float(inf.get('pegRatio', 0.1)), float(inf.get('returnOnEquity', 0)) * 100
                fcf, debt, sh = float(inf.get('freeCashflow', 0))/1e9, float(inf.get('debtToEquity', 0)), float(inf.get('shortPercentOfFloat', 0))*100
                
                f_m = (0 < pe < t_pe and 0 <= peg < t_peg and roe > t_roe and fcf > m_fcf and debt < m_debt)
                ok = "✅ 符合" if (f_m and cur_p > m200 if above_ma200 else f_m) else "❌ 不符"
                
                data.append({
                    t["col_code"]:s, t["col_price"]:f"${cur_p:.2f}", t["col_ma200"]:f"${m200:.2f}", 
                    t["col_pe"]:pe, t["col_peg"]:peg, t["col_roe"]:round(roe,1), 
                    t["col_fcf"]:round(fcf,1), t["col_debt"]:round(debt,1), 
                    t["col_rsi"]:round(rsi,1), t["col_macd"]:macd_s, t["col_short"]:f"{sh:.1f}%", 
                    t["col_vol"]:f"{v_r:+.1f}%", t["col_res"]:ok, 
                    "_p":cur_p, "_m":m200, "_sh":sh, "_v":v_r # 🎯 关键：显式定义隐藏字段
                })
            except: pass
    st.session_state.res = data
    st.session_state.up_t = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示与 深度报告 ---
if st.session_state.res:
    df = pd.DataFrame(st.session_state.res)
    st.caption(f"{t['last_up']} {st.session_state.up_t}")
    m_df = df[df[t["col_res"]].str.contains("✅")]
    
    if not m_df.empty:
        st.subheader("🤖 Issac AI Pro 深度研判中心")
        sel = st.selectbox("🎯 Target Stock:", m_df[t["col_code"]].tolist())
        s = m_df[m_df[t["col_code"]] == sel].iloc[0]
        
        with st.expander(f"📊 {sel} - 机构级深度投研报告", expanded=True):
            # 1. 风险与大势
            st.markdown("#### 🚩 风险雷达 & 趋势判定")
            c1, c2 = st.columns(2)
            with c1:
                if s['_sh'] > 5: st.error(f"⚠️ **高空头警示**: 做空率 {s['_sh']:.1f}%，抛压极大。")
                else: st.success("✅ **筹码稳健**: 无明显大规模做空。")
            with c2:
                if s['_p'] < s['_m']: st.error("❌ **弱势行情**: 股价在 MA200 下方，小心阴跌。")
                else: st.success("📈 **牛市行情**: 站稳牛熊线，向上动能足。")

            # 2. 护城河深度解读
            st.markdown("---")
            st.markdown("#### 🏛️ 基本面护城河 (Fundamentals)")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("PEG (性价比)", s[t['col_peg']], delta="极度低估" if s[t['col_peg']] < 0.6 else None)
            col_b.metric("ROE (盈利能力)", f"{s[t['col_roe']]}%", delta="超强印钞机" if s[t['col_roe']] > 30 else None)
            col_c.metric("FCF (现金储备)", f"${s[t['col_fcf']]}B")
            
            st.write(f"· **深度点评**: 该公司目前的 P/E 为 `{s[t['col_pe']]}`。配合 ROE 来看，管理层资本运作效率{'极高' if s[t['col_roe']] > 25 else '稳健'}。自由现金流充足，具备极强的抗风险和回购能力。")

            # 3. 量价择时 (Timing)
            st.markdown("---")
            st.markdown("#### 📉 技术面 & 量能异动")
            v_msg = "🔥 **巨量突破**: 资金介入明显！" if s['_v'] > 50 else ("💤 **缩量盘整**: 散户博弈为主。" if s['_v'] < -30 else "量能平稳换手。")
            st.write(f"· **成交量(7日对比)**: `{s[t['col_vol']]}` — {v_msg}")
            st.write(f"· **趋势信号**: MACD `{s[t['col_macd']]}` | RSI `{s[t['col_rsi']]}` ({'超卖反弹预警' if s[t['col_rsi']] < 35 else '中性偏稳'})")

            # 结论
            st.divider()
            score = (1 if s[t['col_peg']] < 0.7 else 0) + (1 if s[t['col_roe']] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
            res_map = {3:("Strong Buy (A+)", "🔥 极品资产，量价齐飞，建议果断关注。"), 2:("Buy (A)", "✅ 优质公司，趋势向好，建议分批入场。"), 1:("Hold (B)", "⚖️ 估值尚可但趋势偏弱，建议设好止损。"), 0:("Wait (C)", "⏳ 风险较高，建议等待底部放量信号。")}
            rating, desc = res_map.get(score, res_map[1])
            st.success(f"### 🏆 最终评级: {rating}")
            st.info(f"💡 **操盘建议**: {desc}")

    st.dataframe(m_df if st.checkbox(t["matching_only"], value=True) else df, use_container_width=True, hide_index=True)
