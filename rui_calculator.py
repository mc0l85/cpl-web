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
            # Format: User -> Manager1 -> Manager2 -> ... -> CEO
            managers = [m.strip() for m in manager_line.split('->')]
            
            # Strategy 1: Direct reports of same immediate manager
            if len(managers) >= 2:
                immediate_manager = managers[1]  # Position 1 is the immediate manager
                # Find users who have the exact same immediate manager
                def has_same_manager(x):
                    if pd.isna(x) or '->' not in x:
                        return False
                    parts = [p.strip() for p in x.split('->')]
                    if len(parts) >= 2:
                        return parts[1] == immediate_manager  # Check position 1
                    return False
                
                peers = df[df['ManagerLine'].apply(has_same_manager)]
                
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"direct_{immediate_manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = 'Direct Manager Team'
                    continue
            
            # Strategy 2: Peers at same level (cousins - same skip-level manager)
            if len(managers) >= 3:
                skip_manager = managers[2]  # Position 2 is the skip-level manager
                # Find users who report to any manager under skip_manager
                def has_same_skip_manager(x):
                    if pd.isna(x) or '->' not in x:
                        return False
                    parts = [p.strip() for p in x.split('->')]
                    if len(parts) >= 3:
                        return parts[2] == skip_manager  # Check position 2
                    return False
                
                peers = df[df['ManagerLine'].apply(has_same_skip_manager)]
                
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"skip_{skip_manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = 'Skip-Level Peers'
                    continue
            
            # Strategy 3: Walk up the chain looking for sufficient peers at each level
            for i in range(len(managers) - 1, -1, -1):
                manager = managers[i]
                
                # Find users at the same organizational level under this manager
                manager_position = i
                peers = df[df['ManagerLine'].apply(
                    lambda x: (manager in x.split('->') and 
                              x.split('->').index(manager) == manager_position)
                    if pd.notna(x) and '->' in x else False
                )]
                
                if len(peers) >= self.MIN_PEER_GROUP_SIZE:
                    df.at[idx, 'peer_group'] = f"level_{manager}"
                    df.at[idx, 'peer_group_size'] = len(peers)
                    df.at[idx, 'peer_group_type'] = f'Org Level {len(managers) - i}'
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
        """Create manager-level summary statistics"""
        if 'ManagerLine' not in df.columns:
            return pd.DataFrame()
        
        # Extract immediate manager (position 1 in the chain)
        df['immediate_manager'] = df['ManagerLine'].apply(
            lambda x: x.split('->')[1].strip() if pd.notna(x) and '->' in x and len(x.split('->')) >= 2 else None
        )
        
        # Group by manager
        summary = df.groupby('immediate_manager').agg({
            'Email': 'count',
            'rui_score': 'mean',
            'license_risk': lambda x: (x.str.startswith('High')).sum()
        }).rename(columns={
            'Email': 'team_size',
            'rui_score': 'avg_rui',
            'license_risk': 'high_risk_count'
        })
        
        # Add medium and low risk counts
        for manager in summary.index:
            manager_df = df[df['immediate_manager'] == manager]
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
        
        summary = summary.reset_index()
        summary.columns = ['Manager Name', 'Team Size', 'Avg RUI', 
                          'High Risk', 'Medium Risk', 'Low Risk', 'New Users', 'Action Required']
        
        # Sort by action required, then avg RUI
        summary = summary.sort_values(['Action Required', 'Avg RUI'], 
                                    ascending=[False, True])
        
        return summary