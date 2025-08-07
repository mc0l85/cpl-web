#!/usr/bin/env python3
"""
Simple verification script to check if our data labels fix is in place
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_fix():
    print("Verifying data labels fix...")
    
    # Read the analysis_logic.py file to check if our fix is in place
    try:
        with open('analysis_logic.py', 'r') as f:
            content = f.read()
            
        # Check for the key components of our fix
        checks = [
            ('DataLabelList import', 'from openpyxl.chart.label import DataLabelList'),
            ('Data labels creation', 'series.dLbls = DataLabelList()'),
            ('Show values enabled', 'series.dLbls.showVal = True'),
            ('Position set to top', 'series.dLbls.position = \'top\'')
        ]
        
        all_good = True
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✓ {check_name}: Found")
            else:
                print(f"✗ {check_name}: Missing")
                all_good = False
        
        if all_good:
            print("\n✓ All data labels fix components are in place!")
            print("The chart should now display numbers on the graph points.")
        else:
            print("\n✗ Some fix components are missing.")
            
        return all_good
        
    except FileNotFoundError:
        print("✗ analysis_logic.py file not found")
        return False
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False

if __name__ == "__main__":
    verify_fix()