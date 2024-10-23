# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import yfinance as yf
from datetime import date, datetime, timedelta

# 设置页面配置
st.set_page_config(
    page_title="邦的股市回测系统",
    layout="wide"
)

# 标题
st.title('📈 邦的股市回测系统')

# 功能函数
def load_stock_data(stock_list, start_date, end_date):
    data_frames = []
    for stock in stock_list:
        # yfinance 中，台湾股票代码需要加上 ".TW"
        ticker = f"{stock}.TW"
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty:
                st.warning(f"无法下载股票代码为 {stock} 的数据，数据为空。")
            else:
                # 使用调整后的收盘价
                df = df[['Adj Close']].dropna()
                df.rename(columns={'Adj Close': stock}, inplace=True)
                data_frames.append(df)
        except Exception as e:
            st.warning(f"下载股票代码为 {stock} 的数据时出现错误: {e}")
    if data_frames:
        # 合并所有 DataFrame，按照日期索引对齐
        combined_df = pd.concat(data_frames, axis=1)
        return combined_df
    else:
        return pd.DataFrame()  # 返回空的 DataFrame

def calculate_cumulative_returns(price_data):
    if price_data.empty:
        st.error("价格数据为空，无法计算累计收益。")
        return pd.Series(dtype='float64')
    # 计算累计收益（百分比），保留两位小数
    cumulative_returns = ((price_data / price_data.iloc[0] - 1) * 100).round(2)
    return cumulative_returns

def load_and_process_data(strategy_stocks, benchmark_stock, start_date, end_date):
    strategy_data = load_stock_data(strategy_stocks, start_date, end_date)
    benchmark_data = load_stock_data([benchmark_stock], start_date, end_date)
    if strategy_data.empty:
        st.error("策略股票的数据为空，请检查股票代码或数据来源。")
        return None, None
    if benchmark_data.empty:
        st.error("基准股票的数据为空，请检查股票代码或数据来源。")
        return None, None
    # 计算策略组合的平均价格
    strategy_price = strategy_data.mean(axis=1)
    # 计算累计收益
    strategy_cumulative_returns = calculate_cumulative_returns(strategy_price)
    benchmark_cumulative_returns = calculate_cumulative_returns(benchmark_data.iloc[:, 0])
    return strategy_cumulative_returns, benchmark_cumulative_returns

# 侧边栏选项
with st.sidebar:
    st.header("选项设置")
    # 日期选择器
    start_date = st.date_input('选择开始日期', value=date(2023, 1, 1))
    end_date = st.date_input('选择结束日期', value=date(2024, 10, 23))
    if start_date > end_date:
        st.error('开始日期不能晚于结束日期')

    # 可选股票列表，包括 ETF
    stock_options = ['2330', '2317', '2412', '1301', '2308', '0050', '0056']
    # 选择策略股票
    strategy_stocks = st.multiselect(
        '选择组合策略的股票（至少选择一支）',
        stock_options,
        default=['2330']
    )

    # 让用户输入比较的股票代码
    benchmark_stock = st.text_input('输入比较的股票代码', value='0050')

    # 复利计算器选项
    st.subheader("复利计算器")
    use_compound = st.checkbox('使用复利计算器')

    if use_compound:
        initial_capital = st.number_input('初始资金（元）', min_value=0, value=10000)
        monthly_investment = st.number_input('每月投入（元）', min_value=0, value=1000)

# 主体内容
if strategy_stocks and benchmark_stock and start_date <= end_date:
    # 加载和处理数据
    strategy_performance, benchmark_performance = load_and_process_data(strategy_stocks, benchmark_stock, start_date, end_date)

    if strategy_performance is not None and benchmark_performance is not None and not strategy_performance.empty and not benchmark_performance.empty:
        # 对齐日期索引
        combined_index = strategy_performance.index.intersection(benchmark_performance.index)
        strategy_performance = strategy_performance.loc[combined_index]
        benchmark_performance = benchmark_performance.loc[combined_index]

        # 合并数据
        comparison_df = pd.DataFrame({
            '策略组合': strategy_performance,
            benchmark_stock: benchmark_performance
        })

        # 将日期索引转换为日期格式
        comparison_df.index = comparison_df.index.date

        # 绘制交互式图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=comparison_df.index, y=comparison_df['策略组合'],
            mode='lines', name='策略组合'
        ))
        fig.add_trace(go.Scatter(
            x=comparison_df.index, y=comparison_df[benchmark_stock],
            mode='lines', name=benchmark_stock
        ))
        fig.update_layout(
            title='策略组合与基准股票的累计涨幅比较',
            xaxis_title='日期',
            yaxis_title='累计涨幅（%）',
            hovermode='x unified',
            yaxis=dict(tickformat='.2f%', showgrid=True),
            legend=dict(x=0, y=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # 如果使用复利计算器，进行计算
        if use_compound:
            # 计算投资期间的年数
            total_days = (end_date - start_date).days
            years = total_days / 365.25

            # 计算策略组合的年化报酬率
            strategy_total_return = strategy_performance.iloc[-1] / 100  # 百分比转换为小数
            strategy_annual_return = (1 + strategy_total_return) ** (1 / years) - 1

            # 计算基准股票的年化报酬率
            benchmark_total_return = benchmark_performance.iloc[-1] / 100  # 百分比转换为小数
            benchmark_annual_return = (1 + benchmark_total_return) ** (1 / years) - 1

            # 计算月收益率和总月数
            strategy_r_monthly = strategy_annual_return / 12
            benchmark_r_monthly = benchmark_annual_return / 12
            n_months = int(years * 12)

            # 建立时间轴
            dates = [start_date + timedelta(days=30*i) for i in range(n_months+1)]
            if dates[-1] > end_date:
                dates[-1] = end_date

            # 计算策略组合的收益
            strategy_interest = []
            for i in range(len(dates)):
                # 初始资金增长
                FV_initial = initial_capital * (1 + strategy_r_monthly) ** i
                # 每月投入增长
                if strategy_r_monthly != 0:
                    FV_monthly = monthly_investment * (((1 + strategy_r_monthly) ** i - 1) / strategy_r_monthly)
                else:
                    FV_monthly = monthly_investment * i
                total = FV_initial + FV_monthly
                principal = initial_capital + monthly_investment * i
                interest = total - principal
                strategy_interest.append(interest)

            # 计算基准股票的收益
            benchmark_interest = []
            for i in range(len(dates)):
                # 初始资金增长
                FV_initial = initial_capital * (1 + benchmark_r_monthly) ** i
                # 每月投入增长
                if benchmark_r_monthly != 0:
                    FV_monthly = monthly_investment * (((1 + benchmark_r_monthly) ** i - 1) / benchmark_r_monthly)
                else:
                    FV_monthly = monthly_investment * i
                total = FV_initial + FV_monthly
                principal = initial_capital + monthly_investment * i
                interest = total - principal
                benchmark_interest.append(interest)

            # 构建收益数据表
            growth_df = pd.DataFrame({
                '日期': dates,
                '策略组合收益': strategy_interest,
                f'{benchmark_stock} 收益': benchmark_interest
            })

            # 格式化数据表，去除小数点
            growth_df_display = growth_df.copy()
            cols_to_round = ['策略组合收益', f'{benchmark_stock} 收益']
            growth_df_display[cols_to_round] = growth_df_display[cols_to_round].round(0).astype(int)

            # 显示收益数据表
            st.subheader("收益数据表")
            st.dataframe(growth_df_display)

            # 绘制收益柱状图
            fig2 = go.Figure()

            # 策略组合收益
            fig2.add_trace(go.Bar(
                x=growth_df['日期'],
                y=growth_df['策略组合收益'],
                name='策略组合收益',
                marker_color='blue'
            ))

            # 基准股票收益
            fig2.add_trace(go.Bar(
                x=growth_df['日期'],
                y=growth_df[f'{benchmark_stock} 收益'],
                name=f'{benchmark_stock} 收益',
                marker_color='green'
            ))

            fig2.update_layout(
                barmode='group',  # 分组显示
                title='收益比较图',
                xaxis_title='日期',
                yaxis_title='收益（元）',
                hovermode='x unified',
                legend=dict(x=0, y=1),
                yaxis_tickformat=',',  # 数字不显示科学记号或缩写
            )
            st.plotly_chart(fig2, use_container_width=True)

            # 显示最终结果，使用表格形式
            result_df = pd.DataFrame({
                '项目': ['策略组合', f'基准股票（{benchmark_stock}）'],
                '累计涨幅（%）': [f"{strategy_total_return * 100:.2f}%", f"{benchmark_total_return * 100:.2f}%"],
                '年化报酬率（%）': [f"{strategy_annual_return * 100:.2f}%", f"{benchmark_annual_return * 100:.2f}%"],
            })

            st.subheader("复利计算结果比较")
            st.table(result_df)

    else:
        st.error("数据加载或处理失败，请检查您的股票代码。")
else:
    st.info("请在左侧选择策略股票和比较的股票代码，并确保开始日期早于结束日期。")
