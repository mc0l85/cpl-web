#!/usr/bin/env python3
"""Debug script to understand Mark Rothfuss peer group issue"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rui_calculator import RUICalculator

def debug_mark_rothfuss_peers():
    """Debug Mark Rothfuss's peer group formation"""
    
    reference_date = datetime.now()
    
    # Create the actual org structure based on manager.tree data
    users_data = [
        # Mark Rothfuss - reports to James Peterson
        {
            'Email': 'mark.x.rothfuss@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=5),
            'Adjusted Consistency (%)': 65,
            'Avg Tools / Report': 4.5,
            'Usage Trend': 'Stable'
        },
        # Jenn Cooney - reports to Pariss Bethune (Dan Basile's other direct report)  
        {
            'Email': 'jenn.x.cooney@haleon.com',
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=3),
            'Adjusted Consistency (%)': 70,
            'Avg Tools / Report': 5.0,
            'Usage Trend': 'Growing'
        },
        # Bryce Weiberg - also reports to Pariss Bethune
        {
            'Email': 'bryce.x.weiberg@haleon.com', 
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=7),
            'Adjusted Consistency (%)': 60,
            'Avg Tools / Report': 4.0,
            'Usage Trend': 'Declining'
        }
    ]
    
    # Add some hypothetical peers under James Peterson if they existed
    # (These are the peers that SHOULD exist according to the user)
    hypothetical_james_peers = [
        {
            'Email': 'peer1.under.james@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=4),
            'Adjusted Consistency (%)': 68,
            'Avg Tools / Report': 4.2,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'peer2.under.james@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=2),
            'Adjusted Consistency (%)': 72,
            'Avg Tools / Report': 4.8,
            'Usage Trend': 'Growing'
        },
        {
            'Email': 'peer3.under.james@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=6),
            'Adjusted Consistency (%)': 62,
            'Avg Tools / Report': 4.1,
            'Usage Trend': 'Stable'
        }
    ]
    
    print("=== SCENARIO 1: Only Mark has a license under James Peterson ===")
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
    
    mark_result = result[result['Email'] == 'mark.x.rothfuss@haleon.com'].iloc[0]
    
    print(f"Mark's peer group: {mark_result['peer_group']}")
    print(f"Mark's peer group type: {mark_result['peer_group_type']}")
    print(f"Mark's peer group size: {mark_result['peer_group_size']}")
    print(f"Peers in group: {result[result['peer_group'] == mark_result['peer_group']]['Email'].tolist()}")
    
    print("\n=== SCENARIO 2: Mark + 3 hypothetical peers under James Peterson ===")
    users_with_peers = users_data + hypothetical_james_peers
    users_df2 = pd.DataFrame(users_with_peers)
    
    manager_df2 = pd.DataFrame([
        {'UserPrincipalName': user['Email'], 
         'ManagerLine': user['ManagerLine'],
         'Department': 'QSC',
         'Company': 'Haleon',
         'City': 'Lincoln NE'}
        for user in users_with_peers
    ])
    
    result2 = calculator.calculate_rui_scores(users_df2, manager_df2)
    mark_result2 = result2[result2['Email'] == 'mark.x.rothfuss@haleon.com'].iloc[0]
    
    print(f"Mark's peer group: {mark_result2['peer_group']}")
    print(f"Mark's peer group type: {mark_result2['peer_group_type']}")
    print(f"Mark's peer group size: {mark_result2['peer_group_size']}")
    print(f"Peers in group: {result2[result2['peer_group'] == mark_result2['peer_group']]['Email'].tolist()}")
    
    print("\n=== ANALYSIS ===")
    print("The issue is likely that:")
    print("1. Mark is the ONLY person with a Copilot license who reports to James Peterson")
    print("2. Since direct team size is 1 (< MIN_PEER_GROUP_SIZE of 5), the algorithm escalates")
    print("3. It escalates to skip-level peers (people under Dan Basile)")
    print("4. This includes Jenn and Bryce who report to Pariss Bethune")
    print("5. But this logic treats James Peterson and Pariss Bethune as peers instead of")
    print("   recognizing that James is Mark's direct manager")

if __name__ == '__main__':
    debug_mark_rothfuss_peers()