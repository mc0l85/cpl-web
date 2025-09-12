#!/usr/bin/env python3
"""Test what happens if James Peterson is also in the users dataset"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rui_calculator import RUICalculator

def test_manager_as_peer():
    """Test what happens when a manager also has a Copilot license"""
    
    reference_date = datetime.now()
    
    # Scenario: James Peterson ALSO has a Copilot license
    users_data = [
        # Mark reports to James
        {
            'Email': 'mark.x.rothfuss@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara'
        },
        # James Peterson HIMSELF (this would be the bug)
        {
            'Email': 'james.peterson@haleon.com',  # Hypothetical email
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara'  # James reports to Dan
        },
        # Jenn and Bryce report to Pariss
        {
            'Email': 'jenn.x.cooney@haleon.com',
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara'
        },
        {
            'Email': 'bryce.x.weiberg@haleon.com',
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara'
        }
    ]
    
    # Add default columns
    for user in users_data:
        user.update({
            'Overall Recency': reference_date - timedelta(days=5),
            'Adjusted Consistency (%)': 65,
            'Avg Tools / Report': 4.5,
            'Usage Trend': 'Stable'
        })
    
    users_df = pd.DataFrame(users_data)
    
    manager_df = pd.DataFrame([
        {'UserPrincipalName': user['Email'], 
         'ManagerLine': user['ManagerLine'],
         'Department': 'QSC',
         'Company': 'Haleon',
         'City': 'Lincoln NE'}
        for user in users_data
    ])
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    print("=== SCENARIO: James Peterson has a Copilot license too ===")
    
    for _, row in result.iterrows():
        print(f"\n{row['Email']}:")
        print(f"  Peer Group: {row['peer_group']}")
        print(f"  Peer Group Type: {row['peer_group_type']}")
        print(f"  Peer Group Size: {row['peer_group_size']}")
    
    print(f"\nAll users in the system: {result['Email'].tolist()}")
    
    # Show peer group assignments
    for group in result['peer_group'].unique():
        group_members = result[result['peer_group'] == group]['Email'].tolist()
        print(f"\nPeer group '{group}': {group_members}")
    
    print("\n=== ANALYSIS ===")
    mark_result = result[result['Email'] == 'mark.x.rothfuss@haleon.com'].iloc[0]
    peers_in_marks_group = result[result['peer_group'] == mark_result['peer_group']]['Email'].tolist()
    
    print(f"Mark's peers: {peers_in_marks_group}")
    
    if 'james.peterson@haleon.com' in peers_in_marks_group:
        print("❌ BUG FOUND: James Peterson (Mark's manager) is in Mark's peer group!")
        print("   This means the system is treating Mark's manager as his peer.")
    else:
        print("✅ James Peterson is NOT in Mark's peer group (correct behavior)")

if __name__ == '__main__':
    test_manager_as_peer()