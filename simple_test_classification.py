#!/usr/bin/env python3
"""
Simple test for license recapture classification logic
Does not require external dependencies
"""

from datetime import datetime, timedelta

def test_classification_logic():
    """Test the classification logic without pandas"""
    
    def get_manager_classification(last_seen, first_seen, reference_date, consistency, complexity):
        """Simplified version of the classification logic"""
        today = reference_date
        
        # Check if new user (first seen within 90 days)
        if first_seen and (today - first_seen).days < 90:
            return "New User"
        
        # Check if license recapture (no activity in last 90 days)
        if last_seen and (today - last_seen).days > 90:
            return "License Recapture"
        
        # Other classifications based on consistency and complexity
        if consistency > 75 and complexity > 10:
            return "Power User"
        if consistency > 75:
            return "Consistent User"
        if consistency > 25:
            return "Coaching Opportunity"
        return "Coaching Opportunity"  # Changed default from "License Recapture" to "Coaching Opportunity"
    
    # Test cases
    test_cases = [
        {
            'name': 'Active User (should NOT be License Recapture)',
            'last_seen': datetime(2025, 6, 26),
            'first_seen': datetime(2025, 4, 1),
            'reference_date': datetime(2025, 7, 22),
            'consistency': 13.5,
            'complexity': 2,
            'expected': 'Coaching Opportunity'  # Based on consistency <= 25
        },
        {
            'name': 'Inactive User (should be License Recapture)',
            'last_seen': datetime(2025, 3, 1),
            'first_seen': datetime(2025, 1, 1),
            'reference_date': datetime(2025, 7, 22),
            'consistency': 50,
            'complexity': 5,
            'expected': 'License Recapture'
        },
        {
            'name': 'New User (should be New User)',
            'last_seen': datetime(2025, 7, 1),
            'first_seen': datetime(2025, 5, 1),
            'reference_date': datetime(2025, 7, 22),
            'consistency': 80,
            'complexity': 15,
            'expected': 'New User'
        },
        {
            'name': 'Power User',
            'last_seen': datetime(2025, 7, 20),
            'first_seen': datetime(2025, 1, 1),
            'reference_date': datetime(2025, 7, 22),
            'consistency': 80,
            'complexity': 15,
            'expected': 'Power User'
        }
    ]
    
    print("Testing License Recapture Classification Logic")
    print("=" * 50)
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"  Last Seen: {test_case['last_seen'].strftime('%Y-%m-%d')}")
        print(f"  First Seen: {test_case['first_seen'].strftime('%Y-%m-%d')}")
        print(f"  Reference Date: {test_case['reference_date'].strftime('%Y-%m-%d')}")
        print(f"  Days Inactive: {(test_case['reference_date'] - test_case['last_seen']).days}")
        print(f"  Days Since First Seen: {(test_case['reference_date'] - test_case['first_seen']).days}")
        print(f"  Consistency: {test_case['consistency']}%")
        print(f"  Complexity: {test_case['complexity']}")
        
        result = get_manager_classification(
            test_case['last_seen'],
            test_case['first_seen'],
            test_case['reference_date'],
            test_case['consistency'],
            test_case['complexity']
        )
        
        print(f"  Expected: {test_case['expected']}")
        print(f"  Actual: {result}")
        
        if result == test_case['expected']:
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

def test_specific_user():
    """Test the specific user mentioned in the issue"""
    print("\nTesting Specific User: kamila.x.rodrigues@haleon.com")
    print("=" * 60)
    
    # User data from the issue
    last_seen = datetime(2025, 6, 26)
    first_seen = datetime(2025, 4, 22)
    reference_date = datetime(2025, 7, 22)  # Latest report date
    consistency = 13.5
    complexity = 2
    
    def get_manager_classification(last_seen, first_seen, reference_date, consistency, complexity):
        """Simplified version of the classification logic"""
        today = reference_date
        
        # Check if new user (first seen within 90 days)
        if first_seen and (today - first_seen).days < 90:
            return "New User"
        
        # Check if license recapture (no activity in last 90 days)
        if last_seen and (today - last_seen).days > 90:
            return "License Recapture"
        
        # Other classifications based on consistency and complexity
        if consistency > 75 and complexity > 10:
            return "Power User"
        if consistency > 75:
            return "Consistent User"
        if consistency > 25:
            return "Coaching Opportunity"
        return "Coaching Opportunity"  # Changed default from "License Recapture" to "Coaching Opportunity"
    
    days_inactive = (reference_date - last_seen).days
    days_since_start = (reference_date - first_seen).days
    
    print(f"Last Activity: {last_seen.strftime('%Y-%m-%d')}")
    print(f"First Activity: {first_seen.strftime('%Y-%m-%d')}")
    print(f"Latest Report: {reference_date.strftime('%Y-%m-%d')}")
    print(f"Days Inactive: {days_inactive}")
    print(f"Days Since First Seen: {days_since_start}")
    print(f"Consistency: {consistency}%")
    print(f"Complexity: {complexity}")
    
    result = get_manager_classification(last_seen, first_seen, reference_date, consistency, complexity)
    
    print(f"\nClassification Result: {result}")
    
    if result == "License Recapture":
        print("❌ FAILED: User incorrectly classified as License Recapture")
        print(f"   User has only been inactive for {days_inactive} days, not > 90 days")
        return False
    else:
        print("✅ PASSED: User correctly NOT classified as License Recapture")
        return True

if __name__ == "__main__":
    # Run all tests
    general_tests_passed = test_classification_logic()
    specific_user_passed = test_specific_user()
    
    print("\n" + "=" * 60)
    if general_tests_passed and specific_user_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("💥 SOME TESTS FAILED!")