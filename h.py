import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
from matplotlib.font_manager import FontProperties
import os

# 設置應用標題
st.title("多股票回測系統")

# 說明文字
st.write("""
    請輸入多支台灣股市代號，並選擇一支基準股票進行回測比較。
    您可以輸入多支股票代號，使用逗號分隔，例如：2330,2317,2412
""")

# 使用者輸入
symbols_input = st.text_input("請輸入多支台灣股市代號（用逗號分隔）:", "2330,2317,2412")
benchmark_input = st.text_input("請輸入用於對比的台灣股市代號:", "0050")

# 新增日期選擇功能，標籤使用中文
st.write("### 選擇回測的日期範圍")
default_end_date = datetime.today()
default_start_date = default_end_date - timedelta(days=730)  # 預設過去兩年

start_date = st.date_input("開始日期", default_start_date)
end_date = st.date_input("結束日期", default_end_date)

# 確保開始日期不晚於結束日期
if start_date > end_date:
    st.error("開始日期不能晚於結束日期。請重新選擇日期。")

# 按鈕觸發回測
if st.button("開始回測"):
    # 處理股票代號輸入，替換全角逗號為半角逗號，並分割
    symbols_list = [symbol.strip() + ".TW" for symbol in symbols_input.replace('，', ',').split(",")]

    # 處理基準股票代號
    benchmark_symbol = benchmark_input.strip() + ".TW"

    # 定義日期範圍（根據使用者選擇）
    end_date_dt = datetime.combine(end_date, datetime.min.time())
    start_date_dt = datetime.combine(start_date, datetime.min.time())

    # 下載所有股票的歷史數據
    portfolio_data = yf.download(
        symbols_list,
        start=start_date_dt.strftime('%Y-%m-%d'),
        end=end_date_dt.strftime('%Y-%m-%d'),
        group_by='ticker'
    )

    if portfolio_data.empty:
        st.error("未能獲取到任何有效的投資組合股票數據。請檢查股票代號並重試。")
    else:
        # 提取 'Close' 價格
        pivot_close = portfolio_data['Close']
        # 處理缺失值
        pivot_close = pivot_close.ffill().dropna()
        # 計算每日收益率
        returns = pivot_close.pct_change()
        # 計算組合的平均每日收益率（等權重）
        portfolio_returns = returns.mean(axis=1)

        # 獲取基準股票的歷史數據
        benchmark_data = yf.download(
            benchmark_symbol,
            start=start_date_dt.strftime('%Y-%m-%d'),
            end=end_date_dt.strftime('%Y-%m-%d')
        )

        if benchmark_data is not None and not benchmark_data.empty:
            # 計算基準股票的每日收益率
            benchmark_returns = benchmark_data['Close'].pct_change()

            # 對齊日期索引
            portfolio_returns = portfolio_returns.loc[benchmark_returns.index]
            benchmark_returns = benchmark_returns.loc[portfolio_returns.index]

            # 處理缺失值
            portfolio_returns = portfolio_returns.fillna(0)
            benchmark_returns = benchmark_returns.fillna(0)

            # 計算累積收益
            portfolio_cumulative_returns = (1 + portfolio_returns).cumprod() - 1
            benchmark_cumulative_returns = (1 + benchmark_returns).cumprod() - 1

            # 準備 Plotly 圖表
            fig = go.Figure()

            # 添加投資組合累積收益曲線
            fig.add_trace(go.Scatter(
                x=portfolio_cumulative_returns.index,
                y=portfolio_cumulative_returns.values,
                mode='lines',
                name='投資組合累積收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累積收益: %{y:.2%}<extra></extra>'
            ))

            # 添加基準股票累積收益曲線
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative_returns.index,
                y=benchmark_cumulative_returns.values,
                mode='lines',
                name=f'{benchmark_input} 累積收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累積收益: %{y:.2%}<extra></extra>'
            ))

            # 設置圖表布局
            fig.update_layout(
                title='投資組合與基準股票累積收益對比',
                xaxis_title='日期',
                yaxis_title='累積收益',
                hovermode='x unified',
                template='plotly_white'
            )

            # 設置 Y 軸為百分比格式
            fig.update_yaxes(tickformat=".2%")

            # 顯示 Plotly 圖表
            st.plotly_chart(fig, use_container_width=True)

            # 繪製基準股票的 K 線圖
            fig_candlestick = go.Figure(data=[go.Candlestick(
                x=benchmark_data.index,
                open=benchmark_data['Open'],
                high=benchmark_data['High'],
                low=benchmark_data['Low'],
                close=benchmark_data['Close'],
                name=f'{benchmark_input} K 線',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '開盤價: %{open}<br>' +
                    '最高價: %{high}<br>' +
                    '最低價: %{low}<br>' +
                    '收盤價: %{close}<extra></extra>'
            )])

            fig_candlestick.update_layout(
                title=f'{benchmark_input} K 線圖',
                xaxis_title='日期',
                yaxis_title='價格',
                template='plotly_white'
            )

            st.plotly_chart(fig_candlestick, use_container_width=True)

            # 計算總收益
            total_portfolio_return = portfolio_cumulative_returns.iloc[-1]
            total_benchmark_return = benchmark_cumulative_returns.iloc[-1]

            # 顯示回測結果
            st.write(f"**投資組合總收益:** {total_portfolio_return * 100:.2f}%")
            st.write(f"**{benchmark_input} 總收益:** {total_benchmark_return * 100:.2f}%")

            # 計算每月獲利百分比
            portfolio_monthly = portfolio_cumulative_returns.resample('M').last().pct_change().dropna() * 100
            benchmark_monthly = benchmark_cumulative_returns.resample('M').last().pct_change().dropna() * 100

            # 合併數據
            monthly_returns_df = pd.DataFrame({
                '日期': portfolio_monthly.index.strftime('%Y-%m'),
                '投資組合月獲利%': portfolio_monthly.values,
                f'{benchmark_input} 月獲利%': benchmark_monthly.values
            })

            # 顯示每月獲利數據表
            st.write("### 每月獲利百分比比較")
            st.dataframe(monthly_returns_df.style.format({
                '投資組合月獲利%': "{:.2f}",
                f'{benchmark_input} 月獲利%': "{:.2f}"
            }))
        else:
            st.error(f"無法取得基準股票 {benchmark_input} 的資料。請檢查股票代號是否正確或該股票是否已退市。")
