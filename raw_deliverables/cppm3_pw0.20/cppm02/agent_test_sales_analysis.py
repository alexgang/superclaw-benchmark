#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售数据分析脚本
功能：
1. 读取 CSV 文件
2. 数据清洗：用当月同渠道均值填充缺失值，剔除 revenue < cost 的异常行
3. 计算每月汇总销售额、毛利率
4. 按渠道统计全年占比
5. 生成图表并保存
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

# 设置中文字体
font_properties = FontProperties(family='SimHei', size=12)

def load_and_clean_data(filepath):
    """
    加载数据并进行清洗
    返回：原始数据、清洗后数据、异常行信息
    """
    # 读取 CSV
    df = pd.read_csv(filepath)
    
    # 记录原始行数
    original_rows = len(df)
    
    # 创建副本用于清洗
    df_clean = df.copy()
    
    # 步骤 1：先标记并剔除 revenue < cost 的异常行
    df_clean['is_outlier'] = df_clean['revenue'] < df_clean['cost']
    
    # 记录异常行信息
    outlier_rows = df_clean[df_clean['is_outlier']].copy()
    outlier_details = []
    for idx, row in outlier_rows.iterrows():
        outlier_details.append({
            'month': row['month'],
            'revenue': row['revenue'],
            'cost': row['cost'],
            'channel': row['channel']
        })
    
    # 剔除异常行
    df_clean = df_clean[~df_clean['is_outlier']].copy()
    
    # 步骤 2：用当月同渠道均值填充缺失值
    # 先计算每个渠道的均值（排除缺失值）
    df_clean['revenue_mean'] = df_clean.groupby('channel')['revenue'].transform('mean')
    df_clean['cost_mean'] = df_clean.groupby('channel')['cost'].transform('mean')
    
    # 填充缺失值
    df_clean['revenue'] = df_clean['revenue'].fillna(df_clean['revenue_mean'])
    df_clean['cost'] = df_clean['cost'].fillna(df_clean['cost_mean'])
    
    # 删除临时列
    df_clean = df_clean.drop(columns=['revenue_mean', 'cost_mean', 'is_outlier'])
    
    # 记录清洗后行数
    cleaned_rows = len(df_clean)
    
    return df, df_clean, outlier_details, original_rows, cleaned_rows

def calculate_monthly_summary(df):
    """
    计算每月汇总销售额、毛利率
    """
    df['month_num'] = pd.to_datetime(df['month']).dt.year * 12 + pd.to_datetime(df['month']).dt.month - 1
    
    # 每月汇总
    monthly_summary = df.groupby('month_num').agg({
        'revenue': 'sum',
        'cost': 'sum',
        'channel': lambda x: x.mode().iloc[0] if len(x) > 0 else '未知'
    }).reset_index()
    
    # 计算毛利率
    monthly_summary['gross_margin'] = (monthly_summary['revenue'] - monthly_summary['cost']) / monthly_summary['revenue']
    
    return monthly_summary

def calculate_channel_distribution(df):
    """
    按渠道统计全年占比
    """
    channel_stats = df.groupby('channel').agg({
        'revenue': 'sum',
        'cost': 'sum'
    }).reset_index()
    
    channel_stats['total_revenue'] = channel_stats['revenue']
    channel_stats['total_cost'] = channel_stats['cost']
    channel_stats['gross_margin'] = (channel_stats['total_revenue'] - channel_stats['total_cost']) / channel_stats['total_revenue']
    
    # 计算占比
    total_revenue = channel_stats['total_revenue'].sum()
    channel_stats['revenue_share'] = channel_stats['total_revenue'] / total_revenue
    
    return channel_stats

def create_monthly_trend_plot(monthly_summary, output_path):
    """
    创建月度销售额 + 毛利率双轴折线图
    """
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # 绘制销售额折线
    ax1.plot(monthly_summary['month_num'], monthly_summary['revenue'], 
             marker='o', color='blue', label='销售额（万元）', linewidth=2)
    ax1.set_ylabel('销售额（万元）', fontsize=12)
    ax1.set_title('月度销售额与毛利率趋势图', fontsize=14, fontname='SimHei')
    ax1.grid(True, alpha=0.3)
    
    # 创建第二个 y 轴
    ax2 = ax1.twinx()
    
    # 绘制毛利率折线
    ax2.plot(monthly_summary['month_num'], monthly_summary['gross_margin'], 
             marker='s', color='red', label='毛利率', linewidth=2)
    ax2.set_ylabel('毛利率', fontsize=12)
    
    # 合并图例
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"月度趋势图已保存到：{output_path}")

def create_channel_pie_plot(channel_stats, output_path):
    """
    创建渠道占比饼图
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 创建饼图
    wedges, texts, autotexts = ax.pie(
        channel_stats['revenue_share'],
        labels=channel_stats['channel'],
        autopct='%1.1f%%',
        colors=['#FF9999', '#99FF99', '#9999FF'],
        wedgeprops=dict(edgecolor='white', linewidth=1)
    )
    
    ax.set_title('全年渠道销售占比', fontsize=14, fontname='SimHei')
    ax.axis('equal')
    
    # 设置中文显示
    for text in texts:
        text.set_fontname('SimHei')
    for autotext in autotexts:
        autotext.set_fontname('SimHei')
        autotext.set_fontsize(10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"渠道占比饼图已保存到：{output_path}")

def main():
    """
    主函数
    """
    print("=" * 60)
    print("销售数据分析脚本开始执行")
    print("=" * 60)
    
    # 文件路径
    csv_path = '/workspace/agent_test/sales_data.csv'
    output_dir = '/workspace/agent_test/'
    
    # 步骤 1：加载并清洗数据
    print("\n[步骤 1] 加载并清洗数据...")
    original_df, cleaned_df, outlier_details, original_rows, cleaned_rows = load_and_clean_data(csv_path)
    
    print(f"原始数据行数：{original_rows}")
    print(f"清洗后数据行数：{cleaned_rows}")
    print(f"清洗掉的异常行数：{original_rows - cleaned_rows}")
    
    # 步骤 2：计算汇总统计
    print("\n[步骤 2] 计算每月汇总...")
    monthly_summary = calculate_monthly_summary(cleaned_df)
    channel_stats = calculate_channel_distribution(cleaned_df)
    
    # 步骤 3：生成图表
    print("\n[步骤 3] 生成图表...")
    create_monthly_trend_plot(monthly_summary, output_dir + 'monthly_trend.png')
    create_channel_pie_plot(channel_stats, output_dir + 'channel_pie.png')
    
    # 步骤 4：输出全年总毛利率
    print("\n[步骤 4] 输出全年统计信息...")
    total_revenue = cleaned_df['revenue'].sum()
    total_cost = cleaned_df['cost'].sum()
    total_gross_margin = (total_revenue - total_cost) / total_revenue
    
    print(f"\n" + "=" * 60)
    print("脚本执行完成！")
    print("=" * 60)
    print(f"\n清洗掉的异常行详情：")
    for outlier in outlier_details:
        print(f"  - 月份：{outlier['month']}, 销售额：{outlier['revenue']}, 成本：{outlier['cost']}, 渠道：{outlier['channel']}")
    
    print(f"\n全年总销售额：{total_revenue:.2f} 万元")
    print(f"全年总成本：{total_cost:.2f} 万元")
    print(f"全年总毛利率：{total_gross_margin:.2%}")
    print("=" * 60)
    
    return total_gross_margin

if __name__ == '__main__':
    main()
