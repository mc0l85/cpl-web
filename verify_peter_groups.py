"""Verify all Peter Obasa org members are in correct groups"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

# The ACTUAL org structure under Peter - simplified
users_data = [
    # Mark - under James -> Dan -> Peter
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa'},
    
    # Direct reports to Peter (5 people)
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'gershon.n@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'nicolas.h@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'troy.tweedy@h.com', 'ManagerLine': 'Peter Obasa'},
    {'Email': 'marion.polivka@h.com', 'ManagerLine': 'Peter Obasa'},
    
    # James Peterson (under Dan)
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    
    # A few more people at various levels under Peter
    {'Email': 'person1@h.com', 'ManagerLine': 'Manager1 -> Dan Basile -> Peter Obasa'},
    {'Email': 'person2@h.com', 'ManagerLine': 'Manager1 -> Gershon N -> Peter Obasa'},
    {'Email': 'person3@h.com', 'ManagerLine': 'Nicolas H -> Peter Obasa'},
    {'Email': 'person4@h.com', 'ManagerLine': 'Troy Tweedy -> Peter Obasa'},
]

for user in users_data:
    user.update({
        'Overall Recency': reference_date,
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

print(f"Total people under Peter: {len(users_df)}")
print("="*80)

calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

# Check each person's assignment
print("\nPeer Group Assignments:")
print("-" * 80)
print(f"{'Email':<30} {'Type':<25} {'Size':<6} {'Group ID'}")
print("-" * 80)

for _, user in result.iterrows():
    email = user['Email'].split('@')[0]
    pg_type = user['peer_group_type']
    pg_size = user['peer_group_size']
    pg_id = user['peer_group']
    print(f"{email:<30} {pg_type:<25} {pg_size:<6} {pg_id}")

# Verify consistency
print("\n" + "="*80)
print("Checking for issues:")

# Everyone should ideally be in the same peer group since they're all under Peter
unique_groups = result['peer_group'].unique()
if len(unique_groups) > 2:  # Allow for some variation
    print(f"⚠️  WARNING: {len(unique_groups)} different peer groups found")
    for group in unique_groups:
        members = result[result['peer_group'] == group]
        print(f"\n  {group}: {len(members)} members")
        for _, m in members.iterrows():
            print(f"    - {m['Email']}")
else:
    print("✓ Peer groups look reasonable")

# Check Mark specifically
mark = result[result['Email'] == 'mark.rothfuss@h.com'].iloc[0]
if mark['peer_group_size'] > 15:
    print(f"\n❌ Mark's peer group is too large: {mark['peer_group_size']}")
elif mark['peer_group_size'] < 5:
    print(f"\n❌ Mark's peer group is too small: {mark['peer_group_size']}")
else:
    print(f"\n✓ Mark's peer group size is good: {mark['peer_group_size']}")