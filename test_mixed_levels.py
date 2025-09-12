"""Test peer groups with mixed organizational levels"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

# Create a dataset that mimics the real org structure
users_data = [
    # Mark's team under James -> Dan -> Peter
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # Dan's direct reports
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen'},
    {'Email': 'pariss.bethune@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # People under Pariss
    {'Email': 'jenn.cooney@h.com', 'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen'},
    {'Email': 'bryce.weiberg@h.com', 'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa -> Mike Allen'},
    
    # Dan himself
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    
    # Marion reports DIRECTLY to Peter (not through Dan)
    {'Email': 'marion.polivka@h.com', 'ManagerLine': 'Peter Obasa -> Mike Allen'},
    
    # Tim reports to someone else under Peter (not Dan)
    {'Email': 'tim.gunderson@h.com', 'ManagerLine': 'Tim Manager -> Peter Obasa -> Mike Allen'},
    
    # Some people under Tim's manager
    {'Email': 'tim.peer1@h.com', 'ManagerLine': 'Tim Manager -> Peter Obasa -> Mike Allen'},
    {'Email': 'tim.peer2@h.com', 'ManagerLine': 'Tim Manager -> Peter Obasa -> Mike Allen'},
    
    # Peter himself
    {'Email': 'peter.obasa@h.com', 'ManagerLine': 'Mike Allen'},
    
    # Add many more people under different managers under Mike Allen
    # This simulates the 200+ people in the broader organization
]

# Add 50 people under various managers reporting to Mike Allen
for i in range(50):
    manager_num = i // 10  # 5 different managers, 10 people each
    users_data.append({
        'Email': f'mike.team{i}@h.com',
        'ManagerLine': f'Manager{manager_num} -> Mike Allen'
    })

# Add 50 people under another executive at Mike's level
for i in range(50):
    users_data.append({
        'Email': f'other.exec.team{i}@h.com',
        'ManagerLine': f'OtherManager{i//10} -> Other Exec'
    })

# Add consistent metrics for all users
for user in users_data:
    user.update({
        'Overall Recency': reference_date - timedelta(days=len(user['Email']) % 30),
        'Adjusted Consistency (%)': 50 + (len(user['Email']) % 40),
        'Avg Tools / Report': 2.0 + (len(user['Email']) % 5),
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

print(f"Total users in dataset: {len(users_df)}")
print("="*80)

# Calculate RUI
calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

# Check specific users
important_users = [
    'mark.rothfuss@h.com',
    'marion.polivka@h.com',
    'dan.basile@h.com',
    'tim.gunderson@h.com'
]

print("\nPeer Group Assignments for Key Users:")
print("="*80)
for email in important_users:
    user = result[result['Email'] == email]
    if not user.empty:
        user = user.iloc[0]
        print(f"\n{email}:")
        print(f"  Manager Line: {users_df[users_df['Email'] == email]['ManagerLine'].values[0]}")
        print(f"  Peer Group Type: {user['peer_group_type']}")
        print(f"  Peer Group Size: {user['peer_group_size']}")
        print(f"  Peer Group: {user['peer_group'][:50]}")

# Verify Mark's peer group is reasonable
mark = result[result['Email'] == 'mark.rothfuss@h.com'].iloc[0]
print("\n" + "="*80)
print("Mark Rothfuss Peer Group Analysis:")
print(f"  Should be ~5-10 people under Dan Basile")
print(f"  Actual size: {mark['peer_group_size']}")

if mark['peer_group_size'] > 50:
    print("  ❌ ERROR: Peer group too large! Should not include entire organization")
    # Show who's in the group
    mark_peers = result[result['peer_group'] == mark['peer_group']]
    print(f"\n  Sample of peers (first 10):")
    for _, peer in mark_peers.head(10).iterrows():
        mgr_line = users_df[users_df['Email'] == peer['Email']]['ManagerLine'].values[0]
        print(f"    - {peer['Email']:30} -> {mgr_line[:40]}")
elif mark['peer_group_size'] < 5:
    print("  ⚠️  WARNING: Peer group too small")
else:
    print("  ✓ Peer group size is reasonable")

# Verify Marion's peer group is different from Mark's
marion = result[result['Email'] == 'marion.polivka@h.com'].iloc[0]
if marion['peer_group'] != mark['peer_group']:
    print("\n  ✓ Marion has a different peer group from Mark (correct)")
else:
    print("\n  ❌ ERROR: Marion and Mark in same peer group (should be different)")