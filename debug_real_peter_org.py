"""Debug with the ACTUAL people under Peter Obasa"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

# The ACTUAL org structure under Peter
users_data = [
    # Mark - 3 levels down from Peter (James -> Dan -> Peter)
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # Direct reports to Peter
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    {'Email': 'gershon.n@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    {'Email': 'nicolas.h@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    {'Email': 'troy.tweedy@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    {'Email': 'marion.polivka@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    
    # James Peterson (Mark's manager, under Dan)
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # Let's add a few more people at various levels to simulate the real data
    # Some people under Dan's other reports
    {'Email': 'person1.underdan@h.com', 'ManagerLine': 'Manager1 -> Dan Basile -> Peter Obasa -> Mike Allen'},
    {'Email': 'person2.underdan@h.com', 'ManagerLine': 'Manager1 -> Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # Some people under Gershon
    {'Email': 'person1.undergershon@h.com', 'ManagerLine': 'SubMgr1 -> Gershon N -> Peter Obasa -> Mike Allen'},
    {'Email': 'person2.undergershon@h.com', 'ManagerLine': 'SubMgr1 -> Gershon N -> Peter Obasa -> Mike Allen'},
]

# Add more people to simulate why it might be escalating
# Add 250+ people at various levels under Mike Allen
for i in range(250):
    dept = i // 50  # 5 departments
    users_data.append({
        'Email': f'person{i}@h.com',
        'ManagerLine': f'Mgr{i%10} -> Dept{dept} -> Mike Allen'
    })

for user in users_data:
    user.update({
        'Overall Recency': reference_date - timedelta(days=1),
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

print(f"Total users: {len(users_df)}")
print("\nPeople directly under Peter Obasa:")
print("="*80)
peter_directs = users_df[users_df['ManagerLine'].str.startswith('Peter Obasa', na=False)]
print(f"Found {len(peter_directs)} direct reports to Peter")
for _, user in peter_directs.iterrows():
    print(f"  - {user['Email']}")

print("\nAll people with Peter in their chain:")
peter_org = users_df[users_df['ManagerLine'].str.contains('Peter Obasa', na=False)]
print(f"Found {len(peter_org)} people total under Peter")

print("\n" + "="*80)
print("Calculating RUI...")

calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

# Check Mark's assignment
mark = result[result['Email'] == 'mark.rothfuss@h.com'].iloc[0]
print(f"\nMark Rothfuss:")
print(f"  Peer Group Type: {mark['peer_group_type']}")
print(f"  Peer Group Size: {mark['peer_group_size']}")
print(f"  Peer Group: {mark['peer_group']}")

if mark['peer_group_size'] > 20:
    print(f"\n❌ FAILURE: Mark is in a group of {mark['peer_group_size']} people!")
    print("   Should be ~6-11 people under Peter Obasa")
    
    # Show what's in his peer group
    mark_peers = result[result['peer_group'] == mark['peer_group']]
    print(f"\n   Sample of who's in Mark's peer group:")
    for _, peer in mark_peers.head(10).iterrows():
        mgr_line = peer.get('ManagerLine', 'N/A')
        if 'Peter Obasa' in mgr_line:
            print(f"     - {peer['Email']} (UNDER PETER)")
        else:
            print(f"     - {peer['Email']} (NOT UNDER PETER!)")
else:
    print(f"\n✓ SUCCESS: Mark is in a reasonable peer group of {mark['peer_group_size']} people")

# Check the direct reports to Peter
print("\n" + "="*80)
print("Peer groups for Peter's direct reports:")
for email in ['dan.basile@h.com', 'marion.polivka@h.com', 'gershon.n@h.com']:
    user = result[result['Email'] == email]
    if not user.empty:
        user = user.iloc[0]
        print(f"  {email}: {user['peer_group_type']} (size: {user['peer_group_size']})")