# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import yfinance as yf
from datetime import date

# 設定頁面配置
st.set_page_config(
    page_title="台灣股市回測系統",
    layout="wide"
)

# 標題
st.title('📈 台灣股市回測系統')

# 功能函數
def load_stock_data(stock_list, start_date, end_date):
    data_frames = []
    for stock in stock_list:
        # yfinance 中，台灣股票代碼需要加上 ".TW"
        ticker = f"{stock}.TW"
        st.write(f"正在下載股票代碼為 {stock} 的資料...")
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                st.warning(f"無法下載股票代碼為 {stock} 的資料，數據為空。")
            else:
                df = df[['Close']].dropna()
                df.rename(columns={'Close': stock}, inplace=True)
                data_frames.append(df)
                st.write(f"成功下載 {stock} 的資料，共有 {len(df)} 條記錄。")
        except Exception as e:
            st.warning(f"下載股票代碼為 {stock} 的資料時出現錯誤: {e}")
    if data_frames:
        # 合併所有 DataFrame，按照日期索引對齊
        combined_df = pd.concat(data_frames, axis=1)
        return combined_df
    else:
        return pd.DataFrame()  # 返回空的 DataFrame

def calculate_cumulative_returns(price_data):
    if price_data.empty:
        st.error("價格數據為空，無法計算累積收益。")
        return pd.Series(dtype='float64')
    # 計算累積收益（百分比），並轉換為整數
    cumulative_returns = ((price_data / price_data.iloc[0] - 1) * 100).round(0).astype(int)
    return cumulative_returns

def load_and_process_data(strategy_stocks, benchmark_stock, start_date, end_date):
    strategy_data = load_stock_data(strategy_stocks, start_date, end_date)
    benchmark_data = load_stock_data([benchmark_stock], start_date, end_date)
    if strategy_data.empty:
        st.error("策略股票的資料為空，請檢查股票代碼或數據來源。")
        return None, None
    if benchmark_data.empty:
        st.error("基準股票的資料為空，請檢查股票代碼或數據來源。")
        return None, None
    # 計算策略組合的平均價格
    strategy_price = strategy_data.mean(axis=1)
    # 計算累積收益
    strategy_cumulative_returns = calculate_cumulative_returns(strategy_price)
    benchmark_cumulative_returns = calculate_cumulative_returns(benchmark_data.iloc[:, 0])
    return strategy_cumulative_returns, benchmark_cumulative_returns

# 側邊欄選項
with st.sidebar:
    st.header("選項設定")
    # 日期選擇器
    start_date = st.date_input('選擇開始日期', value=date(2010, 1, 1))
    end_date = st.date_input('選擇結束日期', value=date.today())
    if start_date > end_date:
        st.error('開始日期不能晚於結束日期')

    # 可選股票列表，包括 ETF
    stock_options = ['2330', '2317', '2412', '1301', '2308', '0050', '0056']
    # 選擇策略股票
    strategy_stocks = st.multiselect(
        '選擇組合策略的股票（至少選擇一支）',
        stock_options,
        default=['2330', '2317']
    )

    # 選擇基準股票
    benchmark_stock = st.selectbox(
        '選擇比較的股票',
        stock_options  # 使用相同的股票選項，包括 ETF
    )

    # 複利計算機選項
    st.subheader("複利計算機")
    use_compound = st.checkbox('使用複利計算機')

    if use_compound:
        initial_capital = st.number_input('初始資金（元）', min_value=0, value=100000)
        monthly_investment = st.number_input('每月投入（元）', min_value=0, value=10000)
        target_amount = st.number_input('目標資產（元）', min_value=0, value=1000000)

# 主體內容
if strategy_stocks and benchmark_stock and start_date <= end_date:
    # 加載和處理資料
    strategy_performance, benchmark_performance = load_and_process_data(strategy_stocks, benchmark_stock, start_date, end_date)

    if strategy_performance is not None and benchmark_performance is not None and not strategy_performance.empty and not benchmark_performance.empty:
        # 對齊日期索引
        combined_index = strategy_performance.index.intersection(benchmark_performance.index)
        strategy_performance = strategy_performance.loc[combined_index]
        benchmark_performance = benchmark_performance.loc[combined_index]

        # 合併資料
        comparison_df = pd.DataFrame({
            '策略組合': strategy_performance,
            benchmark_stock: benchmark_performance
        })

        # 將日期索引轉換為日期格式
        comparison_df.index = comparison_df.index.date

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
            title='策略組合與基準股票的累積漲幅比較',
            xaxis_title='日期',
            yaxis_title='累積漲幅（%）',
            hovermode='x unified',
            yaxis=dict(tickformat=',d'),  # 去除小數點，顯示整數
            legend=dict(x=0, y=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 顯示數據表格
        comparison_df.reset_index(inplace=True)
        comparison_df.rename(columns={'index': '日期'}, inplace=True)
        st.subheader("數據表格")
        st.dataframe(comparison_df)

        # 如果使用複利計算機，進行計算
        if use_compound:
            # 計算投資期間的年數
            total_days = (end_date - start_date).days
            years = total_days / 365.25

            # 計算年化報酬率
            total_return = strategy_performance.iloc[-1] / 100  # 百分比轉換為小數
            annual_return = (1 + total_return) ** (1 / years) - 1

            # 計算最終資產
            # 未來價值 FV = PV * (1 + r) ^ n + PMT * [((1 + r) ^ n - 1) / r]
            n = years * 1  # 每年複利一次
            r = annual_return
            if r != 0:
                future_value = initial_capital * (1 + r) ** n + monthly_investment * 12 * [((1 + r) ** n - 1) / r]
            else:
                future_value = initial_capital + monthly_investment * 12 * n

            st.subheader("複利計算結果")
            st.write(f"年化報酬率：約 {annual_return * 100:.2f}%")
            st.write(f"投資 {years:.2f} 年後的預期資產：約 {future_value:,.0f} 元")
    else:
        st.error("資料加載或處理失敗，請檢查您的股票代碼。")
else:
    st.info("請在左側選擇策略股票和基準股票，並確保開始日期早於結束日期。")
