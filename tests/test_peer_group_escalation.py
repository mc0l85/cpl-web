"""Test proper peer group escalation to avoid overly broad comparisons"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_alvaro_scenario():
    """Test that Alvaro's team isn't compared to all 200+ people under Namrata"""
    
    reference_date = datetime.now()
    
    # Create a realistic org structure:
    # Namrata Patel (top)
    #   -> Alvaro Cantillo (4 direct reports)
    #   -> Other Manager 1 (50 reports)
    #   -> Other Manager 2 (50 reports)
    #   -> Other Manager 3 (50 reports)
    #   -> Other Manager 4 (50 reports)
    
    users_data = []
    
    # Alvaro's 4 direct reports
    for i in range(4):
        users_data.append({
            'Email': f'alvaro_team_{i}@test.com',
            'ManagerLine': 'Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
            'Overall Recency': reference_date - timedelta(days=i*5),
            'Adjusted Consistency (%)': 60 + i*5,
            'Avg Tools / Report': 4.0 + i*0.5,
            'Usage Trend': 'Stable'
        })
    
    # Other managers' teams (200+ people total under Namrata)
    for mgr_num in range(1, 5):
        for i in range(50):
            users_data.append({
                'Email': f'other_mgr{mgr_num}_team_{i}@test.com',
                'ManagerLine': f'Other Manager {mgr_num} -> Namrata Patel -> Brian McNamara',
                'Overall Recency': reference_date - timedelta(days=i),
                'Adjusted Consistency (%)': 50 + i,
                'Avg Tools / Report': 3.0 + i*0.1,
                'Usage Trend': 'Stable'
            })
    
    users_df = pd.DataFrame(users_data)
    
    # Create manager data
    manager_data = []
    for user in users_data:
        manager_data.append({
            'UserPrincipalName': user['Email'],
            'ManagerLine': user['ManagerLine'],
            'Department': 'QSC',
            'Company': 'TestCorp',
            'City': 'New York'
        })
    
    manager_df = pd.DataFrame(manager_data)
    
    # Calculate RUI
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Check Alvaro's team peer groups
    alvaro_team = result[result['Email'].str.startswith('alvaro_team')]
    
    # Alvaro's team should be compared to skip-level peers (others under Namrata)
    # NOT just among themselves (only 4 people)
    # But also NOT to all 200+ people
    
    # They should be in a skip-level peer group since direct team is too small
    assert all(alvaro_team['peer_group_type'] == 'Skip-Level Peers')
    
    # The peer group should include others at the same level (under Namrata)
    # This should be ~204 people (4 from Alvaro + 200 from other managers)
    assert all(alvaro_team['peer_group_size'] == len(users_df))
    
    # Verify the peer group name references Namrata (skip-level)
    assert all('Namrata Patel' in pg for pg in alvaro_team['peer_group'])


def test_sufficient_direct_team():
    """Test that teams with 5+ members use direct manager comparison"""
    
    reference_date = datetime.now()
    
    # Create a team with exactly 5 members
    users_data = []
    for i in range(5):
        users_data.append({
            'Email': f'team_member_{i}@test.com',
            'ManagerLine': 'Direct Manager -> Skip Manager -> Top Manager',
            'Overall Recency': reference_date - timedelta(days=i*5),
            'Adjusted Consistency (%)': 60 + i*5,
            'Avg Tools / Report': 4.0 + i*0.5,
            'Usage Trend': 'Stable'
        })
    
    # Add some other teams for context
    for i in range(10):
        users_data.append({
            'Email': f'other_team_{i}@test.com',
            'ManagerLine': 'Other Manager -> Skip Manager -> Top Manager',
            'Overall Recency': reference_date - timedelta(days=i),
            'Adjusted Consistency (%)': 50,
            'Avg Tools / Report': 3.0,
            'Usage Trend': 'Stable'
        })
    
    users_df = pd.DataFrame(users_data)
    
    manager_df = pd.DataFrame([
        {'UserPrincipalName': user['Email'], 
         'ManagerLine': user['ManagerLine'],
         'Department': 'Tech',
         'Company': 'TestCorp',
         'City': 'NYC'}
        for user in users_data
    ])
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Check that the 5-person team uses direct manager comparison
    direct_team = result[result['Email'].str.startswith('team_member')]
    
    # Should be compared only to their direct team
    assert all(direct_team['peer_group_type'] == 'Direct Manager Team')
    assert all(direct_team['peer_group_size'] == 5)
    
    # Should NOT be compared to the broader organization
    assert all(direct_team['peer_group_size'] != len(users_df))


def test_small_team_escalation():
    """Test that teams with <5 members escalate to skip-level peers"""
    
    reference_date = datetime.now()
    
    # Create a small team (3 members)
    users_data = []
    for i in range(3):
        users_data.append({
            'Email': f'small_team_{i}@test.com',
            'ManagerLine': 'Small Team Mgr -> Middle Mgr -> Top Mgr',
            'Overall Recency': reference_date - timedelta(days=i*5),
            'Adjusted Consistency (%)': 70,
            'Avg Tools / Report': 5.0,
            'Usage Trend': 'Stable'
        })
    
    # Add other teams under the same middle manager
    for team_num in range(1, 4):
        for i in range(6):
            users_data.append({
                'Email': f'peer_team{team_num}_{i}@test.com',
                'ManagerLine': f'Peer Mgr {team_num} -> Middle Mgr -> Top Mgr',
                'Overall Recency': reference_date - timedelta(days=i),
                'Adjusted Consistency (%)': 60,
                'Avg Tools / Report': 4.0,
                'Usage Trend': 'Stable'
            })
    
    users_df = pd.DataFrame(users_data)
    
    manager_df = pd.DataFrame([
        {'UserPrincipalName': user['Email'], 
         'ManagerLine': user['ManagerLine'],
         'Department': 'Ops',
         'Company': 'TestCorp',
         'City': 'SF'}
        for user in users_data
    ])
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Check the small team's peer groups
    small_team = result[result['Email'].str.startswith('small_team')]
    
    # Should escalate to skip-level peers (all under Middle Mgr)
    assert all(small_team['peer_group_type'] == 'Skip-Level Peers')
    
    # Should include all teams under Middle Mgr (3 + 18 = 21)
    assert all(small_team['peer_group_size'] == 21)
    
    # Verify they're not compared globally
    assert all(small_team['peer_group_size'] < len(users_df))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])