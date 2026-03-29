import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone
from lang_config import LANG 

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# 顶层快照白名单
WHITE_LIST = ["Symbol", "Price", "MA200", "ROE%", "Inst%", "P/E", "PEG", "Match"]

# --- 2. 侧边栏 ---
st.sidebar.header(t.get("sidebar_header"))
search_ticker = st.sidebar.text_input(t.get("search_label"), "").upper().strip()
st.sidebar.divider()
t_pe, t_peg = st.sidebar.number_input(t.get("pe_label"), value=25.0), st.sidebar.number_input(t.get("peg_label"), value=1.2)
m_roe, m_fcf = st.sidebar.number_input(t.get("roe_label"), value=15.0), st.sidebar.number_input(t.get("fcf_label"), value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t.get("scan_range"), ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t.get("scan_btn"))

# --- 🎯 3. 分析引擎 (财报抓取深度强化) ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if h.empty or len(h) < 200: return None
        inf = tk.info
        p = h['Close'].iloc[-1]
        m200_val = h['Close'].rolling(200).mean().iloc[-1]
        
        # 基础财务
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        inst = (inf.get('heldPercentInstitutions') or 0) * 100
        cash, debt = (inf.get('totalCash') or 0)/1e9, (inf.get('totalDebt') or 0)/1e9
        
        # 估值水位
        pe_curr = inf.get('forwardPE') or inf.get('trailingPE', 0)
        pe_pct = "N/A"
        try:
            hist_pe = h['Close'] / inf.get('trailingEps', 1)
            pe_pct = round((hist_pe < pe_curr).mean() * 100, 1)
        except: pass

        # 🧩 深度 ROE 审计
        prev_roe = "N/A"
        try:
            y_fin, y_bs = tk.get_financials(), tk.get_balance_sheet()
            if not y_fin.empty and not y_bs.empty:
                # 优先对比上两个财年，避开 TTM 的干扰
                idx = 1 if len(y_fin.columns) > 1 else 0
                prev_roe = round((y_fin.loc['Net Income'].iloc[idx] / y_bs.loc['Stockholders Equity'].iloc[idx]) * 100, 1)
        except: pass

        # 🎯 🧩 核心修复：财报雷达多重探测逻辑
        n_date, n_days, p_date, p_act, p_est, p_surp = "N/A", 999, "N/A", "N/A", "N/A", "N/A"
        
        try:
            # 路径 A: 尝试获取最新财报表
            e_table = tk.get_earnings_dates(limit=12)
            if e_table is not None and not e_table.empty:
                # 转换索引为统一的 UTC 时间戳
                e_table.index = pd.to_datetime(e_table.index).tz_convert('UTC')
                now_utc = datetime.now(timezone.utc)
                
                # 寻找未来的财报日
                fut = e_table[e_table.index > now_utc].sort_index()
                if not fut.empty:
                    n_date = fut.index[0].strftime('%Y-%m-%d')
                    n_days = (fut.index[0] - now_utc).days
                
                # 寻找上一个财报表现
                pst = e_table[e_table.index <= now_utc].sort_index(ascending=False)
                if not pst.empty:
                    p_date = pst.index[0].strftime('%Y-%m-%d')
                    p_act = pst['Reported EPS'].iloc[0]
                    p_est = pst['EPS Estimate'].iloc[0]
                    # 有些列名可能是 'Surprise(%)'
                    if 'Surprise(%)' in pst.columns:
                        p_surp = round(pst['Surprise(%)'].iloc[0] * 100, 1) if pst['Surprise(%)'].iloc[0] < 1 else round(pst['Surprise(%)'].iloc[0], 1)
                    elif pd.notnull(p_act) and pd.notnull(p_est) and p_est != 0:
                        p_surp = round(((p_act / p_est) - 1) * 100, 1)

            # 路径 B: 如果 n_date 还是 N/A，尝试 tk.calendar
            if n_date == "N/A":
                cal = tk.calendar
                if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
                    c_date = cal.loc['Earnings Date'].iloc[0]
                    n_date = c_date.strftime('%Y-%m-%d')
                    n_days = (pd.to_datetime(c_date).tz_localize(None) - datetime.now()).days
        except: pass

        # RS 相对强度
        s_ret, spy_ret = 0, 0
        try:
            spy_tk = yf.Ticker("^GSPC")
            h_3m, h_spy_3m = tk.history(period="3mo"), spy_tk.history(period="3mo")
            s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
            spy_ret = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
        except: pass

        return {
            "Symbol": s, "Price": round(p, 2), "MA200": round(m200_val, 2), "Match": "✅" if ok else "❌",
            "P/E": pe_curr, "PEG": round(peg, 4), "ROE%": round(roe, 1), "Inst%": f"{inst:.1f}%",
            "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), "Upside": f"{((inf.get('targetMeanPrice', p)/p)-1)*100:+.1f}%",
            "_p": p, "_m": m200_val, "_h": h, "_m_s": h['Close'].rolling(200).mean(), "_target": inf.get('targetMeanPrice'),
            "_inst": inst, "_cash": cash, "_debt": debt, "_pe_pct": pe_pct,
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_n_e": n_date, "_n_d": n_days,
            "_p_e": p_date, "_p_act": p_act, "_p_est": p_est, "_p_s": p_surp,
            "_prev_roe": prev_roe, "_fcf_m": ((inf.get('freeCashflow', 0) / inf.get('totalRevenue', 1)) * 100),
            "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

def render_report(s):
    # 🚨 1. 快照与动能图
    st.markdown(f"## {t.get('snapshot_title')} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t.get('chart_close'), line=dict(color='#00d1ff', width=2)))
        fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t.get('chart_ma200'), line=dict(color='#ffaa00', width=2, dash='dash')))
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=1
