# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import os

# 設定頁面配置
st.set_page_config(
    page_title="台灣股市回測系統",
    layout="wide"
)

# 標題
st.title('📈 台灣股市回測系統')

# 功能函數
def load_stock_data(stock_list):
    data = {}
    for stock in stock_list:
        file_path = f'data/{stock}.csv'  # 請確保資料存放在 data 資料夾中
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
            data[stock] = df['Close']
        else:
            st.warning(f"找不到股票代碼為 {stock} 的資料檔案。")
    return pd.DataFrame(data)

def calculate_strategy_performance(strategy_data):
    # 計算每日報酬率
    returns = strategy_data.pct_change().dropna()
    # 假設等權重投資
    strategy_returns = returns.mean(axis=1)
    # 計算累積報酬率
    cumulative_returns = (1 + strategy_returns).cumprod()
    return cumulative_returns

def load_and_process_data(strategy_stocks, benchmark_stock):
    strategy_data = load_stock_data(strategy_stocks)
    benchmark_data = load_stock_data([benchmark_stock])
    if strategy_data.empty or benchmark_data.empty:
        st.error("無法加載策略股票或基準股票的資料。")
        return None, None
    strategy_performance = calculate_strategy_performance(strategy_data)
    benchmark_performance = calculate_strategy_performance(benchmark_data)
    return strategy_performance, benchmark_performance

# 側邊欄選項
with st.sidebar:
    st.header("選項設定")
    # 選擇策略股票
    strategy_stocks = st.multiselect(
        '選擇組合策略的股票（至少選擇一支）',
        ['2330', '2317', '2412', '1301', '2308'],  # 請替換為您關心的股票代碼
        default=['2330', '2317']
    )

    # 選擇基準股票
    benchmark_stock = st.selectbox(
        '選擇比較的股票',
        ['0050', '0056', '2330']  # 常用的基準，如 ETF 或大型權值股
    )

# 主體內容
if strategy_stocks and benchmark_stock:
    # 加載和處理資料
    strategy_performance, benchmark_performance = load_and_process_data(strategy_stocks, benchmark_stock)

    if strategy_performance is not None and benchmark_performance is not None:
        # 合併資料
        comparison_df = pd.DataFrame({
            '策略組合': strategy_performance,
            benchmark_stock: benchmark_performance
        })

        # 繪製互動式圖表
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=comparison_df.index, y=comparison_df['策略組合'],
            mode='lines', name='策略組合'
        ))
        fig.add_trace(go.Scatter(
            x=comparison_df.index, y=comparison_df[benchmark_stock],
            mode='lines', name=benchmark_stock
        ))
        fig.update_layout(
            title='策略組合與基準股票的績效比較',
            xaxis_title='日期',
            yaxis_title='累積報酬率',
            hovermode='x unified',
            legend=dict(x=0, y=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 顯示數據表格
        st.subheader("數據表格")
        st.dataframe(comparison_df)
    else:
        st.error("資料加載失敗，請檢查您的股票代碼和資料檔案。")
else:
    st.info("請在左側選擇策略股票和基準股票。")
