#!/usr/bin/env python3
"""
Test to verify peer count display shows only licensed users
"""
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_peer_count_only_licensed_users():
    """Test that peer_group_size only counts licensed users in the DataFrame"""
    
    reference_date = datetime.now()
    
    users_data = []
    
    # Peter Obassa (the manager)
    users_data.append({
        'Email': 'peter.obassa@company.com',
        'ManagerLine': 'Mike Allen -> CEO',
        'Overall Recency': reference_date - timedelta(days=2),
        'Adjusted Consistency (%)': 85,
        'Avg Tools / Report': 6.0,
        'Usage Trend': 'Growing'
    })
    
    # Add 6 licensed direct reports under Peter (simulating the actual scenario)
    for i in range(1, 7):
        users_data.append({
            'Email': f'licensed.user{i}@company.com',
            'ManagerLine': 'Peter Obassa -> Mike Allen -> CEO',
            'Overall Recency': reference_date - timedelta(days=5+i),
            'Adjusted Consistency (%)': 70 - i*2,
            'Avg Tools / Report': 4.0 - i*0.1,
            'Usage Trend': 'Stable'
        })
    
    # Add some other people under Mike Allen (Peter's peers)
    for i in range(1, 4):
        users_data.append({
            'Email': f'peer{i}@company.com',
            'ManagerLine': 'Mike Allen -> CEO',
            'Overall Recency': reference_date - timedelta(days=3+i),
            'Adjusted Consistency (%)': 75 - i*2,
            'Avg Tools / Report': 5.0 - i*0.1,
            'Usage Trend': 'Stable'
        })
    
    # Create DataFrame (NOTE: Only licensed users are in the DataFrame)
    df = pd.DataFrame(users_data)
    
    # Calculate RUI scores
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(df)
    
    # Check Peter's direct reports
    peter_reports = result[result['ManagerLine'].str.startswith('Peter Obassa', na=False)]
    
    # Verify peer group sizes match actual peer counts
    for idx, row in peter_reports.iterrows():
        peer_group = row['peer_group']
        peer_group_size = row['peer_group_size']
        peer_rank_display = row['peer_rank_display']
        
        # Find actual peers in the same group
        actual_peers = result[result['peer_group'] == peer_group]
        
        # The peer_group_size should match the actual number of peers
        assert len(actual_peers) == peer_group_size, \
            f"Mismatch for {row['Email']}: peer_group_size={peer_group_size} but actual={len(actual_peers)}"
        
        # The peer_rank_display should show "x of {peer_group_size}"
        expected_suffix = f" of {peer_group_size}"
        assert expected_suffix in peer_rank_display, \
            f"peer_rank_display '{peer_rank_display}' should contain '{expected_suffix}'"
    
    # Specific check: All 6 licensed reports should show "x of 6" not "x of 16"
    for idx, row in peter_reports.iterrows():
        peer_rank_display = row['peer_rank_display']
        # Extract the denominator from "x of y" format
        if " of " in peer_rank_display:
            denominator = int(peer_rank_display.split(" of ")[1])
            assert denominator == 6, \
                f"Expected 'x of 6' but got '{peer_rank_display}' for {row['Email']}"
    
    print("✓ Test passed: peer_group_size correctly counts only licensed users")
    print(f"  - Peter's direct reports show 'x of 6' (not 'x of 16')")
    print(f"  - All peer_group_size values match actual peer counts")


def test_manager_summary_counts():
    """Test that manager summary only counts licensed users"""
    
    reference_date = datetime.now()
    
    users_data = []
    
    # Create a manager with 6 licensed reports (simulating Peter Obassa scenario)
    users_data.append({
        'Email': 'manager@company.com',
        'ManagerLine': 'Top Boss',
        'Overall Recency': reference_date - timedelta(days=1),
        'Adjusted Consistency (%)': 90,
        'Avg Tools / Report': 7.0,
        'Usage Trend': 'Growing',
        'license_risk': 'Low Risk',
        'rui_score': 85
    })
    
    # Add 6 licensed direct reports
    for i in range(1, 7):
        risk = 'High Risk' if i <= 2 else ('Medium Risk' if i <= 4 else 'Low Risk')
        users_data.append({
            'Email': f'report{i}@company.com',
            'ManagerLine': 'manager -> Top Boss',
            'Overall Recency': reference_date - timedelta(days=5+i),
            'Adjusted Consistency (%)': 70 - i*5,
            'Avg Tools / Report': 4.0 - i*0.2,
            'Usage Trend': 'Stable',
            'license_risk': risk,
            'rui_score': 70 - i*5
        })
    
    df = pd.DataFrame(users_data)
    
    # Calculate RUI scores
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(df)
    
    # Get manager summary
    summary = calculator.get_manager_summary(result)
    
    # The manager should show team size of 6 (not 16 or any other number)
    manager_row = summary[summary['Manager/Group'].str.contains('manager', case=False, na=False)]
    if not manager_row.empty:
        team_size = manager_row.iloc[0]['Team Size']
        assert team_size == 6, f"Expected team size of 6 but got {team_size}"
        print(f"✓ Manager summary correctly shows team size of {team_size} (licensed users only)")


if __name__ == "__main__":
    test_peer_count_only_licensed_users()
    test_manager_summary_counts()