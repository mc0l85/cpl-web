"""Test RUI Calculator functionality"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rui_calculator import RUICalculator


def test_rui_calculator_basic():
    """Test basic RUI calculation without manager data"""
    
    # Create test data
    reference_date = datetime.now()
    
    users_df = pd.DataFrame({
        'Email': ['user1@test.com', 'user2@test.com', 'user3@test.com'],
        'Overall Recency': [
            reference_date - timedelta(days=5),   # Recent user
            reference_date - timedelta(days=30),  # Medium recency
            reference_date - timedelta(days=90)   # Old activity
        ],
        'Adjusted Consistency (%)': [80, 50, 20],
        'Avg Tools / Report': [5.0, 3.0, 1.0],
        'Usage Trend': ['Growing', 'Stable', 'Declining']
    })
    
    # Initialize calculator
    calculator = RUICalculator(reference_date)
    
    # Calculate RUI scores
    result = calculator.calculate_rui_scores(users_df)
    
    # Verify columns exist
    assert 'rui_score' in result.columns
    assert 'license_risk' in result.columns
    assert 'peer_rank_display' in result.columns
    assert 'trend_arrow' in result.columns
    
    # Verify RUI scores are in range
    assert all(0 <= score <= 100 for score in result['rui_score'])
    
    # Verify risk classifications
    assert all(risk in ['High - Reclaim', 'Medium - Review', 'Low - Retain'] 
              for risk in result['license_risk'])
    
    # User 1 should have highest RUI (best metrics)
    assert result.iloc[0]['rui_score'] > result.iloc[2]['rui_score']


def test_rui_calculator_with_managers():
    """Test RUI calculation with manager hierarchy"""
    
    reference_date = datetime.now()
    
    # Create users with same manager
    users_df = pd.DataFrame({
        'Email': [f'user{i}@test.com' for i in range(6)],
        'Overall Recency': [reference_date - timedelta(days=i*10) for i in range(6)],
        'Adjusted Consistency (%)': [90, 80, 70, 60, 50, 40],
        'Avg Tools / Report': [6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
        'Usage Trend': ['Growing', 'Growing', 'Stable', 'Stable', 'Declining', 'Declining']
    })
    
    # Create manager data
    manager_df = pd.DataFrame({
        'UserPrincipalName': [f'user{i}@test.com' for i in range(6)],
        'ManagerLine': ['John Doe -> Brian McNamara'] * 6,
        'Department': ['Engineering'] * 6,
        'Company': ['TestCorp'] * 6,
        'City': ['New York'] * 6,
        'JobTitle': ['Engineer'] * 6
    })
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Check manager data was merged
    assert 'ManagerLine' in result.columns
    assert 'Department' in result.columns
    
    # Check peer groups were formed
    assert 'peer_group' in result.columns
    assert 'peer_group_size' in result.columns
    
    # All users should be in same peer group (same manager)
    assert len(result['peer_group'].unique()) == 1
    assert all(result['peer_group_size'] == 6)
    
    # Verify peer rankings make sense
    # User 0 should have best rank (1 of 6)
    assert '1 of 6' in result.iloc[0]['peer_rank_display']
    # User 5 should have worst rank (6 of 6)
    assert '6 of 6' in result.iloc[5]['peer_rank_display']


def test_rui_risk_classification():
    """Test that risk classifications are applied correctly"""
    
    reference_date = datetime.now()
    
    # Create enough users to meet minimum peer group size (5)
    users_df = pd.DataFrame({
        'Email': ['high_risk@test.com', 'medium_risk1@test.com', 'medium_risk2@test.com', 
                 'low_risk1@test.com', 'low_risk2@test.com'],
        'Overall Recency': [
            reference_date - timedelta(days=90),  # Very old
            reference_date - timedelta(days=30),  # Medium
            reference_date - timedelta(days=15),  # Medium
            reference_date - timedelta(days=2),   # Recent
            reference_date - timedelta(days=1)    # Very recent
        ],
        'Adjusted Consistency (%)': [10, 35, 45, 75, 90],  # Low to High
        'Avg Tools / Report': [0.5, 2.0, 3.0, 6.0, 8.0],   # Low to High
        'Usage Trend': ['Declining', 'Declining', 'Stable', 'Growing', 'Growing']
    })
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df)
    
    # Sort by RUI score
    result = result.sort_values('rui_score')
    
    # Lowest RUI should be High Risk (RUI < 20)
    assert result.iloc[0]['rui_score'] < 20
    assert 'High' in result.iloc[0]['license_risk']
    
    # Highest RUI should be Low Risk (RUI >= 40)
    assert result.iloc[-1]['rui_score'] >= 40
    assert 'Low' in result.iloc[-1]['license_risk']


def test_manager_summary():
    """Test manager summary generation"""
    
    reference_date = datetime.now()
    
    # Create users across two managers
    users_df = pd.DataFrame({
        'Email': [f'user{i}@test.com' for i in range(8)],
        'Overall Recency': [reference_date - timedelta(days=i*15) for i in range(8)],
        'Adjusted Consistency (%)': [90, 80, 30, 20, 70, 60, 15, 10],
        'Avg Tools / Report': [6.0, 5.0, 2.0, 1.5, 4.0, 3.5, 1.0, 0.5],
        'Usage Trend': ['Growing', 'Stable', 'Declining', 'Declining', 
                       'Growing', 'Stable', 'Declining', 'Declining']
    })
    
    manager_df = pd.DataFrame({
        'UserPrincipalName': [f'user{i}@test.com' for i in range(8)],
        'ManagerLine': ['Jane Smith -> Brian McNamara'] * 4 + ['John Doe -> Brian McNamara'] * 4,
        'Department': ['Engineering'] * 8,
        'Company': ['TestCorp'] * 8,
        'City': ['New York'] * 8,
        'JobTitle': ['Engineer'] * 8
    })
    
    calculator = RUICalculator(reference_date)
    result = calculator.calculate_rui_scores(users_df, manager_df)
    
    # Generate manager summary
    summary = calculator.get_manager_summary(result)
    
    # Should have 2 managers
    assert len(summary) == 2
    
    # Check columns exist
    assert 'Manager Name' in summary.columns
    assert 'Team Size' in summary.columns
    assert 'Avg RUI' in summary.columns
    assert 'High Risk' in summary.columns
    assert 'Medium Risk' in summary.columns
    assert 'Low Risk' in summary.columns
    
    # Each manager should have 4 team members
    assert all(summary['Team Size'] == 4)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])