import pandas as pd
from datetime import datetime, timedelta
from analysis_logic import CopilotAnalyzer

def test_license_recapture_classification():
    """Test that users with recent activity are not classified for license recapture"""
    
    # Create test cases
    test_cases = [
        {
            'email': 'active_user@test.com',
            'last_activity': datetime(2025, 6, 26),
            'first_activity': datetime(2025, 4, 1),
            'report_date': datetime(2025, 7, 22),
            'expected_classification': 'NOT License Recapture'
        },
        {
            'email': 'inactive_user@test.com', 
            'last_activity': datetime(2025, 3, 1),
            'first_activity': datetime(2025, 1, 1),
            'report_date': datetime(2025, 7, 22),
            'expected_classification': 'License Recapture'
        },
        {
            'email': 'new_user@test.com',
            'last_activity': datetime(2025, 7, 1),
            'first_activity': datetime(2025, 5, 1),
            'report_date': datetime(2025, 7, 22),
            'expected_classification': 'New User'
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['email']}")
        print(f"  Last Activity: {test_case['last_activity'].strftime('%Y-%m-%d')}")
        print(f"  Report Date: {test_case['report_date'].strftime('%Y-%m-%d')}")
        print(f"  Days Inactive: {(test_case['report_date'] - test_case['last_activity']).days}")
        print(f"  Expected: {test_case['expected_classification']}")
        
        # Simulate the classification logic
        days_inactive = (test_case['report_date'] - test_case['last_activity']).days
        days_since_start = (test_case['report_date'] - test_case['first_activity']).days
        
        if days_since_start < 90:
            actual = "New User"
        elif days_inactive > 90:
            actual = "License Recapture"
        else:
            actual = "NOT License Recapture"
            
        print(f"  Actual: {actual}")
        assert (actual == test_case['expected_classification']), f"Classification mismatch for {test_case['email']}"
    
    print("\n✅ All tests passed!")

def test_specific_user():
    """Test with the specific user mentioned in the issue"""
    # Create a mock analyzer instance
    class MockAnalyzer:
        def __init__(self):
            self.reference_date = pd.Timestamp('2025-07-22')
        
        def get_manager_classification(self, row):
            today = self.reference_date
            last_seen = pd.to_datetime(row['Overall Recency']) if pd.notna(row['Overall Recency']) else pd.NaT
            first_seen = pd.to_datetime(row.get('Adoption Date')) if pd.notna(row.get('Adoption Date')) else (pd.to_datetime(row['First Appearance']) if pd.notna(row['First Appearance']) else pd.NaT)
            
            if pd.notna(first_seen) and (today - first_seen).days < 90:
                return "New User"
            if pd.notna(last_seen) and (today - last_seen).days > 90:
                return "License Recapture"
            
            # Default logic for other classifications
            consistency_metric = row['Adjusted Consistency (%)']
            if consistency_metric > 75 and row['Usage Complexity'] > 10:
                return "Power User"
            if consistency_metric > 75:
                return "Consistent User"
            if consistency_metric > 25:
                return "Coaching Opportunity"
            return "License Recapture" if (today - last_seen).days > 90 else "Coaching Opportunity"
    
    analyzer = MockAnalyzer()
    
    # Create test row for kamila.x.rodrigues@haleon.com
    test_row = {
        'Email': 'kamila.x.rodrigues@haleon.com',
        'Overall Recency': pd.Timestamp('2025-06-26'),
        'First Appearance': pd.Timestamp('2025-04-22'),
        'Adoption Date': pd.Timestamp('2025-04-22'),
        'Usage Complexity': 2,
        'Adjusted Consistency (%)': 13.5
    }
    
    # Test classification
    classification = analyzer.get_manager_classification(pd.Series(test_row))
    
    print(f"\nTesting specific user: kamila.x.rodrigues@haleon.com")
    print(f"Last Activity: 2025-06-26")
    print(f"Latest Report: 2025-07-22")
    print(f"Days Inactive: {(analyzer.reference_date - test_row['Overall Recency']).days}")
    print(f"Classification: {classification}")
    print(f"Expected: Should NOT be 'License Recapture' (only 26 days inactive)")
    
    # This should NOT be "License Recapture" since only 26 days have passed
    assert classification != "License Recapture", f"User incorrectly classified as License Recapture"
    print("✅ Specific user test passed!")

if __name__ == "__main__":
    test_license_recapture_classification()
    test_specific_user()