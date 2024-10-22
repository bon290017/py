import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
import os

# 设置支持中文的字体（如果需要在其他图表中使用）
def get_font_properties(font_size=12):
    font_path = os.path.join("fonts", "NotoSansTC-SemiBold.ttf")
    if os.path.exists(font_path):
        try:
            from matplotlib.font_manager import FontProperties
            font_prop = FontProperties(fname=font_path, size=font_size)
            return font_prop
        except Exception as e:
            st.warning(f"加载字体时出错：{e}。将使用默认字体。")
            return None
    else:
        st.warning("未找到自定义中文字体文件。将使用默认字体。")
        return None

# 设置应用标题
st.title("多股票回测系统")

# 说明文字
st.write("""
    请输入多支台湾股市代号，并选择一支基准股票进行回测比较。
    您可以输入多支股票代号，使用逗号分隔，例如：2330,2317,2412
""")

# 用户输入
symbols_input = st.text_input("请输入多支台湾股市代号（用逗号分隔）:", "2330,2317,2412")
benchmark_input = st.text_input("请输入用于对比的台湾股市代号:", "0050")

# 新增日期选择功能，标签使用中文
st.write("### 选择回测的日期范围")
default_end_date = datetime.today()
default_start_date = default_end_date - timedelta(days=730)  # 默认过去两年

start_date = st.date_input("开始日期", default_start_date)
end_date = st.date_input("结束日期", default_end_date)

# 确保开始日期不晚于结束日期
if start_date > end_date:
    st.error("开始日期不能晚于结束日期。请重新选择日期。")

# 按钮触发回测
if st.button("开始回测"):
    # 获取字体属性（如果需要）
    font_prop = get_font_properties()

    # 定义函数以获取单个股票的历史数据
    def fetch_stock_data(symbol, start_date, end_date):
        try:
            stock = yf.download(symbol, start=start_date, end=end_date)
            if stock.empty:
                st.warning(f"未能获取到 {symbol} 的数据。请检查股票代号是否正确或该股票是否已退市。")
                return None
            stock['Symbol'] = symbol
            return stock
        except Exception as e:
            st.error(f"获取 {symbol} 数据时出错。错误信息：{e}")
            return None

    # 处理股票代号输入，替换全角逗号为半角逗号，并分割
    symbols_list = [symbol.strip() + ".TW" for symbol in symbols_input.replace('，', ',').split(",")]

    # 处理基准股票代号
    benchmark_symbol = benchmark_input.strip() + ".TW"

    # 定义日期范围（根据用户选择）
    end_date_dt = datetime.combine(end_date, datetime.min.time())
    start_date_dt = datetime.combine(start_date, datetime.min.time())

    # 获取多支股票的历史数据
    portfolio_data_list = []

    for symbol in symbols_list:
        data = fetch_stock_data(symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))
        if data is not None:
            portfolio_data_list.append(data)

    # 检查是否有有效的数据
    if not portfolio_data_list:
        st.error("未能获取到任何有效的投资组合股票数据。请检查股票代号并重试。")
    else:
        # 使用 pd.concat 合并所有股票的数据
        portfolio_data = pd.concat(portfolio_data_list)
        portfolio_data.reset_index(inplace=True)
        portfolio_data.rename(columns={'Date': 'Date'}, inplace=True)  # 确保日期列名为 'Date'

        # 确保 'Date' 列是 datetime 类型
        portfolio_data['Date'] = pd.to_datetime(portfolio_data['Date'])

        # 删除关键列中的缺失值
        portfolio_data.dropna(subset=['Date', 'Symbol', 'Close'], inplace=True)

        # 使用 pivot_table 并指定聚合函数
        pivot_close = portfolio_data.pivot_table(index='Date', columns='Symbol', values='Close', aggfunc='mean')

        # 处理缺失值（如有）
        pivot_close = pivot_close.ffill().dropna()

        # 计算每日收益率
        returns = pivot_close.pct_change()

        # 计算组合的平均每日收益率（等权重）
        portfolio_returns = returns.mean(axis=1)

        # 获取基准股票的历史数据
        benchmark_data = fetch_stock_data(benchmark_symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))

        if benchmark_data is not None and not benchmark_data.empty:
            benchmark_data.reset_index(inplace=True)
            benchmark_data.rename(columns={'Date': 'Date'}, inplace=True)  # 确保日期列名为 'Date'
            benchmark_data['Date'] = pd.to_datetime(benchmark_data['Date'])
            benchmark_data.set_index('Date', inplace=True)

            # 计算基准股票的每日收益率
            benchmark_returns = benchmark_data['Close'].pct_change()

            # 对齐日期索引
            common_index = portfolio_returns.index.intersection(benchmark_returns.index)
            portfolio_returns = portfolio_returns.loc[common_index]
            benchmark_returns = benchmark_returns.loc[common_index]

            # 处理缺失值
            portfolio_returns = portfolio_returns.fillna(0)
            benchmark_returns = benchmark_returns.fillna(0)

            # 计算累积收益
            portfolio_cumulative_returns = (1 + portfolio_returns).cumprod() - 1
            benchmark_cumulative_returns = (1 + benchmark_returns).cumprod() - 1

            # 准备 Plotly 图表
            fig = go.Figure()

            # 添加投资组合累积收益曲线
            fig.add_trace(go.Scatter(
                x=portfolio_cumulative_returns.index,
                y=portfolio_cumulative_returns.values,
                mode='lines',
                name='投资组合累积收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累积收益: %{y:.2%}<extra></extra>'
            ))

            # 添加基准股票累积收益曲线
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative_returns.index,
                y=benchmark_cumulative_returns.values,
                mode='lines',
                name=f'{benchmark_input} 累积收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累积收益: %{y:.2%}<extra></extra>'
            ))

            # 设置图表布局
            fig.update_layout(
                title='投资组合与基准股票累积收益对比',
                xaxis_title='日期',
                yaxis_title='累积收益',
                hovermode='x unified',
                template='plotly_white'
            )

            # 设置 Y 轴为百分比格式
            fig.update_yaxes(tickformat=".2%")

            # 显示 Plotly 图表
            st.plotly_chart(fig, use_container_width=True)

            # 绘制基准股票的 K 线图
            fig_candlestick = go.Figure(data=[go.Candlestick(
                x=benchmark_data.index,
                open=benchmark_data['Open'],
                high=benchmark_data['High'],
                low=benchmark_data['Low'],
                close=benchmark_data['Close'],
                name=f'{benchmark_input} K 线',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '开盘价: %{open}<br>' +
                    '最高价: %{high}<br>' +
                    '最低价: %{low}<br>' +
                    '收盘价: %{close}<extra></extra>'
            )])

            fig_candlestick.update_layout(
                title=f'{benchmark_input} K 线图',
                xaxis_title='日期',
                yaxis_title='价格',
                template='plotly_white'
            )

            st.plotly_chart(fig_candlestick, use_container_width=True)

            # 计算总收益
            total_portfolio_return = portfolio_cumulative_returns.iloc[-1]
            total_benchmark_return = benchmark_cumulative_returns.iloc[-1]

            # 显示回测结果
            st.write(f"**投资组合总收益:** {total_portfolio_return * 100:.2f}%")
            st.write(f"**{benchmark_input} 总收益:** {total_benchmark_return * 100:.2f}%")

            # 计算每月获利百分比
            portfolio_monthly = portfolio_cumulative_returns.resample('M').last().pct_change().dropna() * 100
            benchmark_monthly = benchmark_cumulative_returns.resample('M').last().pct_change().dropna() * 100

            # 合并数据
            monthly_returns_df = pd.DataFrame({
                '日期': portfolio_monthly.index.strftime('%Y-%m'),
                '投资组合月获利%': portfolio_monthly.values,
                f'{benchmark_input} 月获利%': benchmark_monthly.values
            })

            # 显示每月获利数据表
            st.write("### 每月获利百分比比较")
            st.dataframe(monthly_returns_df.style.format({
                '投资组合月获利%': "{:.2f}",
                f'{benchmark_input} 月获利%': "{:.2f}"
            }))
        else:
            st.error(f"无法取得基准股票 {benchmark_input} 的资料。请检查股票代号是否正确或该股票是否已退市。")
