"""Debug why peer group sizes are different for people in same group"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

users_data = [
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa'},
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    {'Email': 'marion.polivka@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'tim.gunderson@h.com', 'ManagerLine': 'Tim Manager -> Peter Obasa'},
    {'Email': 'tim.manager@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'other.manager@h.com', 'ManagerLine': 'Peter Obasa'},
]

for user in users_data:
    user.update({
        'Overall Recency': reference_date,
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

# Check each person's peer group
print("Peer groups and what managers are excluded:")
print("="*80)

for _, user in result.iterrows():
    email = user['Email']
    peer_group = user['peer_group']
    peer_size = user['peer_group_size']
    
    # Get this user's manager chain
    mgr_line = users_df[users_df['Email'] == email]['ManagerLine'].values[0]
    
    print(f"\n{email}:")
    print(f"  Manager Line: {mgr_line}")
    print(f"  Peer Group: {peer_group}")
    print(f"  Peer Size: {peer_size}")
    
    # What managers would be excluded for this user?
    if '->' in mgr_line:
        managers = [m.strip() for m in mgr_line.split('->')]
        print(f"  Managers to exclude: {managers}")
    else:
        print(f"  No managers to exclude (top level)")
    
# Show who's actually in each unique peer group
unique_groups = result['peer_group'].unique()
print("\n" + "="*80)
print("Actual members of each peer group:")
for group in unique_groups:
    members = result[result['peer_group'] == group]['Email'].tolist()
    print(f"\n{group}:")
    for member in members:
        print(f"  - {member}")