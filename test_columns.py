#!/usr/bin/env python3
"""Test to see what columns are present in the dataframe after RUI processing"""

import pandas as pd
import numpy as np

print("Testing column preservation after RUI processing...")

# Create a minimal test dataframe with required columns
test_df = pd.DataFrame({
    'Email': ['test1@example.com', 'test2@example.com'],
    'Overall Recency': [pd.Timestamp('2024-01-15'), pd.Timestamp('2024-01-10')],
    'Usage Complexity': [5, 8],
    'Adjusted Consistency (%)': [75.0, 60.0],
    'Avg Tools / Report': [3.5, 2.1],
    'Usage Consistency (%)': [70.0, 55.0],
    'First Appearance': [pd.Timestamp('2023-12-01'), pd.Timestamp('2023-11-15')],
    'Adoption Date': [pd.Timestamp('2023-12-01'), pd.Timestamp('2023-11-15')],
    'Adoption Velocity': [0.05, 0.03],
    'Days Since License': [45, 60],
    'Classification': ['Active User', 'Active User'],
    'Usage Trend': ['Stable', 'Increasing']  # Add Usage Trend column
})

print("\nColumns before RUI processing:")
print(test_df.columns.tolist())

# Create RUI calculator
from rui_calculator import RUICalculator
rui_calc = RUICalculator(pd.Timestamp('2024-01-20'))

# Process without manager data
result_df = rui_calc.calculate_rui_scores(test_df)

print("\nColumns after RUI processing:")
print(result_df.columns.tolist())

# Check if critical columns are preserved
critical_cols = ['Overall Recency', 'Usage Complexity']
print("\nChecking critical columns:")
for col in critical_cols:
    if col in result_df.columns:
        print(f"✓ {col} - PRESERVED")
        print(f"  Sample values: {result_df[col].tolist()}")
    else:
        print(f"✗ {col} - MISSING!")

# Check what new columns were added
new_cols = [col for col in result_df.columns if col not in test_df.columns]
print(f"\nNew columns added by RUI: {new_cols}")

# Now test with the Excel report generation
print("\n" + "="*50)
print("Testing Excel report column handling...")

# Simulate what happens in create_excel_report
col_display_map = {
    'Usage Complexity': 'Total Tools Used'
}

df_local = result_df.copy()

# Rename columns for display
for old_name, new_name in col_display_map.items():
    if old_name in df_local.columns:
        print(f"Renaming '{old_name}' to '{new_name}'")
        df_local = df_local.rename(columns={old_name: new_name})
    else:
        print(f"WARNING: Column '{old_name}' not found for renaming!")

# Check target columns for Leaderboard
target_cols = ['Global Rank', 'Email', 'Adjusted Consistency (%)', 'Overall Recency', 
               'Total Tools Used', 'Avg Tools / Report', 'Adoption Velocity', 
               'Tool Expansion Rate', 'Days Since License', 'Usage Trend', 'Engagement Score']

print("\nChecking target columns for Leaderboard:")
for col in target_cols:
    if col in df_local.columns:
        print(f"✓ {col}")
    else:
        print(f"✗ {col} - MISSING")

print("\nActual columns in df_local:")
print(df_local.columns.tolist())