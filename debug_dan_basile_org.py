"""Debug why Dan Basile's organization isn't forming a proper peer group"""

import pandas as pd
from datetime import datetime, timedelta

reference_date = datetime.now()

# Create Dan Basile's org structure exactly
users_data = [
    # Mark under James under Dan
    {'Email': 'mark.rothfuss@h.com', 'ManagerLine': 'James Peterson -> Dan Basile -> Peter Obasa'},
    
    # James (Dan's direct report #1)
    {'Email': 'james.peterson@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    
    # Pariss (Dan's direct report #2)  
    {'Email': 'pariss.bethune@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    
    # People under Pariss
    {'Email': 'jenn.cooney@h.com', 'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa'},
    {'Email': 'bryce.weiberg@h.com', 'ManagerLine': 'Pariss Bethune -> Dan Basile -> Peter Obasa'},
    
    # Let's add a third direct report to Dan
    {'Email': 'manager3@h.com', 'ManagerLine': 'Dan Basile -> Peter Obasa'},
    
    # And some people under manager3
    {'Email': 'person1@h.com', 'ManagerLine': 'Manager3 -> Dan Basile -> Peter Obasa'},
    {'Email': 'person2@h.com', 'ManagerLine': 'Manager3 -> Dan Basile -> Peter Obasa'},
    
    # Dan himself
    {'Email': 'dan.basile@h.com', 'ManagerLine': 'Peter Obasa'}
]

for user in users_data:
    user.update({
        'Overall Recency': reference_date,
        'Adjusted Consistency (%)': 70,
        'Avg Tools / Report': 4.0,
        'Usage Trend': 'Stable'
    })

users_df = pd.DataFrame(users_data)

print("Dan Basile's Organization:")
print("="*80)
for _, user in users_df.iterrows():
    email = user['Email'].split('@')[0].ljust(20)
    mgr_line = user['ManagerLine']
    print(f"{email} -> {mgr_line}")

print("\n" + "="*80)
print("Who should be in Mark's peer group?")
print("-" * 40)

# Manual calculation
print("\n1. Direct peers under James Peterson:")
james_reports = users_df[users_df['ManagerLine'].str.startswith('James Peterson ->')]['Email'].tolist()
print(f"   {james_reports} = {len(james_reports)} people")

print("\n2. Skip-level peers (all under Dan Basile, excluding managers):")
dan_org = users_df[users_df['ManagerLine'].str.contains('Dan Basile', na=False)]
print(f"   Total with Dan in chain: {len(dan_org)}")

# Filter out managers
non_managers = []
for _, user in dan_org.iterrows():
    email = user['Email']
    # Check if this person is a manager
    is_manager = any(users_df['ManagerLine'].str.contains(email.split('@')[0], case=False, na=False))
    if not is_manager:
        non_managers.append(email)
    else:
        print(f"   Excluding {email} (is a manager)")

print(f"   Non-managers: {non_managers}")
print(f"   Total non-managers: {len(non_managers)}")

print("\n" + "="*80)
print("Testing RUI Calculator:")

from rui_calculator import RUICalculator
calculator = RUICalculator(reference_date)
result = calculator.calculate_rui_scores(users_df)

print("\nPeer Groups Assigned:")
for _, user in result.iterrows():
    email = user['Email'].split('@')[0].ljust(20)
    pg_type = user['peer_group_type'].ljust(20)
    pg_size = str(user['peer_group_size']).rjust(3)
    print(f"{email} | {pg_type} | Size: {pg_size}")

# Focus on Mark
mark = result[result['Email'] == 'mark.rothfuss@h.com'].iloc[0]
print(f"\nMark's peer group: {mark['peer_group']}")
mark_peers = result[result['peer_group'] == mark['peer_group']]
print("Members:")
for _, peer in mark_peers.iterrows():
    print(f"  - {peer['Email']}")