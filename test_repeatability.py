#!/usr/bin/env python3
"""Test repeatability of analysis results"""

import os
import sys
import hashlib
import json
from analysis_logic import AnalysisRunner

def get_results_hash(results):
    """Generate a hash of the results for comparison"""
    # Extract key metrics that should be identical
    if 'error' in results:
        return None
    
    metrics_df = results['deep_dive_data']['utilized_metrics_df']
    
    # Create a deterministic string representation
    hash_data = {
        'total_users': len(metrics_df),
        'categories': results['dashboard']['categories'],
        'top_10_users': metrics_df.head(10)[['Email', 'Global Rank', 'Engagement Score', 'Classification']].to_dict('records')
    }
    
    # Convert to JSON string and hash
    json_str = json.dumps(hash_data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

def main():
    # Test files - update these paths as needed
    usage_files = {
        'file1': 'temp_uploads/0e77dde1-3a16-42bc-ab06-5cdeaa655d9f/2025_07_01_CopilotActivityUserDetail.csv',
        'file2': 'temp_uploads/0e77dde1-3a16-42bc-ab06-5cdeaa655d9f/2025_07_04_User_Activity_Report.csv'
    }
    
    target_file = 'temp_uploads/0e77dde1-3a16-42bc-ab06-5cdeaa655d9f/202507Jul-30 - ManagerReport.csv'
    filters = {}  # Empty filters for testing
    
    print("Testing repeatability of analysis results...")
    print("-" * 50)
    
    hashes = []
    
    # Run analysis 5 times
    for i in range(5):
        print(f"\nRun {i+1}...")
        runner = AnalysisRunner(None, None)
        
        # Mock the update_status method
        runner.update_status = lambda msg: None
        
        results = runner.execute_analysis(usage_files, target_file, filters)
        
        if 'error' in results:
            print(f"Error in run {i+1}: {results['error']}")
            continue
            
        result_hash = get_results_hash(results)
        hashes.append(result_hash)
        
        # Print some key metrics
        metrics_df = results['deep_dive_data']['utilized_metrics_df']
        print(f"  Total users: {len(metrics_df)}")
        print(f"  Top user: {metrics_df.iloc[0]['Email']} (Score: {metrics_df.iloc[0]['Engagement Score']:.4f})")
        print(f"  Hash: {result_hash[:16]}...")
    
    print("\n" + "-" * 50)
    print("REPEATABILITY TEST RESULTS:")
    
    if len(set(hashes)) == 1:
        print("✅ PASS: All runs produced identical results")
        print(f"   Consistent hash: {hashes[0]}")
    else:
        print("❌ FAIL: Results varied between runs")
        print("   Unique hashes found:")
        for i, h in enumerate(set(hashes)):
            print(f"   - {h}")
    
    return 0 if len(set(hashes)) == 1 else 1

if __name__ == "__main__":
    sys.exit(main())