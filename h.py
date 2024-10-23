# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import yfinance as yf
from datetime import date, datetime, timedelta

# 設定頁面配置
st.set_page_config(
    page_title="邦的股市回測系統",
    layout="wide"
)

# 標題
st.title('📈 邦的股市回測系統')

# 功能函數
def load_stock_data(stock_list, start_date, end_date):
    data_frames = []
    for stock in stock_list:
        # yfinance 中，台灣股票代碼需要加上 ".TW"
        ticker = f"{stock}.TW"
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty:
                st.warning(f"無法下載股票代碼為 {stock} 的資料，數據為空。")
            else:
                # 使用調整後的收盤價
                df = df[['Adj Close']].dropna()
                df.rename(columns={'Adj Close': stock}, inplace=True)
                data_frames.append(df)
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
    # 計算累積收益（百分比），保留兩位小數
    cumulative_returns = ((price_data / price_data.iloc[0] - 1) * 100).round(2)
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
    start_date = st.date_input('選擇開始日期', value=date(2023, 1, 1))
    end_date = st.date_input('選擇結束日期', value=date(2024, 10, 23))
    if start_date > end_date:
        st.error('開始日期不能晚於結束日期')

    # 可選股票列表，包括 ETF
    stock_options = ['2330', '2317', '2412', '1301', '2308', '0050', '0056']
    # 選擇策略股票
    strategy_stocks = st.multiselect(
        '選擇組合策略的股票（至少選擇一支）',
        stock_options,
        default=['2330']
    )

    # 讓使用者輸入比較的股票代號
    benchmark_stock = st.text_input('輸入比較的股票代號', value='0050')

    # 複利計算機選項
    st.subheader("複利計算機")
    use_compound = st.checkbox('使用複利計算機')

    if use_compound:
        initial_capital = st.number_input('初始資金（元）', min_value=0, value=10000)
        monthly_investment = st.number_input('每月投入（元）', min_value=0, value=1000)
        # 移除目標資產的輸入
        # target_amount = st.number_input('目標資產（元）', min_value=0, value=1000000)

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
            yaxis=dict(tickformat='.2f%', showgrid=True),  # 顯示兩位小數，並添加百分比符號
            legend=dict(x=0, y=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 移除數據表格顯示
        # st.subheader("數據表格")
        # st.dataframe(comparison_df)

        # 如果使用複利計算機，進行計算
        if use_compound:
            # 計算投資期間的年數
            total_days = (end_date - start_date).days
            years = total_days / 365.25

            # 計算策略組合的年化報酬率
            strategy_total_return = strategy_performance.iloc[-1] / 100  # 百分比轉換為小數
            strategy_annual_return = (1 + strategy_total_return) ** (1 / years) - 1

            # 計算月收益率和總月數
            r_monthly = strategy_annual_return / 12
            n_months = years * 12

            # 建立時間軸
            dates = [start_date + timedelta(days=30*i) for i in range(int(n_months)+1)]
            if dates[-1] > end_date:
                dates[-1] = end_date

            # 計算每個月的資產增長
            total_capital = []
            for i in range(len(dates)):
                # 初始資金增長
                FV_initial = initial_capital * (1 + r_monthly) ** i
                # 每月投入增長
                if r_monthly != 0:
                    FV_monthly = monthly_investment * (( (1 + r_monthly) ** i - 1) / r_monthly)
                else:
                    FV_monthly = monthly_investment * i
                total = FV_initial + FV_monthly
                total_capital.append(total)

            # 繪製資產增長圖表
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dates, y=total_capital,
                mode='lines+markers', name='總資產'
            ))
            fig2.update_layout(
                title='資產增長圖',
                xaxis_title='日期',
                yaxis_title='資產總額（元）',
                hovermode='x unified',
                legend=dict(x=0, y=1)
            )
            st.plotly_chart(fig2, use_container_width=True)

            # 顯示最終結果
            final_capital = total_capital[-1]

            st.subheader("複利計算結果")
            st.write(f"策略投資累積漲幅：約 {strategy_total_return * 100:.2f}%")
            st.write(f"年化報酬率：約 {strategy_annual_return * 100:.2f}%")
            st.write(f"投資 {years:.2f} 年後的預期資產：約 {final_capital:,.0f} 元")

    else:
        st.error("資料加載或處理失敗，請檢查您的股票代碼。")
else:
    st.info("請在左側選擇策略股票和比較的股票代號，並確保開始日期早於結束日期。")
