#!/usr/bin/env python3
"""Detailed debug of peer group logic"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rui_calculator import RUICalculator

def analyze_peer_group_logic():
    """Analyze exactly what the peer group logic is doing"""
    
    reference_date = datetime.now()
    
    # Recreate the exact scenario from manager.tree
    users_data = [
        {
            'Email': 'mark.x.rothfuss@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara'
        },
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
    
    print("=== MANAGER HIERARCHY ANALYSIS ===")
    for _, user in users_df.iterrows():
        email = user['Email']
        manager_line = user['ManagerLine']
        managers = [m.strip() for m in manager_line.split('->')]
        
        print(f"\n{email}:")
        print(f"  Manager Line: {manager_line}")
        print(f"  Immediate Manager (position 0): {managers[0]}")
        print(f"  Skip Manager (position 1): {managers[1] if len(managers) > 1 else 'N/A'}")
    
    print("\n=== STRATEGY 2: Direct Peers Under Same Manager ===")
    # For each user, find others with same immediate manager
    for _, user in users_df.iterrows():
        email = user['Email']
        manager_line = user['ManagerLine']
        managers = [m.strip() for m in manager_line.split('->')]
        
        if len(managers) >= 1:
            immediate_manager = managers[0]
            
            # Find peers with same immediate manager
            peers = users_df[users_df['ManagerLine'].apply(
                lambda x: x.split('->')[0].strip() == immediate_manager if pd.notna(x) and '->' in x else False
            )]
            
            print(f"\n{email} (reports to {immediate_manager}):")
            print(f"  Peers under {immediate_manager}: {peers['Email'].tolist()}")
            print(f"  Count: {len(peers)} (min required: 5)")
            print(f"  Strategy 2 applicable: {len(peers) >= 5}")
    
    print("\n=== STRATEGY 3: Skip-Level Peers ===")
    # For each user, find others with same skip-level manager
    for _, user in users_df.iterrows():
        email = user['Email']
        manager_line = user['ManagerLine']
        managers = [m.strip() for m in manager_line.split('->')]
        
        if len(managers) >= 2:
            skip_manager = managers[1]
            
            # Find peers with same skip-level manager
            peers = users_df[users_df['ManagerLine'].apply(
                lambda x: x.split('->')[1].strip() == skip_manager if pd.notna(x) and '->' in x and len(x.split('->')) >= 2 else False
            )]
            
            print(f"\n{email} (skip-manager: {skip_manager}):")
            print(f"  Skip-level peers under {skip_manager}: {peers['Email'].tolist()}")
            print(f"  Count: {len(peers)} (min required: 5)")
            print(f"  Strategy 3 applicable: {len(peers) >= 5}")
    
    print("\n=== THE PROBLEM ===")
    print("Mark Rothfuss should have peers that include:")
    print("1. Anyone else who reports to James Peterson (his direct manager)")
    print("2. If James has no other direct reports with licenses, then Mark should be")
    print("   compared to his 'organizational cousins' - people at the same level")
    print("   (i.e., other people who report to managers who are peers of James)")
    print("")
    print("In this case:")
    print("- Mark reports to James Peterson")
    print("- Jenn & Bryce report to Pariss Bethune") 
    print("- James Peterson and Pariss Bethune are BOTH subordinates of Dan Basile")
    print("- Therefore James and Pariss are organizational peers")
    print("- So Mark, Jenn, and Bryce should be organizational cousins")
    print("")
    print("The current algorithm finds this correctly via Strategy 3 (skip-level peers)")
    print("But the user says 'James P is Mark's boss, but the system treats James as a peer'")
    print("This suggests the UI or reporting might be incorrectly showing James in the peer list")

if __name__ == '__main__':
    analyze_peer_group_logic()