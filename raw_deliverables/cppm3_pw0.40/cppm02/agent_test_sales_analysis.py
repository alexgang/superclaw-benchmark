#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售数据分析脚本
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

def main():
    csv_path = '/workspace/agent_test/sales_data.csv'
    output_dir = '/workspace/agent_test/'
    
    # 读取 CSV
    print("=" * 50)
    print("开始读取销售数据...")
    print("=" * 50)
    
    df = pd.read_csv(csv_path)
    df['month'] = pd.to_datetime(df['month'], format='%Y-%m')
    df['year_month'] = df['month'].dt.strftime('%Y-%m')
    
    print(f"原始数据行数：{len(df)}")
    print(f"原始数据列：{list(df.columns)}")
    print("\n原始数据预览：")
    print(df.to_string())
    
    # 数据清洗
    print("\n" + "=" * 50)
    print("开始数据清洗...")
    print("=" * 50)
    
    # 记录缺失值
    missing_mask = df[['revenue', 'cost']].isnull()
    missing_count = missing_mask.sum().sum()
    print(f"发现 {missing_count} 个缺失值")
    
    # 按月份和渠道分组，计算均值
    df['month_channel_key'] = df['year_month'] + '_' + df['channel']
    
    # 填充缺失值
    df['revenue_filled'] = df.groupby(['year_month', 'channel'])['revenue'].transform(lambda x: x.fillna(x.mean()))
    df['cost_filled'] = df.groupby(['year_month', 'channel'])['cost'].transform(lambda x: x.fillna(x.mean()))
    
    # 标记异常值 (revenue < cost)
    df['is_anomaly'] = df['revenue'] < df['cost']
    
    # 剔除异常行
    df_clean = df[~df['is_anomaly']].copy()
    
    # 删除临时列
    df_clean = df_clean.drop(columns=['month_channel_key', 'revenue_filled', 'cost_filled', 'is_anomaly'])
    
    print(f"清洗后数据行数：{len(df_clean)}")
    print(f"清洗掉的异常行数：{len(df) - len(df_clean)}")
    
    # 显示异常行详情
    print("\n" + "=" * 50)
    print("异常行详情：")
    print("=" * 50)
    anomalies = df[df['is_anomaly']]
    for idx, row in anomalies.iterrows():
        print(f"  行 {idx+1}: 月份={row['month']}, 销售额={row['revenue']}, 成本={row['cost']}, 渠道={row['channel']}")
    
    # 计算每月汇总
    print("\n" + "=" * 50)
    print("计算每月汇总...")
    print("=" * 50)
    
    monthly_summary = df_clean.groupby('year_month').agg({
        'revenue': 'sum',
        'cost': 'sum',
        'channel': lambda x: x.mode().iloc[0] if len(x) > 0 else '未知'
    }).reset_index()
    
    monthly_summary['毛利率'] = (monthly_summary['revenue'] - monthly_summary['cost']) / monthly_summary['revenue']
    
    print(monthly_summary.to_string())
    
    # 按渠道统计全年占比
    print("\n" + "=" * 50)
    print("按渠道统计全年占比...")
    print("=" * 50)
    
    channel_summary = df_clean.groupby('channel').agg({
        'revenue': 'sum',
        'cost': 'sum'
    }).reset_index()
    
    channel_summary['毛利率'] = (channel_summary['revenue'] - channel_summary['cost']) / channel_summary['revenue']
    channel_summary['占比'] = channel_summary['revenue'] / channel_summary['revenue'].sum() * 100
    
    print(channel_summary.to_string())
    
    # 计算全年总毛利率
    total_revenue = df_clean['revenue'].sum()
    total_cost = df_clean['cost'].sum()
    total_margin = (total_revenue - total_cost) / total_revenue * 100
    
    print("\n" + "=" * 50)
    print("全年汇总：")
    print("=" * 50)
    print(f"  全年总销售额：{total_revenue:.2f} 万元")
    print(f"  全年总成本：{total_cost:.2f} 万元")
    print(f"  全年总毛利率：{total_margin:.2f}%")
    
    # 生成图表
    print("\n" + "=" * 50)
    print("生成图表...")
    print("=" * 50)
    
    # 月度销售额 + 毛利率双轴折线图
    plt.figure(figsize=(12, 8))
    
    months = monthly_summary['year_month']
    monthly_revenue = monthly_summary['revenue']
    monthly_margin = monthly_summary['毛利率']
    
    # 设置中文字体
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.size'] = 12
    
    # 双轴折线图
    ax1 = plt.subplot(121)
    ax1.plot(months, monthly_revenue, marker='o', label='销售额', color='blue')
    ax1.set_title('月度销售额', fontsize=14, fontweight='bold')
    ax1.set_xlabel('月份', fontsize=12)
    ax1.set_ylabel('销售额 (万元)', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 毛利率折线（右轴）
    ax2 = plt.subplot(122, sharex=ax1)
    ax2.plot(months, monthly_margin, marker='s', label='毛利率', color='red')
    ax2.set_title('月度毛利率', fontsize=14, fontweight='bold')
    ax2.set_xlabel('月份', fontsize=12)
    ax2.set_ylabel('毛利率 (%)', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'monthly_trend.png'), dpi=150, bbox_inches='tight')
    print(f"  已生成：monthly_trend.png")
    plt.close()
    
    # 渠道占比饼图
    plt.figure(figsize=(10, 8))
    
    ax = plt.subplot(111)
    channel_names = channel_summary['channel']
    channel_values = channel_summary['revenue']
    channel_percentages = channel_summary['占比']
    
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    ax.pie(channel_values, labels=channel_names, autopct='%1.1f%%', 
           startangle=140, colors=colors, explode=[0.1, 0.15, 0.1])
    
    ax.set_title('全年渠道销售额占比', fontsize=14, fontweight='bold')
    ax.axis('equal')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'channel_pie.png'), dpi=150, bbox_inches='tight')
    print(f"  已生成：channel_pie.png")
    plt.close()
    
    # 打印清洗前后的数据行数对比
    print("\n" + "=" * 50)
    print("数据行数对比：")
    print("=" * 50)
    print(f"  清洗前：{len(df)} 行")
    print(f"  清洗后：{len(df_clean)} 行")
    print(f"  清洗掉：{len(df) - len(df_clean)} 行")
    
    print("\n" + "=" * 50)
    print("脚本执行完成！")
    print("=" * 50)
    
    return total_margin

if __name__ == '__main__':
    main()
