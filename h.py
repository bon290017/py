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
        '投資組合（至少選一支股票）',
        stock_options,
        default=['2330']
    )

    # 讓使用者輸入比較的股票代號
    benchmark_stock = st.text_input('輸入比較的股票', value='0050')

    # 複利計算機選項
    st.subheader("複利計算機")
    use_compound = st.checkbox('使用複利計算機')

    if use_compound:
        initial_capital = st.number_input('初始資金（元）', min_value=0, value=10000)
        monthly_investment = st.number_input('每月投入（元）', min_value=0, value=1000)

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
            yaxis=dict(tickformat='.2f%', showgrid=True),
            legend=dict(x=0, y=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 如果使用複利計算機，進行計算
        if use_compound:
            # 計算投資期間的年數
            total_days = (end_date - start_date).days
            years = total_days / 365.25

            # 計算策略組合的年化報酬率
            strategy_total_return = strategy_performance.iloc[-1] / 100  # 百分比轉換為小數
            strategy_annual_return = (1 + strategy_total_return) ** (1 / years) - 1

            # 計算基準股票的年化報酬率
            benchmark_total_return = benchmark_performance.iloc[-1] / 100  # 百分比轉換為小數
            benchmark_annual_return = (1 + benchmark_total_return) ** (1 / years) - 1

            # 計算月收益率和總月數
            strategy_r_monthly = strategy_annual_return / 12
            benchmark_r_monthly = benchmark_annual_return / 12
            n_months = int(years * 12)

            # 建立時間軸
            dates = [start_date + timedelta(days=30*i) for i in range(n_months+1)]
            if dates[-1] > end_date:
                dates[-1] = end_date

            # 計算策略組合的總資產、本金和收益
            strategy_total_capital = []
            strategy_principal = []
            strategy_interest = []
            for i in range(len(dates)):
                # 初始資金增長
                FV_initial = initial_capital * (1 + strategy_r_monthly) ** i
                # 每月投入增長
                if strategy_r_monthly != 0:
                    FV_monthly = monthly_investment * (((1 + strategy_r_monthly) ** i - 1) / strategy_r_monthly)
                else:
                    FV_monthly = monthly_investment * i
                total = FV_initial + FV_monthly
                principal = initial_capital + monthly_investment * i
                interest = total - principal
                strategy_total_capital.append(total)
                strategy_principal.append(principal)
                strategy_interest.append(interest)

            # 計算基準股票的總資產、本金和收益
            benchmark_total_capital = []
            benchmark_principal = []
            benchmark_interest = []
            for i in range(len(dates)):
                # 初始資金增長
                FV_initial = initial_capital * (1 + benchmark_r_monthly) ** i
                # 每月投入增長
                if benchmark_r_monthly != 0:
                    FV_monthly = monthly_investment * (((1 + benchmark_r_monthly) ** i - 1) / benchmark_r_monthly)
                else:
                    FV_monthly = monthly_investment * i
                total = FV_initial + FV_monthly
                principal = initial_capital + monthly_investment * i
                interest = total - principal
                benchmark_total_capital.append(total)
                benchmark_principal.append(principal)
                benchmark_interest.append(interest)

            # 建立資料表
            growth_df = pd.DataFrame({
                '日期': dates,
                '策略組合本金': strategy_principal,
                '策略組合收益': strategy_interest,
                f'{benchmark_stock} 本金': benchmark_principal,
                f'{benchmark_stock} 收益': benchmark_interest
            })

            # 格式化資料表，去除小數點
            growth_df_display = growth_df.copy()
            cols_to_round = ['策略組合本金', '策略組合收益', f'{benchmark_stock} 本金', f'{benchmark_stock} 收益']
            growth_df_display[cols_to_round] = growth_df_display[cols_to_round].round(0).astype(int)

            # 顯示資料表
            st.subheader("收益資料表")
            st.dataframe(growth_df_display)

            # **在這裡進行修改，確保收益比較圖不顯示小數點**

            # 將用於繪圖的資料也進行四捨五入，轉換為整數
            plot_growth_df = growth_df.copy()
            plot_growth_df[cols_to_round] = plot_growth_df[cols_to_round].round(0).astype(int)

            # 繪製收益比較圖，包含本金
            fig2 = go.Figure()

            # 策略組合
            fig2.add_trace(go.Bar(
                x=plot_growth_df['日期'],
                y=plot_growth_df['策略組合本金'],
                name='策略組合本金',
                marker_color='lightblue',
                text=plot_growth_df['策略組合本金'],
                textposition='auto'
            ))
            fig2.add_trace(go.Bar(
                x=plot_growth_df['日期'],
                y=plot_growth_df['策略組合收益'],
                name='策略組合收益',
                marker_color='blue',
                text=plot_growth_df['策略組合收益'],
                textposition='auto'
            ))

            # 基準股票
            fig2.add_trace(go.Bar(
                x=plot_growth_df['日期'],
                y=plot_growth_df[f'{benchmark_stock} 本金'],
                name=f'{benchmark_stock} 本金',
                marker_color='lightgreen',
                text=plot_growth_df[f'{benchmark_stock} 本金'],
                textposition='auto'
            ))
            fig2.add_trace(go.Bar(
                x=plot_growth_df['日期'],
                y=plot_growth_df[f'{benchmark_stock} 收益'],
                name=f'{benchmark_stock} 收益',
                marker_color='green',
                text=plot_growth_df[f'{benchmark_stock} 收益'],
                textposition='auto'
            ))

            fig2.update_layout(
                barmode='group',  # 分組顯示
                title='收益比較圖',
                xaxis_title='日期',
                yaxis_title='資產（元）',
                hovermode='x unified',
                legend=dict(x=0, y=1),
                yaxis_tickformat=',',  # 數字不顯示科學記號或縮寫
            )

            st.plotly_chart(fig2, use_container_width=True)

            # 顯示最終結果，使用表格形式
            result_df = pd.DataFrame({
                '項目': ['策略組合', f'基準股票（{benchmark_stock}）'],
                '累積漲幅（%）': [f"{strategy_total_return * 100:.2f}%", f"{benchmark_total_return * 100:.2f}%"],
                '年化報酬率（%）': [f"{strategy_annual_return * 100:.2f}%", f"{benchmark_annual_return * 100:.2f}%"],
            })

            st.subheader("複利計算結果比較")
            st.table(result_df)

    else:
        st.error("資料加載或處理失敗，請檢查您的股票代碼。")
else:
    st.info("請在左側選擇投資組合和比較的股票，並確保開始日期早於結束日期。")
