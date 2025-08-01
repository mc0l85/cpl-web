#!/usr/bin/env python3
"""Simple test to verify the analysis logic works correctly"""

import pandas as pd
from analysis_logic import AnalysisRunner

def main():
    # Test with a small subset of files
    usage_files = {
        'file1': 'temp_uploads/050b01f0-8f53-4d0c-86ff-a30b7479b3a0/2025_07_01_CopilotActivityUserDetail.csv',
        'file2': 'temp_uploads/050b01f0-8f53-4d0c-86ff-a30b7479b3a0/2025_07_04_User_Activity_Report.csv'
    }
    
    target_file = 'temp_uploads/050b01f0-8f53-4d0c-86ff-a30b7479b3a0/202507Jul-30 - ManagerReport.csv'
    
    # Check what companies are available in the target file
    target_df = pd.read_csv(target_file, encoding='utf-8-sig')
    companies = target_df['Company'].dropna().unique().tolist()
    print(f"Available companies: {companies[:5]}...")  # Show first 5
    
    # Apply a filter to limit the results
    filters = {
        'companies': [companies[0]] if companies else []  # Filter by the first company
    }
    
    print("Testing analysis logic with filtering...")
    print("-" * 50)
    
    # Check how many users are in the target file with the filter applied
    target_df['UserPrincipalName'] = target_df['UserPrincipalName'].str.lower()
    if filters.get('companies'):
        vals = set([v.lower() for v in filters['companies']])
        filtered_target_df = target_df[target_df['Company'].str.lower().isin(vals)]
        print(f"Users in target file with company filter: {len(filtered_target_df)}")
    
    # Run analysis with filter
    runner = AnalysisRunner(None, None)
    
    # Mock the update_status method
    runner.update_status = lambda msg: None
    
    results = runner.execute_analysis(usage_files, target_file, filters)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return 1
        
    # Print some key metrics
    metrics_df = results['deep_dive_data']['utilized_metrics_df']
    print(f"Users analyzed with filter: {len(metrics_df)}")
    if len(metrics_df) > 0:
        print(f"Top user: {metrics_df.iloc[0]['Email']} (Score: {metrics_df.iloc[0]['Engagement Score']:.4f})")
    
    # Check if Tool Expansion Rate column exists
    if 'Tool Expansion Rate' in metrics_df.columns:
        print("✅ Tool Expansion Rate column added successfully")
    else:
        print("❌ Tool Expansion Rate column missing")
    
    print("Test completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())