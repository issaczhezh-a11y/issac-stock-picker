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
        "col_vol_ratio": "量比(7D)", "col_short": "做空率", "col_result": "结果",
        "found_msg": "🎯 找到了 {n} 只优质资产：", "no_match": "⚠️ 暂无符合条件的股票。", "last_update": "⏱️ 最后更新时间 (多伦多): "
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
        "col_vol_ratio": "Vol/7D Avg", "col_short": "Short %", "col_result": "Result",
        "found_msg": "🎯 Found {n} quality assets:", "no_match": "⚠️ No matching stocks found.", "last_update": "⏱️ Last Updated (Toronto): "
    }
}

# --- 2. 核心配置 ---
st.set_page_config(page_title="Issac美股筛选器", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

above_ma200_only = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf_input = st.sidebar.number_input(t["fcf_label"], value=1.0)
target_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt_input = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

@st.cache_data
def get_tickers(index_name):
    import urllib.request
    def fetch(url, idx):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: return pd.read_html(response)[idx]
    return fetch('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)['Symbol'].tolist() if index_name == "S&P 500" else fetch('https://en.wikipedia.org/wiki/Nasdaq-100', 4)['Ticker'].tolist()

index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = [str(s).replace('.', '-') for s in get_tickers(index_mode)]

if 'scan_results' not in st.session_state: st.session_state.scan_results = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Scanning...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                # 核心价格数据
                price = float(hist['Close'].iloc[-1])
                ma200 = float(hist['Close'].rolling(200).mean().iloc[-1])
                vol_ratio = ((hist['Volume'].iloc[-1] / hist['Volume'].iloc[-8:-1].mean()) - 1) * 100
                
                # 技术指标
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi_val = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                # 财务数据 (数据清洗)
                info = stock.info
                pe = float(info.get('forwardPE', 0))
                peg = float(info.get('pegRatio', info.get('trailingPegRatio', 0)))
                roe = float(info.get('returnOnEquity', 0)) * 100
                fcf = float(info.get('freeCashflow', 0)) / 1e9
                debt = float(info.get('debtToEquity', 0))
                short_ratio = float(info.get('shortPercentOfFloat', 0)) * 100

                # 🎯 修复 PEG 0 值筛选逻辑
                f_match = (0 < pe < target_pe and 0 <= peg < target_peg and roe > target_roe and fcf > min_fcf_input and debt < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match

                results.append({
                    t["col_code"]: symbol, t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}", t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2), t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf, 2), t["col_debt"]: round(debt, 1),
                    t["col_rsi"]: round(rsi_val, 1), 
                    t["col_short"]: f"{short_ratio:.2f}%",
                    t["col_vol_ratio"]: f"{vol_ratio:+.1f}%",
                    t["col_result"]: "✅ 符合" if final_cond else "❌ 不符",
                    # 🎯 隐藏数据字段（变量名前加下划线，Streamlit 默认会处理或手动排除）
                    "_short_val": short_ratio, "_price_val": price, "_ma200_val": ma200, "_vol_val": vol_ratio
                })
            except: pass
            time.sleep(0.01)
    st.session_state.scan_results = results
    st.session_state.update_time = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示逻辑 (Issac Pro 机构级全维度研判系统) ---
if st.session_state.get('scan_results'):
    df = pd.DataFrame(st.session_state.scan_results)
    if not df.empty:
        st.divider()
        st.caption(f"{t['last_update']} {st.session_state.update_time}")
        
        display_cols = [c for c in df.columns if not c.startswith('_')]
        match_df = df[df[t["col_result"]].str.contains("符合|Match")]
        
        if not match_df.empty:
            st.subheader(f"🤖 Issac AI {'Intelligence Center' if lang_choice=='EN' else '深度投资研判中心'}")
            selected_stock = st.selectbox(f"🎯 {'Deep Dive Analysis:' if lang_choice=='EN' else '选择目标个股进行机构级深度研判：'}", match_df[t["col_code"]].tolist())
            
            if selected_stock:
                s = match_df[match_df[t["col_code"]] == selected_stock].iloc[0]
                with st.expander(f"📑 {selected_stock} - {'Full Investment Thesis' if lang_choice=='EN' else '全维度深度投资价值报告'}", expanded=True):
                    
                    # 第一部分：风险预警 (Risk Radar)
                    st.markdown(f"### 🚩 {'Risk Radar' if lang_choice=='EN' else '风险雷达'}")
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        if s['_short_val'] > 5:
                            st.error(f"⚠️ **{'High Short Interest' if lang_choice=='EN' else '高空头预警'}**\n\n{'Shorts at' if lang_choice=='EN' else '做空率达'} {s['_short_val']:.1f}%。{'Bears are aggressive. Possible short ladder attack.' if lang_choice=='EN' else '空头正在集结。若无重大利好，股价压力极大。'}")
                        else: st.success(f"✅ **{'Low Shorting Risk' if lang_choice=='EN' else '做空风险极低'}**\n\n{'Institutional support is stable.' if lang_choice=='EN' else '筹码分布稳定，没有大规模做空迹象。'}")
                    with col_r2:
                        if s['_price_val'] < s['_ma200_val']:
                            st.error(f"❌ **{'Bearish Trend' if lang_choice=='EN' else '趋势性破位' }**\n\n{'Price is below MA200. This is a \"bottom-fishing\" play with high risk.' if lang_choice=='EN' else '股价处于 200 日均线下方，属于典型的左侧交易，小心阴跌。'}")
                        else: st.success(f"📈 **{'Bullish Trend' if lang_choice=='EN' else '趋势多头排列'}**\n\n{'Price above MA200. Momentum is on your side.' if lang_choice=='EN' else '股价站稳牛熊分界线，属于右侧强势区间。'}")

                    # 第二部分：核心财务分析 (Deep Fundamentals)
                    st.markdown("---")
                    st.markdown(f"### 🏛️ {'Fundamental Quality' if lang_choice=='EN' else '基本面护城河深度评估'}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(f"{'PEG Ratio' if lang_choice=='EN' else '估值性价比'}", f"{s[t['col_pe']]} / {s[t['col_peg']]}")
                        st.caption("PEG < 1 indicates growth is cheaper than its price." if lang_choice=='EN' else "PEG 小于 1 意味着你正在以低于增长的速度买入。")
                    with c2:
                        st.metric(f"{'ROE Efficiency' if lang_choice=='EN' else '资本回报率'}", f"{s[t['col_roe']]}%")
                        st.caption("Reflects management's ability to generate profit." if lang_choice=='EN' else "反映管理层利用股东资本创造利润的高效率。")
                    with c3:
                        st.metric(f"{'FCF Surplus' if lang_choice=='EN' else '自由现金流'}", f"${s[t['col_fcf']]}B")
                        st.caption("The true 'Gasoline' for dividends and buybacks." if lang_choice=='EN' else "公司分红、回购和抗御风险的真正硬通货。")

                    # 第三部分：技术与量能研判 (Technical Matrix)
                    st.markdown(f"### 📈 {'Momentum Matrix' if lang_choice=='EN' else '技术与量能研判矩阵'}")
                    v_ratio = s['_vol_val']
                    v_status = "🔥 巨量突破" if v_ratio > 50 else ("💤 缩量盘整" if v_ratio < -30 else "稳定换手")
                    st.write(f"· **{'Relative Volume' if lang_choice=='EN' else '量能状态'}**: `{s[t['col_vol_ratio']]}` — {v_status}")
                    st.write(f"· **{'RSI Momentum' if lang_choice=='EN' else '相对强弱'}**: `{s[t['col_rsi']]}` — {'超卖(反弹预警)' if s[t['col_rsi']] < 30 else '强势偏热' if s[t['col_rsi']] > 70 else '中性偏稳'}")
                    st.write(f"· **{'MACD Status' if lang_choice=='EN' else '趋势信号'}**: `{s[t['col_macd']]}`")

                    # 第四部分：Issac 终极投资结论 (Final Verdict)
                    st.divider()
                    score = 0
                    if s[t['col_peg']] < 0.7: score += 1
                    if s[t['col_roe']] > 25: score += 1
                    if s['_price_val'] > s['_ma200_val']: score += 1
                    
                    verdicts = {
                        3: ("STRONG BUY (A+)", "强力买入 (A+)", "基本面无懈可击，且趋势已确立，适合重仓逻辑。"),
                        2: ("BUY ON DIPS (A)", "回调买入 (A)", "优质资产，但当前位置可能存在震荡，建议分批分仓。"),
                        1: ("SPECULATIVE HOLD (B)", "投机性持有 (B)", "估值便宜但趋势偏弱，建议设好止损，轻仓博反弹。"),
                        0: ("AVOID (C)", "暂时观望 (C)", "尽管看起来便宜，但量价极度背离，等待企稳信号。")
                    }
                    v_en, v_cn, v_desc = verdicts.get(score, verdicts[1])
                    st.success(f"🏆 **{'Final Verdict' if lang_choice=='EN' else '最终投资建议'}: {v_en if lang_choice=='EN' else v_cn}**")
                    st.info(v_desc if lang_choice=='CN' else "Fundamentals are solid, but follow technical signals for entry.")

        # 展示主表格
        st.dataframe(df[display_cols] if st.checkbox(t["matching_only"], value=True) else df[display_cols], use_container_width=True, height=500, hide_index=True)
