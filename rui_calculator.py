"""
Relative Use Index (RUI) Calculator
Implements manager-based peer group comparisons for fair license usage assessment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


class RUICalculator:
    """Calculate Relative Use Index scores for license management"""
    
    # Component weights
    WEIGHT_RECENCY = 0.40
    WEIGHT_FREQUENCY = 0.30
    WEIGHT_BREADTH = 0.20
    WEIGHT_TREND = 0.10
    
    # Parameters
    RECENCY_HALF_LIFE = 30  # days
    MIN_PEER_GROUP_SIZE = 5
    MIN_BREADTH_GOOD_STANDING = 2.0
    
    # Risk thresholds
    THRESHOLD_HIGH_RISK = 20
    THRESHOLD_MEDIUM_RISK = 40
    
    def __init__(self, reference_date):
        """Initialize with reference date for consistent calculations"""
        self.reference_date = pd.to_datetime(reference_date)
    
    def calculate_rui_scores(self, users_df: pd.DataFrame, manager_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Calculate RUI scores for all users
        
        Args:
            users_df: DataFrame with user metrics (must have Email column)
            manager_df: DataFrame with manager hierarchy (UserPrincipalName, ManagerLine columns)
        
        Returns:
            DataFrame with RUI scores and peer group information added
        """
        # Merge manager data if provided
        if manager_df is not None:
            manager_df = manager_df.copy()
            manager_df['UserPrincipalName'] = manager_df['UserPrincipalName'].str.lower()
            # Only merge columns that don't already exist in users_df
            merge_cols = ['UserPrincipalName']
            for col in ['ManagerLine', 'Department', 'Company', 'City']:
                if col in manager_df.columns and col not in users_df.columns:
                    merge_cols.append(col)
            
            # Only merge if there are columns to add
            if len(merge_cols) > 1:
                users_df = users_df.merge(
                    manager_df[merge_cols],
                    left_on='Email',
                    right_on='UserPrincipalName',
                    how='left'
                )
        
        # Calculate component scores
        users_df = self._calculate_recency_scores(users_df)
        users_df = self._calculate_frequency_scores(users_df)
        users_df = self._calculate_breadth_scores(users_df)
        users_df = self._calculate_trend_scores(users_df)
        
        # Form peer groups and calculate RUI
        users_df = self._assign_peer_groups(users_df)
        users_df = self._calculate_peer_relative_rui(users_df)
        
        # Add risk classification
        users_df = self._classify_risk(users_df)
        
        return users_df
    
    def _calculate_recency_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate recency component (0-100) with exponential decay"""
        df = df.copy()
        
        # Calculate days since last activity
        df['days_since_activity'] = (
            self.reference_date - pd.to_datetime(df['Overall Recency'], errors='coerce')
        ).dt.days
        
        # Apply exponential decay with 30-day half-life
        df['recency_score'] = 100 * np.exp(-df['days_since_activity'] / self.RECENCY_HALF_LIFE)
        df['recency_score'] = df['recency_score'].fillna(0).clip(0, 100)
        
        return df
    
    def _calculate_frequency_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate frequency component based on appearances/reports"""
        df = df.copy()
        
        # Use existing Adjusted Consistency as frequency proxy
        if 'Adjusted Consistency (%)' in df.columns:
            df['frequency_score'] = df['Adjusted Consistency (%)'].clip(0, 100)
        else:
            # Fallback to Usage Consistency
            df['frequency_score'] = df.get('Usage Consistency (%)', 0).clip(0, 100)
        
        return df
    
    def _calculate_breadth_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate breadth component based on tool diversity"""
        df = df.copy()
        
        # Use average tools per report as breadth metric
        if 'Avg Tools / Report' in df.columns:
            # Normalize to 0-100 scale (assume 10 tools = 100%)
            df['breadth_score'] = (df['Avg Tools / Report'] / 10 * 100).clip(0, 100)
        else:
            df['breadth_score'] = 0
        
        # Check good standing requirement
        df['good_standing'] = df['Avg Tools / Report'] >= self.MIN_BREADTH_GOOD_STANDING
        
        return df
    
    def _calculate_trend_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend component based on usage trajectory"""
        df = df.copy()
        
        # Map trend to score
        trend_map = {
            'Growing': 100,
            'Stable': 50,
            'Declining': 0,
            'New User': 75,  # Give new users benefit of doubt
            'Reactivated': 75
        }
        
        if 'Usage Trend' in df.columns:
            df['trend_score'] = df['Usage Trend'].map(trend_map).fillna(50)
        else:
            df['trend_score'] = 50
        
        return df
    
    def _assign_peer_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign users to peer groups based on manager hierarchy"""
        df = df.copy()
        
        df['peer_group'] = None
        df['peer_group_size'] = 0
        df['peer_group_type'] = None
        
        if 'ManagerLine' not in df.columns:
            # No manager data - use global comparison
            df['peer_group'] = 'global'
            df['peer_group_size'] = len(df)
            df['peer_group_type'] = 'Global'
            return df
        
        # Build a mapping of who manages whom
        # This helps us exclude managers from being peers of their subordinates
        manager_to_subordinates = {}
        for _, row in df.iterrows():
            mgr_line = row.get('ManagerLine', '')
            if pd.notna(mgr_line) and mgr_line != '':
                managers = [m.strip() for m in mgr_line.split('->')]
                if managers:
                    # First manager in the chain is the immediate manager
                    immediate_mgr = managers[0]
                    if immediate_mgr not in manager_to_subordinates:
                        manager_to_subordinates[immediate_mgr] = []
                    manager_to_subordinates[immediate_mgr].append(row.get('Email', ''))
        
        # Process each user to find appropriate peer group
        for idx, user in df.iterrows():
            manager_line = user.get('ManagerLine', '')
            
            if pd.isna(manager_line) or manager_line == '':
                # No manager info - use department or global
                if pd.notna(user.get('Department')):
                    df.at[idx, 'peer_group'] = f"dept_{user['Department']}"
                    df.at[idx, 'peer_group_type'] = 'Department'
                else:
                    df.at[idx, 'peer_group'] = 'global'
                    df.at[idx, 'peer_group_type'] = 'Global'
                continue
            
            # Parse manager chain
            # Format: ManagerLine contains Manager1 -> Manager2 -> ... -> CEO (user not included)
            managers = [m.strip() for m in manager_line.split('->')]
            current_user_email = user.get('Email', '')
            
            # Extract user name from email for matching
            if '@' in current_user_email:
                # Convert email to likely name format for manager matching
                user_name_parts = current_user_email.split('@')[0].replace('.', ' ').replace('x ', '').split()
                # Capitalize each part
                user_name_parts = [p.capitalize() for p in user_name_parts]
                # Try different name formats
                possible_names = [
                    ' '.join(user_name_parts),  # First Last
                    ' '.join(reversed(user_name_parts))  # Last First
                ]
            else:
                possible_names = []
            
            # First, check if this user is a manager themselves
            # Find all users who have this person as their immediate manager
            def has_user_as_manager(x):
                if pd.isna(x) or '->' not in x:
                    return False
                parts = [p.strip() for p in x.split('->')]
                if len(parts) > 0:
                    # Check if first position matches any possible name format
                    first_manager = parts[0]
                    for name in possible_names:
                        if name.lower() in first_manager.lower() or first_manager.lower() in name.lower():
                            return True
                return False
            
            subordinates = df[df['ManagerLine'].apply(has_user_as_manager)]
            
            # Strategy 1: Self + direct reports if user is a manager
            if len(subordinates) >= self.MIN_PEER_GROUP_SIZE - 1:
                # Include self and subordinates
                peer_group_indices = list(subordinates.index) + [idx]
                peers = df.loc[peer_group_indices]
                df.at[idx, 'peer_group'] = f"team_{current_user_email}"
                df.at[idx, 'peer_group_size'] = len(peers)
                df.at[idx, 'peer_group_type'] = 'Self + Subordinates'
                continue
            
            # Strategy 2: Direct peers under same manager (excluding the manager themselves)
            if len(managers) >= 1:
                immediate_manager = managers[0]  # Position 0 is the immediate manager
                
                # Find all users who have the same immediate manager
                def has_same_immediate_manager(x):
                    if pd.isna(x) or '->' not in x:
                        return False
                    parts = [p.strip() for p in x.split('->')]
                    # Check if position 0 (immediate manager) matches
                    return len(parts) > 0 and parts[0] == immediate_manager
                
                # Get peers with same manager, but exclude the manager if they're in the dataset
                peers = df[df['ManagerLine'].apply(has_same_immediate_manager)]
                
                # Important: Exclude the manager themselves from the peer group
                # Check if immediate_manager appears as a user (by checking email patterns)
                manager_email_patterns = [
                    immediate_manager.lower().replace(' ', '.') + '@',
                    immediate_manager.lower().replace(' ', '.x.') + '@',
                    immediate_manager.lower().replace(' ', '_') + '@'
                ]
                
                # Filter out the manager if they exist in the peers
                for pattern in manager_email_patterns:
                    peers = peers[~peers['Email'].str.lower().str.contains(pattern, na=False)]
                
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"direct_{immediate_manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = 'Direct Manager Team'
                    continue
            
            # Strategy 3: Peers at same level (cousins - same skip-level manager)
            if len(managers) >= 2:
                skip_manager = managers[1]  # Position 1 is the skip-level manager
                # Find users who have the same skip-level manager
                def has_same_skip_manager(x):
                    if pd.isna(x) or '->' not in x:
                        return False
                    parts = [p.strip() for p in x.split('->')]
                    if len(parts) >= 2:
                        return parts[1] == skip_manager  # Check position 1
                    return False
                
                peers = df[df['ManagerLine'].apply(has_same_skip_manager)]
                
                # Exclude both immediate and skip-level managers from peer group
                manager_email_patterns = []
                for mgr in [managers[0], skip_manager]:
                    manager_email_patterns.extend([
                        mgr.lower().replace(' ', '.') + '@',
                        mgr.lower().replace(' ', '.x.') + '@',
                        mgr.lower().replace(' ', '_') + '@'
                    ])
                
                # Filter out managers
                for pattern in manager_email_patterns:
                    peers = peers[~peers['Email'].str.lower().str.contains(pattern, na=False)]
                
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"skip_{skip_manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = 'Skip-Level Peers'
                    continue
            
            # Strategy 4: Walk up the chain to find the right organizational group
            # For each manager in the chain, check if their organization has 5+ people
            for i in range(len(managers)):
                manager = managers[i]
                
                # Find ALL users who have this manager ANYWHERE in their chain
                # This includes everyone in that manager's organization tree
                peers = df[df['ManagerLine'].apply(
                    lambda x: manager in str(x).split(' -> ') if pd.notna(x) else False
                )]
                
                # If this manager's org has 5+ people, use it as the peer group
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"org_{manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = f'Organization - {manager}'
                    break
            
            # If no suitable manager group found, use department or global
            if df.at[idx, 'peer_group'] is None:
                if pd.notna(user.get('Department')):
                    dept_peers = df[df['Department'] == user['Department']]
                    if len(dept_peers) >= self.MIN_PEER_GROUP_SIZE:
                        df.at[idx, 'peer_group'] = f"dept_{user['Department']}"
                        df.at[idx, 'peer_group_size'] = len(dept_peers)
                        df.at[idx, 'peer_group_type'] = 'Department'
                    else:
                        df.at[idx, 'peer_group'] = 'global'
                        df.at[idx, 'peer_group_size'] = len(df)
                        df.at[idx, 'peer_group_type'] = 'Global'
                else:
                    df.at[idx, 'peer_group'] = 'global'
                    df.at[idx, 'peer_group_size'] = len(df)
                    df.at[idx, 'peer_group_type'] = 'Global'
        
        return df
    
    def _calculate_peer_relative_rui(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RUI scores relative to peer groups"""
        df = df.copy()
        
        # Initialize RUI columns
        df['rui_score'] = 0.0
        df['peer_rank'] = 0
        df['peer_percentile'] = 0.0
        
        # Calculate RUI for each peer group
        for group_id in df['peer_group'].unique():
            group_mask = df['peer_group'] == group_id
            group_df = df[group_mask].copy()
            
            if len(group_df) == 0:
                continue
            
            # Calculate raw component scores
            for component in ['recency', 'frequency', 'breadth', 'trend']:
                col_name = f'{component}_score'
                
                # Calculate percentile rank within peer group
                percentile_col = f'{component}_percentile'
                group_df[percentile_col] = group_df[col_name].rank(pct=True) * 100
            
            # Calculate weighted RUI
            group_df['rui_score'] = (
                group_df['recency_percentile'] * self.WEIGHT_RECENCY +
                group_df['frequency_percentile'] * self.WEIGHT_FREQUENCY +
                group_df['breadth_percentile'] * self.WEIGHT_BREADTH +
                group_df['trend_percentile'] * self.WEIGHT_TREND
            )
            
            # Apply good standing penalty
            group_df.loc[~group_df['good_standing'], 'rui_score'] *= 0.8
            
            # Calculate peer rank
            group_df['rui_score'] = group_df['rui_score'].clip(0, 100)
            group_df['peer_rank'] = group_df['rui_score'].rank(ascending=False, method='min').astype(int)
            group_df['peer_percentile'] = group_df['rui_score'].rank(pct=True) * 100
            
            # Update main dataframe
            df.loc[group_mask, 'rui_score'] = group_df['rui_score']
            df.loc[group_mask, 'peer_rank'] = group_df['peer_rank']
            df.loc[group_mask, 'peer_percentile'] = group_df['peer_percentile']
            
            # Add component percentiles for transparency
            for component in ['recency', 'frequency', 'breadth', 'trend']:
                percentile_col = f'{component}_percentile'
                df.loc[group_mask, percentile_col] = group_df[percentile_col]
        
        return df
    
    def _classify_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify users into risk categories based on RUI score"""
        df = df.copy()
        
        def get_risk_level(score):
            if score < self.THRESHOLD_HIGH_RISK:
                return 'High - Reclaim'
            elif score < self.THRESHOLD_MEDIUM_RISK:
                return 'Medium - Review'
            else:
                return 'Low - Retain'
        
        df['license_risk'] = df['rui_score'].apply(get_risk_level)
        
        # Override risk classification for new users (90-day grace period)
        # New users should not be at risk during their onboarding period
        if 'Classification' in df.columns:
            new_user_mask = df['Classification'] == 'New User'
            df.loc[new_user_mask, 'license_risk'] = 'Low - New User (Grace Period)'
        
        # Create peer rank string (e.g., "3 of 8")
        df['peer_rank_display'] = df.apply(
            lambda x: f"{int(x['peer_rank'])} of {int(x['peer_group_size'])}" 
            if x['peer_group_size'] > 0 else "N/A",
            axis=1
        )
        
        # Create trend arrow
        trend_arrows = {
            'Growing': '↑',
            'Stable': '→',
            'Declining': '↓',
            'New User': '🆕',
            'Reactivated': '↗'
        }
        df['trend_arrow'] = df.get('Usage Trend', 'Stable').map(trend_arrows).fillna('→')
        
        return df
    
    def get_manager_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create manager-level summary statistics, aggregating small teams to meaningful groups"""
        if 'ManagerLine' not in df.columns:
            return pd.DataFrame()
        
        # Create a copy to work with
        df = df.copy()
        
        # Determine the effective manager for each user (lowest level that gets 5+ users)
        df['effective_manager'] = None
        
        # Build manager hierarchy mapping
        manager_hierarchy = {}
        for _, row in df.iterrows():
            mgr_line = row.get('ManagerLine', '')
            if pd.notna(mgr_line) and mgr_line != '':
                managers = [m.strip() for m in mgr_line.split('->')]
                # Store the full chain for each user
                manager_hierarchy[row['Email']] = managers
        
        # For each user, find the appropriate management level for reporting
        for idx, row in df.iterrows():
            mgr_line = row.get('ManagerLine', '')
            if pd.notna(mgr_line) and mgr_line != '':
                managers = [m.strip() for m in mgr_line.split('->')]
                
                # Start from immediate manager and work up
                for i, manager in enumerate(managers):
                    # Count how many users report to this manager at any level
                    users_under_manager = 0
                    for _, other_row in df.iterrows():
                        if pd.notna(other_row.get('ManagerLine')) and manager in other_row.get('ManagerLine', ''):
                            # Check if this manager appears at the same position in their chain
                            other_managers = [m.strip() for m in other_row['ManagerLine'].split('->')]
                            if i < len(other_managers) and other_managers[i] == manager:
                                users_under_manager += 1
                    
                    # If this manager has 5+ users, use them as the effective manager
                    if users_under_manager >= self.MIN_PEER_GROUP_SIZE:
                        df.at[idx, 'effective_manager'] = manager
                        df.at[idx, 'management_level'] = i
                        break
                
                # If no manager has 5+ users, use the highest level available
                if df.at[idx, 'effective_manager'] is None and managers:
                    df.at[idx, 'effective_manager'] = managers[-1]  # Top of chain
                    df.at[idx, 'management_level'] = len(managers) - 1
            else:
                # No manager line - mark as CEO/Top
                df.at[idx, 'effective_manager'] = 'No Manager Data'
                df.at[idx, 'management_level'] = -1
        
        # Group by effective manager
        summary = df.groupby('effective_manager').agg({
            'Email': 'count',
            'rui_score': 'mean',
            'license_risk': lambda x: (x.str.startswith('High')).sum(),
            'management_level': 'min'  # Get the lowest management level for this group
        }).rename(columns={
            'Email': 'team_size',
            'rui_score': 'avg_rui',
            'license_risk': 'high_risk_count',
            'management_level': 'mgmt_level'
        })
        
        # Add medium and low risk counts
        for manager in summary.index:
            manager_df = df[df['effective_manager'] == manager]
            summary.loc[manager, 'medium_risk_count'] = (
                manager_df['license_risk'].str.startswith('Medium')
            ).sum()
            summary.loc[manager, 'low_risk_count'] = (
                manager_df['license_risk'].str.startswith('Low')
            ).sum()
            # New users are counted separately
            summary.loc[manager, 'new_user_count'] = (
                manager_df['license_risk'].str.contains('New User')
            ).sum()
            summary.loc[manager, 'action_required'] = (
                summary.loc[manager, 'high_risk_count']
            )
            
            # Add organization level descriptor
            level = summary.loc[manager, 'mgmt_level']
            if level == -1:
                summary.loc[manager, 'org_level'] = 'No Data'
            elif level == 0:
                summary.loc[manager, 'org_level'] = 'Direct Manager'
            elif level == 1:
                summary.loc[manager, 'org_level'] = 'Skip-Level'
            elif level == 2:
                summary.loc[manager, 'org_level'] = 'Department'
            else:
                summary.loc[manager, 'org_level'] = f'Level {level+1}'
        
        summary = summary.reset_index()
        
        # Ensure correct column order and types
        summary = summary.rename(columns={
            'effective_manager': 'Manager/Group',
            'team_size': 'Team Size',
            'avg_rui': 'Avg RUI',
            'high_risk_count': 'High Risk',
            'medium_risk_count': 'Medium Risk',
            'low_risk_count': 'Low Risk',
            'new_user_count': 'New Users',
            'action_required': 'Action Required',
            'org_level': 'Org Level'
        })
        
        # Ensure numeric columns are integers
        for col in ['Team Size', 'High Risk', 'Medium Risk', 'Low Risk', 'New Users', 'Action Required']:
            if col in summary.columns:
                summary[col] = summary[col].fillna(0).astype(int)
        
        # Only include groups with 5+ users (unless there are no such groups)
        large_groups = summary[summary['Team Size'] >= self.MIN_PEER_GROUP_SIZE]
        if len(large_groups) > 0:
            summary = large_groups
        
        # Sort by action required, then avg RUI
        summary = summary.sort_values(['Action Required', 'Avg RUI'], 
                                    ascending=[False, True])
        
        # Drop the internal mgmt_level column
        if 'mgmt_level' in summary.columns:
            summary = summary.drop('mgmt_level', axis=1)
        
        # Reorder columns for better readability
        column_order = ['Manager/Group', 'Org Level', 'Team Size', 'Avg RUI', 
                       'High Risk', 'Medium Risk', 'Low Risk', 'New Users', 'Action Required']
        summary = summary[[col for col in column_order if col in summary.columns]]
        
        return summary