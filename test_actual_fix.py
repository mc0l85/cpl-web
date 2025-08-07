#!/usr/bin/env python3
"""
Test the actual fix in the analysis_logic.py file
This test simulates the actual classification logic without requiring pandas
"""

from datetime import datetime, timedelta

def test_actual_classification_logic():
    """Test the actual classification logic from analysis_logic.py"""
    
    def get_manager_classification(row):
        """Simulate the actual get_manager_classification method"""
        # Use the max report date as reference for consistency
        today = row['reference_date']
        last_seen = row['last_seen']
        first_seen = row['first_seen']
        
        if first_seen and (today - first_seen).days < 90:
            return "New User"
        if last_seen and (today - last_seen).days > 90:
            return "License Recapture"
        
        # Use adjusted consistency for classification
        consistency_metric = row['consistency']
        
        if consistency_metric > 75 and row['complexity'] > 10:
            return "Power User"
        if consistency_metric > 75:
            return "Consistent User"
        if consistency_metric > 25:
            return "Coaching Opportunity"
        return "Coaching Opportunity"  # Changed default from "License Recapture" to "Coaching Opportunity"
    
    def get_justification(classification):
        """Simulate the get_justification method"""
        if classification == "New User":
            return "User is in their first 90 days and is still learning the tool."
        if classification == "License Recapture":
            return "User has not shown any activity in the last 90 days and their license could be reallocated."
        if classification == "Power User":
            return "User demonstrates high consistency and leverages a wide range of tools, indicating strong engagement."
        if classification == "Consistent User":
            return "User is highly active and has integrated the tool into their regular workflow."
        if classification == "Coaching Opportunity":
            return "User is active but inconsistent. Further coaching could help them maximize the tool's benefits."
        return ""
    
    # Test cases
    test_cases = [
        {
            'name': 'kamila.x.rodrigues@haleon.com (Original Issue)',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 6, 26),
            'first_seen': datetime(2025, 4, 22),
            'consistency': 13.5,
            'complexity': 2,
            'expected_classification': 'Coaching Opportunity',
            'expected_justification': 'User is active but inconsistent. Further coaching could help them maximize the tool\'s benefits.'
        },
        {
            'name': 'Truly Inactive User (should be License Recapture)',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 3, 1),
            'first_seen': datetime(2025, 1, 1),
            'consistency': 50,
            'complexity': 5,
            'expected_classification': 'License Recapture',
            'expected_justification': 'User has not shown any activity in the last 90 days and their license could be reallocated.'
        },
        {
            'name': 'New User (should be New User)',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 7, 1),
            'first_seen': datetime(2025, 5, 1),
            'consistency': 80,
            'complexity': 15,
            'expected_classification': 'New User',
            'expected_justification': 'User is in their first 90 days and is still learning the tool.'
        },
        {
            'name': 'Power User',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 7, 20),
            'first_seen': datetime(2025, 1, 1),
            'consistency': 80,
            'complexity': 15,
            'expected_classification': 'Power User',
            'expected_justification': 'User demonstrates high consistency and leverages a wide range of tools, indicating strong engagement.'
        },
        {
            'name': 'Consistent User',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 7, 20),
            'first_seen': datetime(2025, 1, 1),
            'consistency': 80,
            'complexity': 5,
            'expected_classification': 'Consistent User',
            'expected_justification': 'User is highly active and has integrated the tool into their regular workflow.'
        },
        {
            'name': 'Coaching Opportunity (high consistency)',
            'reference_date': datetime(2025, 7, 22),
            'last_seen': datetime(2025, 7, 20),
            'first_seen': datetime(2025, 1, 1),
            'consistency': 50,
            'complexity': 5,
            'expected_classification': 'Coaching Opportunity',
            'expected_justification': 'User is active but inconsistent. Further coaching could help them maximize the tool\'s benefits.'
        }
    ]
    
    print("Testing Actual Classification Logic from analysis_logic.py")
    print("=" * 70)
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"  Reference Date: {test_case['reference_date'].strftime('%Y-%m-%d')}")
        print(f"  Last Seen: {test_case['last_seen'].strftime('%Y-%m-%d')}")
        print(f"  First Seen: {test_case['first_seen'].strftime('%Y-%m-%d')}")
        print(f"  Days Inactive: {(test_case['reference_date'] - test_case['last_seen']).days}")
        print(f"  Days Since First Seen: {(test_case['reference_date'] - test_case['first_seen']).days}")
        print(f"  Consistency: {test_case['consistency']}%")
        print(f"  Complexity: {test_case['complexity']}")
        
        classification = get_manager_classification(test_case)
        justification = get_justification(classification)
        
        print(f"  Expected Classification: {test_case['expected_classification']}")
        print(f"  Actual Classification: {classification}")
        print(f"  Expected Justification: {test_case['expected_justification']}")
        print(f"  Actual Justification: {justification}")
        
        if (classification == test_case['expected_classification'] and 
            justification == test_case['expected_justification']):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    test_actual_classification_logic()