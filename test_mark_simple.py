"""Simple test of Mark's peer group with minimal data"""

import pandas as pd
from datetime import datetime, timedelta
from rui_calculator import RUICalculator

reference_date = datetime.now()

# Create a minimal test with just the Lincoln NE team structure
users_data = [
    # Mark Rothfuss - reports to James Peterson
    {
        'Email': 'mark.x.rothfuss@haleon.com',
        'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=1),
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    },
    # Another person under James (Mark's peer)
    {
        'Email': 'peer1@haleon.com',
        'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=2),
        'Adjusted Consistency (%)': 65,
        'Avg Tools / Report': 3.5,
        'Usage Trend': 'Stable'
    },
    # James Peterson himself (has a license)
    {
        'Email': 'james.peterson@haleon.com',
        'ManagerLine': 'Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=1),
        'Adjusted Consistency (%)': 80,
        'Avg Tools / Report': 5.0,
        'Usage Trend': 'Growing'
    },
    # Pariss Bethune - reports to Dan Basile
    {
        'Email': 'pariss.bethune@haleon.com',
        'ManagerLine': 'Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=3),
        'Adjusted Consistency (%)': 75,
        'Avg Tools / Report': 4.5,
        'Usage Trend': 'Stable'
    },
    # People under Pariss
    {
        'Email': 'jenn.cooney@haleon.com',
        'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=4),
        'Adjusted Consistency (%)': 72,
        'Avg Tools / Report': 4.2,
        'Usage Trend': 'Stable'
    },
    {
        'Email': 'bryce.weiberg@haleon.com',
        'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=5),
        'Adjusted Consistency (%)': 68,
        'Avg Tools / Report': 3.9,
        'Usage Trend': 'Stable'
    },
    # Dan Basile himself
    {
        'Email': 'dan.basile@haleon.com',
        'ManagerLine': 'Peter Obasa',
        'Overall Recency': reference_date,
        'Adjusted Consistency (%)': 85,
        'Avg Tools / Report': 6.0,
        'Usage Trend': 'Growing'
    },
    # Marion Polivka - reports directly to Peter Obasa
    {
        'Email': 'marion.polivka@haleon.com',
        'ManagerLine': 'Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=10),
        'Adjusted Consistency (%)': 60,
        'Avg Tools / Report': 3.0,
        'Usage Trend': 'New User',
        'Classification': 'New User'
    },
    # Tim Gunderson - let's say he reports to another manager under Dan
    {
        'Email': 'tim.gunderson@haleon.com',
        'ManagerLine': 'Other Manager -> Dan Basile -> Peter Obasa',
        'Overall Recency': reference_date - timedelta(days=7),
        'Adjusted Consistency (%)': 55,
        'Avg Tools / Report': 2.8,
        'Usage Trend': 'Stable'
    }
]

users_df = pd.DataFrame(users_data)

print("Test dataset:")
print("="*80)
for _, user in users_df.iterrows():
    email = user['Email'].split('@')[0]
    mgr_line = user['ManagerLine']
    print(f"{email:30} -> {mgr_line}")

print("\n" + "="*80)
print("Calculating RUI scores...")

calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

print("\nPeer Group Assignments:")
print("="*80)
for _, user in result.iterrows():
    email = user['Email'].split('@')[0]
    pg_type = user['peer_group_type']
    pg_size = user['peer_group_size']
    pg = user['peer_group']
    print(f"{email:30} | {pg_type:20} | Size: {pg_size:3} | {pg[:40]}")

# Detailed look at Mark's peer group
print("\n" + "="*80)
print("Mark Rothfuss's Peer Group Details:")
mark = result[result['Email'] == 'mark.x.rothfuss@haleon.com'].iloc[0]
mark_peers = result[result['peer_group'] == mark['peer_group']]

print(f"  Type: {mark['peer_group_type']}")
print(f"  Size: {mark['peer_group_size']}")
print(f"  Group ID: {mark['peer_group']}")
print(f"\n  Members:")
for _, peer in mark_peers.iterrows():
    email = peer['Email'].split('@')[0]
    mgr_line = peer.get('ManagerLine', 'N/A')
    if '->' in mgr_line:
        first_mgr = mgr_line.split('->')[0].strip()
    else:
        first_mgr = mgr_line
    print(f"    - {email:30} (reports to: {first_mgr})")

# Check if James is incorrectly in Mark's peer group
if 'james.peterson@haleon.com' in mark_peers['Email'].values:
    print("\n  ⚠️  WARNING: James Peterson (Mark's manager) is in Mark's peer group!")
else:
    print("\n  ✓ James Peterson correctly excluded from Mark's peer group")