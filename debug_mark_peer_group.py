"""Debug Mark Rothfuss's peer group calculation"""

import pandas as pd
import numpy as np
from datetime import datetime
from rui_calculator import RUICalculator

# Load the manager tree - handle potential quoting issues
manager_df = pd.read_csv('manager.tree', quoting=1, on_bad_lines='skip')

# Create a simulated users dataset with the people mentioned
reference_date = datetime.now()

# People mentioned by user as having licenses in Lincoln
lincoln_users = [
    'mark.x.rothfuss@haleon.com',
    'dan.x.basile@haleon.com',  # Dan Basile (Mark's skip-level manager)
    'peter.x.obasa@haleon.com',  # Peter Obasa (higher up)
    'tim.x.gunderson@haleon.com',  # Tim Gunderson
    'marion.x.polivka@haleon.com',  # Marion Polivka
    'james.x.peterson@haleon.com',  # James Peterson (Mark's direct manager)
]

# Get their manager lines from the tree
print("Manager Lines for Lincoln users:")
print("="*80)
for email in lincoln_users:
    user_row = manager_df[manager_df['UserPrincipalName'] == email]
    if not user_row.empty:
        mgr_line = user_row['ManagerLine'].values[0]
        print(f"{email}:")
        print(f"  {mgr_line}")
    else:
        print(f"{email}: NOT FOUND in manager tree")

# Now let's see who else reports to James Peterson
print("\n" + "="*80)
print("People reporting to James Peterson:")
james_reports = manager_df[manager_df['ManagerLine'].str.startswith('James Peterson ->', na=False)]
print(f"Found {len(james_reports)} people reporting to James Peterson")
for _, row in james_reports.iterrows():
    print(f"  - {row['UserPrincipalName']}")

# People reporting to Dan Basile  
print("\n" + "="*80)
print("People reporting to Dan Basile (at any level):")
dan_reports = manager_df[manager_df['ManagerLine'].str.contains('Dan Basile', na=False)]
print(f"Found {len(dan_reports)} people with Dan Basile in their chain")

# Direct reports to Dan
dan_direct = manager_df[manager_df['ManagerLine'].str.startswith('Dan Basile ->', na=False)]
print(f"\nDirect reports to Dan Basile: {len(dan_direct)}")
for _, row in dan_direct.iterrows():
    print(f"  - {row['UserPrincipalName']}")

# Let's check the actual peer group calculation
print("\n" + "="*80)
print("Testing peer group calculation for Mark:")

# Create a test dataset with just Lincoln users and some extras
test_users = []

# Add Mark and people under James
test_users.append({
    'Email': 'mark.x.rothfuss@haleon.com',
    'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
    'Overall Recency': reference_date,
    'Adjusted Consistency (%)': 70,
    'Avg Tools / Report': 4.0,
    'Usage Trend': 'Stable'
})

# Add James Peterson (if he has a license)
test_users.append({
    'Email': 'james.x.peterson@haleon.com', 
    'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
    'Overall Recency': reference_date,
    'Adjusted Consistency (%)': 80,
    'Avg Tools / Report': 5.0,
    'Usage Trend': 'Stable'
})

# Add Dan Basile
test_users.append({
    'Email': 'dan.x.basile@haleon.com',
    'ManagerLine': 'Peter Obasa -> Mike Allen -> Alvaro Cantillo -> Namrata Patel -> Brian McNamara',
    'Overall Recency': reference_date,
    'Adjusted Consistency (%)': 85,
    'Avg Tools / Report': 6.0,
    'Usage Trend': 'Growing'
})

# Add other Dan Basile direct reports from the tree
dan_direct_emails = ['pariss.x.bethune@haleon.com']  # We know Pariss reports to Dan
for email in dan_direct_emails:
    user_row = manager_df[manager_df['UserPrincipalName'] == email]
    if not user_row.empty:
        test_users.append({
            'Email': email,
            'ManagerLine': user_row['ManagerLine'].values[0],
            'Overall Recency': reference_date,
            'Adjusted Consistency (%)': 75,
            'Avg Tools / Report': 4.5,
            'Usage Trend': 'Stable'
        })

# Add people under Pariss
pariss_reports = manager_df[manager_df['ManagerLine'].str.startswith('Pariss Bethune ->', na=False)]
for _, row in pariss_reports.head(3).iterrows():
    test_users.append({
        'Email': row['UserPrincipalName'],
        'ManagerLine': row['ManagerLine'],
        'Overall Recency': reference_date,
        'Adjusted Consistency (%)': 65,
        'Avg Tools / Report': 3.5,
        'Usage Trend': 'Stable'
    })

# Add Marion and Tim if we can find them
for email in ['marion.x.polivka@haleon.com', 'tim.x.gunderson@haleon.com']:
    user_row = manager_df[manager_df['UserPrincipalName'] == email]
    if not user_row.empty:
        test_users.append({
            'Email': email,
            'ManagerLine': user_row['ManagerLine'],
            'Overall Recency': reference_date,
            'Adjusted Consistency (%)': 60,
            'Avg Tools / Report': 3.0,
            'Usage Trend': 'Stable'
        })

users_df = pd.DataFrame(test_users)
print(f"\nTest dataset has {len(users_df)} users")

# Calculate RUI with debug output
calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df, manager_df[manager_df['UserPrincipalName'].isin(users_df['Email'])])

# Check Mark's peer group
mark_result = result[result['Email'] == 'mark.x.rothfuss@haleon.com']
if not mark_result.empty:
    mark = mark_result.iloc[0]
    print(f"\nMark Rothfuss peer group:")
    print(f"  Type: {mark['peer_group_type']}")
    print(f"  Size: {mark['peer_group_size']}")
    print(f"  Group: {mark['peer_group']}")
    
    # Show who's in his peer group
    peer_group_members = result[result['peer_group'] == mark['peer_group']]
    print(f"\nMembers of Mark's peer group:")
    for _, member in peer_group_members.iterrows():
        print(f"  - {member['Email']} (Manager Line: {member.get('ManagerLine', 'N/A')[:50]}...)")