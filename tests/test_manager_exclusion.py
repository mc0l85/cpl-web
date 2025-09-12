"""Test that managers are properly excluded from subordinate peer groups"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_manager_not_peer_of_subordinate():
    """Test that James Peterson is not included as Mark Rothfuss's peer"""
    
    reference_date = datetime.now()
    
    # Create users including Mark, his peers, and James Peterson (his manager)
    users_data = [
        # Mark Rothfuss
        {
            'Email': 'mark.x.rothfuss@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=5),
            'Adjusted Consistency (%)': 70,
            'Avg Tools / Report': 4.0,
            'Usage Trend': 'Stable'
        },
        # James Peterson (Mark's manager) - also has a license
        {
            'Email': 'james.x.peterson@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=2),
            'Adjusted Consistency (%)': 85,
            'Avg Tools / Report': 6.0,
            'Usage Trend': 'Growing'
        },
        # Other people who report to James (Mark's actual peers)
        {
            'Email': 'peer1.x.user@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=10),
            'Adjusted Consistency (%)': 60,
            'Avg Tools / Report': 3.5,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'peer2.x.user@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=7),
            'Adjusted Consistency (%)': 65,
            'Avg Tools / Report': 3.8,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'peer3.x.user@haleon.com',
            'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=3),
            'Adjusted Consistency (%)': 75,
            'Avg Tools / Report': 4.5,
            'Usage Trend': 'Growing'
        },
        # Dan Basile's other direct reports (organizational cousins)
        {
            'Email': 'pariss.x.bethune@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=4),
            'Adjusted Consistency (%)': 80,
            'Avg Tools / Report': 5.0,
            'Usage Trend': 'Stable'
        },
        # People under Pariss (to make the org structure more realistic)
        {
            'Email': 'jenn.x.cooney@haleon.com',
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=6),
            'Adjusted Consistency (%)': 72,
            'Avg Tools / Report': 4.2,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'bryce.x.weiberg@haleon.com',
            'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen',
            'Overall Recency': reference_date - timedelta(days=8),
            'Adjusted Consistency (%)': 68,
            'Avg Tools / Report': 3.9,
            'Usage Trend': 'Stable'
        }
    ]
    
    users_df = pd.DataFrame(users_data)
    
    # Create manager data
    manager_df = pd.DataFrame([
        {
            'UserPrincipalName': user['Email'],
            'ManagerLine': user['ManagerLine'],
            'Department': 'CH Quality & Supply Chain',
            'Company': 'Haleon',
            'City': 'Lincoln NE'
        }
        for user in users_data
    ])
    
    # Calculate RUI
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Get Mark's result
    mark_result = result[result['Email'] == 'mark.x.rothfuss@haleon.com'].iloc[0]
    
    # Get James's result (his manager)
    james_result = result[result['Email'] == 'james.x.peterson@haleon.com'].iloc[0]
    
    # Mark's peer group should NOT be the same as James's
    assert mark_result['peer_group'] != james_result['peer_group'], \
        f"Mark and his manager James should not be in the same peer group"
    
    # Mark should be compared to 3 other people under James (not including James himself)
    # Since we only have 4 people under James (Mark + 3 peers), this is too small
    # So it should escalate to skip-level peers (all under Dan Basile except managers)
    assert mark_result['peer_group_type'] == 'Skip-Level Peers', \
        f"Mark should be in skip-level peer group, got {mark_result['peer_group_type']}"
    
    # The peer group should include Mark, his 3 peers, Jenn, and Bryce (6 total)
    # But NOT James or Pariss (the managers)
    assert mark_result['peer_group_size'] == 6, \
        f"Mark's peer group should have 6 members (excluding managers), got {mark_result['peer_group_size']}"
    
    print(f"✓ Mark's peer group: {mark_result['peer_group_type']} with {mark_result['peer_group_size']} members")
    print(f"✓ James (manager) is correctly excluded from Mark's peer group")


def test_manager_with_subordinates_peer_group():
    """Test that managers with 5+ subordinates compare with their subordinates"""
    
    reference_date = datetime.now()
    
    # Create Dan Basile with his direct reports
    users_data = [
        # Dan Basile (manager with subordinates)
        {
            'Email': 'dan.x.basile@haleon.com',
            'ManagerLine': 'Peter Obasa -> Mike Allen -> Alvaro Cantillo',
            'Overall Recency': reference_date - timedelta(days=1),
            'Adjusted Consistency (%)': 90,
            'Avg Tools / Report': 7.0,
            'Usage Trend': 'Growing'
        },
        # Dan's direct reports
        {
            'Email': 'james.x.peterson@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo',
            'Overall Recency': reference_date - timedelta(days=2),
            'Adjusted Consistency (%)': 85,
            'Avg Tools / Report': 6.0,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'pariss.x.bethune@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo',
            'Overall Recency': reference_date - timedelta(days=3),
            'Adjusted Consistency (%)': 80,
            'Avg Tools / Report': 5.5,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'manager3@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo',
            'Overall Recency': reference_date - timedelta(days=4),
            'Adjusted Consistency (%)': 75,
            'Avg Tools / Report': 5.0,
            'Usage Trend': 'Stable'
        },
        {
            'Email': 'manager4@haleon.com',
            'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo',
            'Overall Recency': reference_date - timedelta(days=5),
            'Adjusted Consistency (%)': 70,
            'Avg Tools / Report': 4.5,
            'Usage Trend': 'Declining'
        }
    ]
    
    users_df = pd.DataFrame(users_data)
    
    manager_df = pd.DataFrame([
        {
            'UserPrincipalName': user['Email'],
            'ManagerLine': user['ManagerLine'],
            'Department': 'CH Quality & Supply Chain',
            'Company': 'Haleon',
            'City': 'Lincoln NE'
        }
        for user in users_data
    ])
    
    # Calculate RUI
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Get Dan's result
    dan_result = result[result['Email'] == 'dan.x.basile@haleon.com'].iloc[0]
    
    # Dan should be compared with his subordinates (self + subordinates strategy)
    assert dan_result['peer_group_type'] == 'Self + Subordinates', \
        f"Dan should use Self + Subordinates strategy, got {dan_result['peer_group_type']}"
    
    # Should include Dan + his 4 direct reports = 5 total
    assert dan_result['peer_group_size'] == 5, \
        f"Dan's peer group should have 5 members, got {dan_result['peer_group_size']}"
    
    print(f"✓ Dan's peer group: {dan_result['peer_group_type']} with {dan_result['peer_group_size']} members")


if __name__ == '__main__':
    test_manager_not_peer_of_subordinate()
    test_manager_with_subordinates_peer_group()
    print("\n✓ All manager exclusion tests passed!")