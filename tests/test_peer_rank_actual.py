#!/usr/bin/env python3
"""
Test to reproduce the actual peer rank display issue
"""
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_actual_peer_rank_scenario():
    """
    Reproduce the scenario where peer_rank_display shows x/16 
    but only 6 peers are visible
    """
    
    reference_date = datetime.now()
    
    # Create a scenario similar to Peter Obassa's actual data
    users_data = []
    
    # Add Peter Obassa as a manager
    users_data.append({
        'Email': 'peter.obassa@haleon.com',
        'ManagerLine': 'Mike Allen -> CEO',
        'Overall Recency': reference_date - timedelta(days=2),
        'Adjusted Consistency (%)': 85,
        'Avg Tools / Report': 6.0,
        'Usage Trend': 'Growing',
        'Department': 'Technology'
    })
    
    # Add 6 licensed direct reports under Peter
    # These are the only ones with licenses (visible in data)
    direct_reports = [
        'dan.basile@haleon.com',
        'pariss.bethune@haleon.com', 
        'james.peterson@haleon.com',
        'sarah.jones@haleon.com',
        'john.smith@haleon.com',
        'mary.wilson@haleon.com'
    ]
    
    for i, email in enumerate(direct_reports):
        users_data.append({
            'Email': email,
            'ManagerLine': 'Peter Obassa -> Mike Allen -> CEO',
            'Overall Recency': reference_date - timedelta(days=5+i),
            'Adjusted Consistency (%)': 70 - i*2,
            'Avg Tools / Report': 4.0 - i*0.1,
            'Usage Trend': 'Stable',
            'Department': 'Technology'
        })
    
    # Add some people at Peter's level (his peers)
    peer_managers = ['alice.manager@haleon.com', 'bob.director@haleon.com']
    for i, email in enumerate(peer_managers):
        users_data.append({
            'Email': email,
            'ManagerLine': 'Mike Allen -> CEO',
            'Overall Recency': reference_date - timedelta(days=3+i),
            'Adjusted Consistency (%)': 80 - i*5,
            'Avg Tools / Report': 5.5 - i*0.2,
            'Usage Trend': 'Stable',
            'Department': 'Technology'
        })
    
    # Create DataFrame - only contains licensed users
    df = pd.DataFrame(users_data)
    print("=" * 70)
    print("DATA SETUP")
    print("=" * 70)
    print(f"Total users in DataFrame (all licensed): {len(df)}")
    print(f"- Peter Obassa: 1")
    print(f"- Peter's direct reports (licensed): {len(direct_reports)}")
    print(f"- Peter's peer managers: {len(peer_managers)}")
    
    # Calculate RUI scores
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(df)
    
    print("\n" + "=" * 70)
    print("PEER RANK ANALYSIS FOR PETER'S DIRECT REPORTS")
    print("=" * 70)
    
    # Check Peter's direct reports
    peter_reports = result[result['ManagerLine'].str.startswith('Peter Obassa', na=False)]
    
    print(f"\nFound {len(peter_reports)} direct reports under Peter Obassa:")
    for idx, row in peter_reports.iterrows():
        print(f"\n{row['Email']}:")
        print(f"  peer_group: {row['peer_group']}")
        print(f"  peer_group_type: {row['peer_group_type']}")
        print(f"  peer_group_size: {row['peer_group_size']}")
        print(f"  peer_rank: {row['peer_rank']}")
        print(f"  peer_rank_display: '{row['peer_rank_display']}'")
        
        # Check if this shows x/16 or x/6
        if " of " in row['peer_rank_display']:
            denominator = int(row['peer_rank_display'].split(" of ")[1])
            if denominator != len(peter_reports):
                print(f"  ⚠️  ISSUE: Shows '{row['peer_rank_display']}' but only {len(peter_reports)} licensed peers exist!")
    
    # Also check what peers are actually in each group
    print("\n" + "=" * 70)
    print("PEER GROUP MEMBERS")
    print("=" * 70)
    
    for peer_group in result['peer_group'].unique():
        members = result[result['peer_group'] == peer_group]
        if any(email in direct_reports for email in members['Email'].values):
            print(f"\nPeer group '{peer_group}':")
            print(f"  Total members: {len(members)}")
            print("  Members:")
            for _, member in members.iterrows():
                print(f"    - {member['Email']} (rank: {member['peer_rank_display']})")
    
    return result


if __name__ == "__main__":
    result_df = test_actual_peer_rank_scenario()
    
    # Additional check: Print the actual peer_rank_display values
    print("\n" + "=" * 70)
    print("ALL PEER RANK DISPLAYS")
    print("=" * 70)
    for _, row in result_df.iterrows():
        print(f"{row['Email']:40} -> {row['peer_rank_display']:15} (size: {row['peer_group_size']})")