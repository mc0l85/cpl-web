"""Test that peer groups properly form at Peter Obasa's level"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

# Create realistic org under Peter Obasa
users_data = [
    # Mark's chain: Mark -> James -> Dan -> Peter
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa'},
    
    # Dan Basile (reports to Peter)
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa'},
    
    # James Peterson (reports to Dan who reports to Peter)
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    
    # Marion Polivka (reports DIRECTLY to Peter, not through Dan)
    {'Email': 'marion.polivka@h.com', 'ManagerLine': 'Peter Obasa'},
    
    # Tim Gunderson - let's say he reports to another manager under Peter
    {'Email': 'tim.gunderson@h.com', 'ManagerLine': 'Tim Manager -> Peter Obasa'},
    
    # Tim's manager
    {'Email': 'tim.manager@h.com', 'ManagerLine': 'Peter Obasa'},
    
    # Another person under Peter (peer to Dan and Tim's manager)
    {'Email': 'other.manager@h.com', 'ManagerLine': 'Peter Obasa'},
    
    # Peter himself
    {'Email': 'peter.obasa@h.com', 'ManagerLine': 'Mike Allen'},
]

for user in users_data:
    user.update({
        'Overall Recency': reference_date - timedelta(days=1),
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

print("Organization under Peter Obasa:")
print("="*80)
for _, user in users_df.iterrows():
    email = user['Email'].split('@')[0].ljust(25)
    mgr_line = user['ManagerLine']
    print(f"{email} -> {mgr_line}")

# Calculate RUI
calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

print("\n" + "="*80)
print("Peer Group Assignments:")
print("="*80)
for _, user in result.iterrows():
    email = user['Email'].split('@')[0].ljust(25)
    pg_type = user['peer_group_type'].ljust(20)
    pg_size = str(user['peer_group_size']).rjust(3)
    pg = user['peer_group'][:30].ljust(30)
    print(f"{email} | {pg_type} | Size:{pg_size} | {pg}")

# Check Mark's peer group
mark = result[result['Email'] == 'mark.rothfuss@h.com'].iloc[0]
print("\n" + "="*80)
print("Mark Rothfuss's Peer Group Analysis:")
print(f"  Peer Group Type: {mark['peer_group_type']}")
print(f"  Peer Group Size: {mark['peer_group_size']}")
print(f"  Peer Group ID: {mark['peer_group']}")

mark_peers = result[result['peer_group'] == mark['peer_group']]
print(f"\n  Members of Mark's peer group:")
for _, peer in mark_peers.iterrows():
    email = peer['Email'].split('@')[0]
    mgr_line = users_df[users_df['Email'] == peer['Email']]['ManagerLine'].values[0]
    # Get the first manager in their chain
    if '->' in mgr_line:
        immediate_mgr = mgr_line.split('->')[0].strip()
    else:
        immediate_mgr = mgr_line
    print(f"    - {email:25} (reports to: {immediate_mgr})")

print("\n" + "="*80)
print("Expected behavior:")
print("  - Mark should be in a peer group at Peter Obasa's level")
print("  - Should include Mark, Marion, Dan, Tim's manager, other managers under Peter")
print("  - Should be 5-7 people, NOT 273")

if mark['peer_group_size'] > 20:
    print(f"\n  ❌ ERROR: Peer group too large ({mark['peer_group_size']} people)")
elif mark['peer_group_size'] < 5:
    print(f"\n  ⚠️  WARNING: Peer group too small ({mark['peer_group_size']} people)")
else:
    print(f"\n  ✓ Peer group size is reasonable ({mark['peer_group_size']} people)")