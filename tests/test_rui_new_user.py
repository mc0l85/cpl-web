"""Test RUI Calculator handling of new users with grace period"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_new_user_grace_period():
    """Test that new users get grace period regardless of RUI score"""
    
    reference_date = datetime.now()
    
    # Create users including new users
    users_df = pd.DataFrame({
        'Email': ['new1@test.com', 'new2@test.com', 'old1@test.com', 
                 'old2@test.com', 'old3@test.com'],
        'Overall Recency': [
            reference_date - timedelta(days=2),   # New user, recent
            reference_date - timedelta(days=85),  # New user, not recent
            reference_date - timedelta(days=5),   # Old user, recent
            reference_date - timedelta(days=40),  # Old user, medium
            reference_date - timedelta(days=95)   # Old user, very old
        ],
        'Adjusted Consistency (%)': [20, 15, 80, 45, 10],  # New users have low consistency
        'Avg Tools / Report': [2.0, 1.5, 6.0, 3.5, 0.5],
        'Usage Trend': ['New User', 'New User', 'Growing', 'Stable', 'Declining'],
        'Classification': ['New User', 'New User', 'Consistent User', 
                          'Coaching Opportunity', 'License Recapture'],
        'First Appearance': [
            reference_date - timedelta(days=10),   # New (10 days)
            reference_date - timedelta(days=80),   # New (80 days)
            reference_date - timedelta(days=200),  # Old
            reference_date - timedelta(days=150),  # Old
            reference_date - timedelta(days=400)   # Old
        ]
    })
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df)
    
    # Check that new users have grace period classification
    new_user_results = result[result['Classification'] == 'New User']
    
    # All new users should have "Low - New User (Grace Period)" regardless of RUI
    assert all('New User' in risk for risk in new_user_results['license_risk'])
    assert all('Grace Period' in risk for risk in new_user_results['license_risk'])
    
    # Verify new users still get RUI scores calculated (for tracking)
    assert all(pd.notna(new_user_results['rui_score']))
    
    # Old users should have normal risk classifications
    old_user_results = result[result['Classification'] != 'New User']
    assert not any('New User' in risk for risk in old_user_results['license_risk'])


def test_manager_summary_with_new_users():
    """Test that manager summary correctly counts new users"""
    
    reference_date = datetime.now()
    
    # Create team with mix of new and old users
    users_df = pd.DataFrame({
        'Email': [f'user{i}@test.com' for i in range(8)],
        'Overall Recency': [reference_date - timedelta(days=i*20) for i in range(8)],
        'Adjusted Consistency (%)': [90, 80, 30, 20, 70, 60, 15, 10],
        'Avg Tools / Report': [6.0, 5.0, 2.0, 1.5, 4.0, 3.5, 1.0, 0.5],
        'Usage Trend': ['New User', 'New User', 'Declining', 'Declining', 
                       'Growing', 'Stable', 'Declining', 'Declining'],
        'Classification': ['New User', 'New User', 'Coaching Opportunity', 'License Recapture',
                          'Consistent User', 'Coaching Opportunity', 'License Recapture', 'License Recapture']
    })
    
    manager_df = pd.DataFrame({
        'UserPrincipalName': [f'user{i}@test.com' for i in range(8)],
        'ManagerLine': ['Jane Smith -> Brian McNamara'] * 8,
        'Department': ['Engineering'] * 8,
        'Company': ['TestCorp'] * 8,
        'City': ['New York'] * 8
    })
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Generate manager summary
    summary = calculator.get_manager_summary(result)
    
    # Check that New Users column exists
    assert 'New Users' in summary.columns
    
    # Should have 2 new users for Jane Smith
    jane_summary = summary[summary['Manager Name'] == 'Jane Smith']
    assert len(jane_summary) == 1
    assert jane_summary.iloc[0]['New Users'] == 2
    
    # New users should not be counted in High Risk
    assert jane_summary.iloc[0]['High Risk'] < 8  # Less than total team size


def test_90_day_boundary():
    """Test that 90-day boundary is correctly applied"""
    
    reference_date = datetime.now()
    
    users_df = pd.DataFrame({
        'Email': ['89days@test.com', '90days@test.com', '91days@test.com'],
        'Overall Recency': [reference_date - timedelta(days=5)] * 3,
        'Adjusted Consistency (%)': [20, 20, 20],  # All have same low consistency
        'Avg Tools / Report': [1.0, 1.0, 1.0],     # All have same low usage
        'Usage Trend': ['Stable', 'Stable', 'Stable'],
        'First Appearance': [
            reference_date - timedelta(days=89),   # Just under 90 days - NEW
            reference_date - timedelta(days=90),   # Exactly 90 days - NOT NEW
            reference_date - timedelta(days=91)    # Over 90 days - NOT NEW
        ]
    })
    
    # Need to manually set Classification based on the 90-day rule
    # This mimics what get_manager_classification does
    for idx, row in users_df.iterrows():
        days_since_first = (reference_date - row['First Appearance']).days
        if days_since_first < 90:
            users_df.at[idx, 'Classification'] = 'New User'
        else:
            users_df.at[idx, 'Classification'] = 'Coaching Opportunity'
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df)
    
    # User at 89 days should have grace period
    user_89 = result[result['Email'] == '89days@test.com'].iloc[0]
    assert 'New User' in user_89['license_risk']
    assert 'Grace Period' in user_89['license_risk']
    
    # Users at 90+ days should not have grace period
    user_90 = result[result['Email'] == '90days@test.com'].iloc[0]
    assert 'New User' not in user_90['license_risk']
    
    user_91 = result[result['Email'] == '91days@test.com'].iloc[0]
    assert 'New User' not in user_91['license_risk']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])