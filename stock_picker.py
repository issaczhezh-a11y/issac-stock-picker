import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 语言配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资筛选器", "sidebar_header": "筛选条件设置",
        "ma200_label": "📈 只看股价在 200 日均线上方", "pe_label": "最高市盈率 (P/E)",
        "peg_label": "最高 PEG (市盈增长比)", "fcf_label": "最低自由现金流 (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高资产负债率 (%)",
        "index_label": "📊 选择扫描范围", "scan_btn": "开始扫描股票池",
        "matching_only": "🔍 只显示符合要求的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率(%)", "col_rsi": "RSI(14)", "col_macd": "MACD", 
        "col_vol_ratio": "量比(7D)", "col_result": "结果",
        "found_msg": "🎯 找到了 {n} 只优质资产：", "no_match": "⚠️ 暂无符合条件的股票。", "all_msg": "📊 正在显示全部 {n} 只扫描结果：",
        "last_update": "⏱️ 最后更新时间 (多伦多): "
    },
    "EN": {
        "title": "🍎 Issac-Style Value Screener", "sidebar_header": "Screener Settings",
        "ma200_label": "📈 Above 200D Moving Average Only", "pe_label": "Max P/E Ratio",
        "peg_label": "Max PEG Ratio", "fcf_label": "Min Free Cash Flow ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt-to-Equity (%)",
        "index_label": "📊 Select Index", "scan_btn": "Start Scanning",
        "matching_only": "🔍 Show Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI(14)", "col_macd": "MACD", 
        "col_vol_ratio": "Vol/7D Avg", "col_result": "Result",
        "found_msg": "🎯 Found {n} quality assets:", "no_match": "⚠️ No matching stocks found.", "all_msg": "📊 Showing all {n} scan results:",
        "last_update": "⏱️ Last Updated (Toronto): "
    }
}

# --- 2. 核心配置 ---
st.set_page_config(page_title="Issac美股筛选器", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]

st.title(t["title"])
st.sidebar.header(t["sidebar_header"])

above_ma200_only = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf_input = st.sidebar.number_input(t["fcf_label"], value=1.0)
target_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt_input = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

# --- 3. 获取名单函数 ---
@st.cache_data
def get_tickers(index_name):
    import urllib.request
    def fetch(url, idx):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return pd.read_html(response)[idx]
    
    if index_name == "S&P 500":
        df = fetch('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)
        return [str(s).replace('.', '-') for s in df['Symbol'].tolist()]
    else:
        df = fetch('https://en.wikipedia.org/wiki/Nasdaq-100', 4)
        return [str(tk).replace('.', '-') for tk in df['Ticker'].tolist()]

index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tickers(index_mode)

if 'scan_results' not in st.session_state: st.session_state.scan_results = None
if 'update_time' not in st.session_state: st.session_state.update_time = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Analyzing...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                # 价格与成交量指标
                price = hist['Close'].iloc[-1]
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else price
                
                # 🎯 7日量比计算
                vol_today = hist['Volume'].iloc[-1]
                vol_7d_avg = hist['Volume'].iloc[-8:-1].mean()
                vol_ratio = ((vol_today / vol_7d_avg) - 1) * 100 if vol_7d_avg > 0 else 0
                
                # 技术指标
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi_val = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
                ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                macd_status = "▲ 金叉" if macd_line.iloc[-1] > signal_line.iloc[-1] else "▼ 死叉"
                
                # 财务
                info = stock.info
                pe, peg, roe = info.get('forwardPE', 0), info.get('pegRatio', info.get('trailingPegRatio', 0)), info.get('returnOnEquity', 0) * 100
                fcf_val, debt_val = info.get('freeCashflow', 0) / 1e9, info.get('debtToEquity', 0)
                
                f_match = (0 < pe < target_pe and 0 < peg < target_peg and roe > target_roe and fcf_val > min_fcf_input and debt_val < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match

                results.append({
                    t["col_code"]: symbol, t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}", t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2), t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf_val, 2), t["col_debt"]: round(debt_val, 1),
                    t["col_rsi"]: round(rsi_val, 1), t["col_macd"]: macd_status,
                    t["col_vol_ratio"]: f"{vol_ratio:+.1f}%",
                    t["col_result"]: "✅ 符合" if final_cond else "❌ 不符",
                    "vol_num": vol_ratio # 隐藏字段用于 AI 分析
                })
            except: pass
            time.sleep(0.01)
    
    st.session_state.scan_results = results
    st.session_state.update_time = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示逻辑 (Issac Pro 终极深度双语分析版) ---
if st.session_state.get('scan_results'):
    df = pd.DataFrame(st.session_state.scan_results)
    if not df.empty:
        st.divider()
        st.caption(f"{t['last_update']} {st.session_state.update_time}")
        
        show_only = st.checkbox(t["matching_only"], value=True)
        match_df = df[df[t["col_result"]].str.contains("符合|Match")]
        display_df = match_df if show_only else df
        
        # --- 🤖 Issac AI Pro 深度研判系统 ---
        if not match_df.empty:
            st.subheader(f"🤖 Issac AI {'Stock Intelligence' if lang_choice=='EN' else '深度投资研判'}")
            selected_stock = st.selectbox(f"🎯 {'Select Target:' if lang_choice=='EN' else '选择个股进行全维度分析：'}", match_df[t["col_code"]].tolist())
            
            if selected_stock:
                s = match_df[match_df[t["col_code"]] == selected_stock].iloc[0]
                with st.expander(f"📊 {selected_stock} - {'Full Investment Analysis' if lang_choice=='EN' else '全维度投资价值报告'}", expanded=True):
                    
                    # 1. 估值与成长性 (Valuation & Growth)
                    st.markdown(f"#### 💰 {'Valuation & Growth' if lang_choice=='EN' else '估值与成长性'}")
                    peg_v = s[t['col_peg']]
                    v_msg = f"该股 PEG 为 `{peg_v}`，" if lang_choice=='CN' else f"With a PEG of `{peg_v}`, "
                    if peg_v < 0.5: v_msg += "处于极度低估状态，增长动能远超估值。" if lang_choice=='CN' else "the stock is deeply undervalued relative to its growth."
                    else: v_msg += "处于合理偏低区间，具备防御性。" if lang_choice=='CN' else "the valuation is reasonable with a safety margin."
                    st.write(f"· {v_msg}")
                    st.write(f"· {'High capital efficiency with ROE' if lang_choice=='EN' else '净资产收益率'} `{s[t['col_roe']]}%` {'reflects a strong industry moat.' if lang_choice=='EN' else '反映了卓越的行业竞争力。'}")

                    # 2. 财务稳健性 (Financial Health)
                    st.markdown(f"#### 🛡️ {'Financial Resilience' if lang_choice=='EN' else '财务稳健度 (护城河)'}")
                    fcf_v, debt_v = float(s[t['col_fcf']]), float(s[t['col_debt']])
                    f_msg = f"自由现金流 ${fcf_v}B 极其充沛，" if lang_choice=='CN' else f"FCF of ${fcf_v}B is very healthy, "
                    f_msg += f"且负债率仅为 {debt_v}%，抗风险能力极强。" if lang_choice=='CN' else f"combined with a low debt of {debt_v}%, showing elite resilience."
                    st.write(f"· {f_msg}")

                    # 3. 技术面与量能 (Technical & Volume)
                    st.markdown(f"#### 📈 {'Momentum & Volume' if lang_choice=='EN' else '趋势与动能'}")
                    v_ratio = float(s[t['col_vol_ratio']].replace('%',''))
                    vol_eval = "放量突破，大资金介入明显。" if v_ratio > 30 else ("缩量震荡，等待方向选择。" if v_ratio < -30 else "量能平稳。")
                    if lang_choice == 'EN':
                        vol_eval = "Strong volume surge, institutional buying." if v_ratio > 30 else ("Consolidating on low volume." if v_ratio < -30 else "Stable volume.")
                    
                    st.write(f"· **{'Volume' if lang_choice=='EN' else '量能'}:** `{s[t['col_vol_ratio']]}` — {vol_eval}")
                    st.write(f"· **{'Indicators' if lang_choice=='EN' else '指标'}:** RSI `{s[t['col_rsi']]}` ({'Oversold' if s[t['col_rsi']] < 30 else 'Neutral'}), MACD `{s[t['col_macd']]}`")

                    # 4. 终极评级 (Final Rating)
                    st.divider()
                    # 评级逻辑：PEG低+RSI低+金叉 = A+
                    score = 0
                    if peg_v < 0.7: score += 1
                    if s[t['col_rsi']] < 45: score += 1
                    if "金叉" in s[t['col_macd']] or "▲" in s[t['col_macd']]: score += 1
                    
                    ratings = {
                        3: ("STRONG BUY (A+)", "强力买入 (A+)", "🔥 估值、动能与量能产生完美共振，极具爆发力。"),
                        2: ("ACCUMULATE (A)", "建议建仓 (A)", "✅ 基本面扎实，建议在当前位置分批布局。"),
                        1: ("HOLD (B)", "建议持有 (B)", "⚖️ 处于盘整期，建议观察支撑位，不宜追高。"),
                        0: ("WAIT (C)", "观望 (C)", "⏳ 指标尚未企稳，建议等待回调或放量信号。")
                    }
                    r_en, r_cn, r_desc = ratings.get(score, ratings[1])
                    
                    st.success(f"### 🏆 {'Rating' if lang_choice=='EN' else '最终评级'}: {r_en if lang_choice=='EN' else r_cn}")
                    st.info(r_desc if lang_choice=='CN' else "The fundamentals are solid, but wait for a clear entry point or momentum shift.")

        # 展示主表格
        st.dataframe(display_df.drop(columns=['vol_num']), use_container_width=True, height=500, hide_index=True)
