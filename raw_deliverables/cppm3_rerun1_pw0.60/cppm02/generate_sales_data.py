#!/usr/bin/env python3
"""
Generate a CSV file with sales data containing:
- 36 rows (3 rows per month for 12 months)
- Columns: month, revenue, cost, channel
- Intentional NaN values in revenue or cost columns
- Intentional anomalies where revenue < cost
- Reproducible random values
"""

import random
import csv
import os

# Set seed for reproducibility
random.seed(42)

# Define directories
output_dir = "/tmp/opencode/agent_test"
output_file = os.path.join(output_dir, "sales_data.csv")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Generate data
rows = []
channels = ["线上", "线下", "分销"]

# Track which rows have anomalies and NaNs
anomaly_rows = []  # rows where revenue < cost
nan_rows = []      # rows where revenue or cost is NaN

# Generate 36 rows (3 per month)
for month in range(1, 13):
    for _ in range(3):
        # Generate revenue (50-200 万元)
        revenue = random.uniform(50, 200)
        
        # Generate cost (30-120 万元)
        cost = random.uniform(30, 120)
        
        # Random channel
        channel = random.choice(channels)
        
        # Introduce anomalies (revenue < cost) at specific rows
        # Row 5 (month 1, 2nd row) and Row 10 (month 2, 2nd row)
        if month == 1 and _ == 1:
            revenue = 40  # Make revenue < cost
            anomaly_rows.append((month, _ + 1))
        elif month == 2 and _ == 1:
            revenue = 35  # Make revenue < cost
            anomaly_rows.append((month, _ + 1))
        
        # Introduce NaN values at specific rows
        # Row 15 (month 3, 2nd row) - NaN in revenue
        # Row 25 (month 6, 2nd row) - NaN in cost
        if month == 3 and _ == 1:
            revenue = None  # NaN in revenue
            nan_rows.append((month, _ + 1, "revenue"))
        elif month == 6 and _ == 1:
            cost = None  # NaN in cost
            nan_rows.append((month, _ + 1, "cost"))
        
        rows.append({
            "month": month,
            "revenue": revenue,
            "cost": cost,
            "channel": channel
        })

# Write to CSV
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["month", "revenue", "cost", "channel"])
    writer.writeheader()
    writer.writerows(rows)

print(f"CSV file generated successfully at: {output_file}")
print(f"Total rows: {len(rows)}")
print(f"Anomaly rows (revenue < cost): {anomaly_rows}")
print(f"NaN rows: {nan_rows}")
