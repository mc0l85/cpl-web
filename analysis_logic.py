import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import os
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import DateAxis
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.colors import ColorChoice # Import ColorChoice
from openpyxl.styles.colors import Color
from datetime import datetime
import config


class CopilotAnalyzer:
    def __init__(self, socketio, sid):
        self.socketio = socketio
        self.sid = sid
        self.full_usage_data = None
        self.utilized_metrics_df = None

    def update_status(self, message):
        self.socketio.emit('status_update', {'message': message}, to=self.sid)
        self.socketio.sleep(0.1)

    def detect_adoption_date(self, user_history_df, tool_cols):
        user_history_df = user_history_df.sort_values(by='Report Refresh Date')
        user_history_df['tools_used'] = user_history_df[tool_cols].notna().sum(axis=1)
        if user_history_df.empty:
            return pd.NaT
        if user_history_df['tools_used'].iloc[0] >= 4:
            return user_history_df['Report Refresh Date'].iloc[0]
        prev_tools = user_history_df['tools_used'].shift(1).fillna(0)
        burst_mask = (prev_tools <= 2) & (user_history_df['tools_used'] >= 4)
        if burst_mask.any():
            return user_history_df.loc[burst_mask, 'Report Refresh Date'].iloc[0]
        return user_history_df['Report Refresh Date'].iloc[0]

    def get_manager_classification(self, row):
        # Use the max report date as reference for consistency
        today = self.reference_date
        last_seen = pd.to_datetime(row['Overall Recency']) if pd.notna(row['Overall Recency']) else pd.NaT
        first_seen = pd.to_datetime(row.get('Adoption Date')) if pd.notna(row.get('Adoption Date')) else (pd.to_datetime(row['First Appearance']) if pd.notna(row['First Appearance']) else pd.NaT)
        if pd.notna(first_seen) and (today - first_seen).days < 90:
            return "New User"
        if pd.notna(last_seen) and (today - last_seen).days > 90:
            return "License Recapture"
        
        # Use adjusted consistency for classification
        consistency_metric = row['Adjusted Consistency (%)']
        
        if consistency_metric > 75 and row['Usage Complexity'] > 10:
            return "Power User"
        if consistency_metric > 75:
            return "Consistent User"
        if consistency_metric > 25:
            return "Coaching Opportunity"
        return "Coaching Opportunity"  # Changed default from "License Recapture" to "Coaching Opportunity"

    def get_justification(self, row):
        classification = row['Classification']
        if classification == "New User":
            return "User is in their first 90 days and is still learning the tool."
        if classification == "License Recapture":
            return "User has not shown any activity in the last 90 days and their license could be reallocated."
        if classification == "Power User":
            return "User demonstrates high consistency and leverages a wide range of tools, indicating strong engagement."
        if classification == "Consistent User":
            return "User is highly active and has integrated the tool into their regular workflow."
        if classification == "Coaching Opportunity":
            return "User is active but inconsistent. Further coaching could help them maximize the tool's benefits."
        return ""

    def execute_analysis(self, usage_file_paths, target_user_path, filters):
        try:
            self.update_status("1. Loading usage reports from server...")
            all_reports = []
            print(f"--- Starting to process {len(usage_file_paths)} usage reports ---")
            i = 0
            for file_path in usage_file_paths.values():
                i += 1
                try:
                    df = pd.read_csv(file_path) if file_path.lower().endswith('.csv') else pd.read_excel(file_path)
                    all_reports.append(df)
                    print(f"({i}/{len(usage_file_paths)}) Successfully loaded: {file_path}")
                except Exception as e:
                    print(f"({i}/{len(usage_file_paths)}) Could not read file {file_path}: {e}")
                    continue
            print(f"--- Finished processing usage reports. Total dataframes loaded: {len(all_reports)} ---")
            if not all_reports: return {'error': "No usage reports could be read or they were empty."}
            usage_df = pd.concat(all_reports, ignore_index=True)
            usage_df['User Principal Name'] = usage_df['User Principal Name'].str.lower()
            date_cols = [col for col in usage_df.columns if 'date' in col.lower()]
            for col in date_cols:
                usage_df[col] = pd.to_datetime(usage_df[col], errors='coerce', format='mixed')
            self.full_usage_data = usage_df.copy()
            utilized_emails = set(usage_df['User Principal Name'].unique())
            # Store the original count from usage files
            original_usage_count = len(utilized_emails)
            if target_user_path:
                self.update_status("Applying filters...")
                target_df = pd.read_csv(target_user_path, encoding='utf-8-sig')

                if filters.get('companies'):
                    vals = set([v.lower() for v in filters['companies']])
                    if 'Company' in target_df.columns:
                        target_df = target_df[target_df['Company'].str.lower().isin(vals)]
                if filters.get('departments'):
                    vals = set([v.lower() for v in filters['departments']])
                    if 'Department' in target_df.columns:
                        target_df = target_df[target_df['Department'].str.lower().isin(vals)]
                if filters.get('locations'):
                    vals = set([v.lower() for v in filters['locations']])
                    if 'City' in target_df.columns:
                        target_df = target_df[target_df['City'].str.lower().isin(vals)]
                if filters.get('managers'):
                    if 'ManagerLine' in target_df.columns:
                        target_df['ManagerLine_lc'] = target_df['ManagerLine'].str.lower().fillna('')
                        managers_lc = [m.strip().lower() for m in filters['managers']]
                        target_df = target_df[target_df['ManagerLine_lc'].apply(lambda s: any(m == part.strip() for part in s.split('->') for m in managers_lc))]
                filtered_emails_before = len(utilized_emails)
                utilized_emails = utilized_emails.intersection(set(target_df['UserPrincipalName'].str.lower()))
                filtered_emails_after = len(utilized_emails)

                # Log the filtering impact
                if filtered_emails_before != filtered_emails_after:
                    self.update_status(f"Filtered from {filtered_emails_before} to {filtered_emails_after} users based on target file")
            if not utilized_emails: return {'error': "No matching users found to analyze."}
            # Validation: Log the filtering results
            if target_user_path:
                original_count = len(set(usage_df['User Principal Name'].unique()))
                filtered_count = len(utilized_emails)
                if original_count > filtered_count * 1.3:  # If more than 30% difference
                    self.update_status(f"Warning: Large difference in user counts - {original_count} in usage data vs {filtered_count} after filtering")
            self.update_status("2. Calculating user metrics...")
            matched_users_df = usage_df[usage_df['User Principal Name'].isin(utilized_emails)].copy()
            copilot_tool_cols = [col for col in matched_users_df.columns if 'Last activity date of' in col]
            min_report_date, max_report_date = usage_df['Report Refresh Date'].min(), usage_df['Report Refresh Date'].max()
            self.reference_date = max_report_date  # Set reference date for consistent calculations
            total_months_in_period = (max_report_date.year - min_report_date.year) * 12 + max_report_date.month - min_report_date.month + 1
            user_metrics = []
            total_users = len(utilized_emails)
            processed = 0
            for email in utilized_emails:
                processed += 1
                if processed % 50 == 0 or processed == total_users:
                    self.update_status(f"2b. Processing users: {processed} of {total_users} (filtered)...")
                user_data = matched_users_df[matched_users_df['User Principal Name'] == email]
                user_data_sorted = user_data.sort_values(by='Report Refresh Date')
                user_data_sorted['Row Recency'] = user_data_sorted[copilot_tool_cols].max(axis=1)
                adoption_date = self.detect_adoption_date(user_data_sorted.copy(), copilot_tool_cols)
                is_reactivated = False
                recency_series = user_data_sorted['Row Recency'].dropna()
                if len(recency_series) >= 3:
                    latest_date, prev_date_1, prev_date_2 = recency_series.iloc[-1], recency_series.iloc[-2], recency_series.iloc[-3]
                    if pd.notna(latest_date) and pd.notna(prev_date_1) and pd.notna(prev_date_2):
                        if prev_date_1 == prev_date_2 and latest_date > prev_date_1: is_reactivated = True
                activity_dates = pd.to_datetime(user_data[copilot_tool_cols].stack().dropna().unique())
                if len(activity_dates) == 0:
                    first_activity, last_activity, active_months, complexity, avg_tools_per_month, trend = pd.NaT, pd.NaT, 0, 0, 0, "N/A"
                    trend_details = {}
                    report_dates = user_data['Report Refresh Date'].unique()
                    if len(report_dates) > 0: first_activity = pd.to_datetime(report_dates).min()
                else:
                    # Ensure we're getting the absolute maximum date across all tools and reports
                    all_tool_dates_raw = user_data[copilot_tool_cols].values.flatten()
                    all_tool_dates_raw = pd.to_datetime(all_tool_dates_raw[pd.notna(all_tool_dates_raw)])
                    # Filter out any dates that are in the future relative to the last report
                    all_tool_dates = all_tool_dates_raw[all_tool_dates_raw <= self.reference_date]
                    last_activity = all_tool_dates.max() if len(all_tool_dates) > 0 else self.reference_date
                    first_activity = activity_dates.min()
                    if pd.notna(adoption_date):
                        first_activity = adoption_date
                    active_months = len(pd.to_datetime(activity_dates).to_period('M').unique())
                    complexity = user_data[copilot_tool_cols].notna().any().sum()
                    monthly_activity = user_data.groupby(pd.to_datetime(user_data['Report Refresh Date']).dt.to_period('M'))[copilot_tool_cols].apply(lambda x: x.notna().sum()).reset_index()
                    monthly_activity.columns = ['Month'] + copilot_tool_cols
                    # Calculate average tools per report correctly
                    tools_per_report = user_data.groupby('Report Refresh Date')[copilot_tool_cols].apply(lambda x: x.notna().sum(axis=1).sum())
                    avg_tools_per_month = tools_per_report.mean() if len(tools_per_report) > 0 else 0.0
                    # Improved trend analysis with recent momentum
                    trend = "N/A"
                    trend_details = {}
                    
                    trend_details = {}
                    if len(activity_dates) > 1:
                        # Get report-level activity
                        report_activity = user_data.groupby('Report Refresh Date')[copilot_tool_cols].apply(
                            lambda x: x.notna().sum(axis=1).sum()
                        ).sort_index()
                        
                        if len(report_activity) >= 2:
                            # Calculate different time windows
                            last_30_days = self.reference_date - pd.Timedelta(days=30)
                            last_60_days = self.reference_date - pd.Timedelta(days=60)
                            last_90_days = self.reference_date - pd.Timedelta(days=90)
                            
                            # Get activity in different periods
                            recent_activity = report_activity[report_activity.index > last_30_days]
                            medium_activity = report_activity[(report_activity.index > last_60_days) & (report_activity.index <= last_30_days)]
                            older_activity = report_activity[(report_activity.index > last_90_days) & (report_activity.index <= last_60_days)]
                            
                            # Calculate averages for each period
                            recent_avg = recent_activity.mean() if len(recent_activity) > 0 else 0
                            medium_avg = medium_activity.mean() if len(medium_activity) > 0 else 0
                            older_avg = older_activity.mean() if len(older_activity) > 0 else 0
                            
                            # Determine trend based on momentum
                            if recent_avg > 0:
                                if medium_avg == 0 and older_avg == 0:
                                    trend = "New Momentum"  # Just started using
                                elif recent_avg > medium_avg * 1.2:
                                    if medium_avg > older_avg * 1.2:
                                        trend = "Accelerating"  # Increasing faster
                                    else:
                                        trend = "Recovering"  # Was declining, now increasing
                                elif recent_avg < medium_avg * 0.8:
                                    if medium_avg < older_avg * 0.8:
                                        trend = "Declining"  # Decreasing consistently
                                    else:
                                        trend = "Cooling"  # Was increasing, now decreasing
                                else:
                                    trend = "Stable"
                            elif medium_avg > 0:
                                trend = "Dormant"  # Was active but stopped recently
                            else:
                                trend = "Inactive"  # No recent activity
                            
                            # Store detailed metrics for debugging
                            trend_details = {
                                'recent_avg': recent_avg,
                                'medium_avg': medium_avg,
                                'older_avg': older_avg
                            }
                consistency = (active_months / total_months_in_period) * 100 if total_months_in_period > 0 else 0
                
                # Calculate license-aware metrics with improved approach
                license_start = adoption_date if pd.notna(adoption_date) else first_activity
                tool_expansion_rate = 0
                if pd.notna(license_start):
                    days_since_license = (self.reference_date - license_start).days + 1  # Add 1 to include start day
                    adoption_velocity = complexity / max(days_since_license, 1)  # Tools per day
                    
                    # Calculate tool expansion rate (tools adopted per month)
                    if days_since_license > 30:  # Only calculate for users with at least 30 days
                        months_since_start = max(1, days_since_license / 30)
                        tool_expansion_rate = complexity / months_since_start
                    
                    # Improved consistency calculation with minimum evaluation period
                    # Only adjust consistency for users with less than minimum period
                    min_evaluation_days = 60  # Minimum 60 days for fair evaluation
                    if days_since_license <= min_evaluation_days:
                        # For new users, use a blended approach to prevent inflated scores
                        adjusted_consistency = (consistency * 0.7) + (min(100, (active_months / max(1, days_since_license / 30)) * 100) * 0.3)
                    else:
                        # For established users, use a balanced approach that considers both overall and recent patterns
                        months_since_license = (self.reference_date.year - license_start.year) * 12 + self.reference_date.month - license_start.month + 1
                        months_since_license = max(1, months_since_license)
                        raw_adjusted_consistency = (active_months / months_since_license) * 100 if months_since_license > 0 else 0
                        # Blend overall consistency with adjusted consistency
                        adjusted_consistency = (consistency * 0.6) + (raw_adjusted_consistency * 0.4)
                else:
                    adjusted_consistency = consistency
                    adoption_velocity = 0
                    days_since_license = 0
                    tool_expansion_rate = 0                
                user_metrics.append({
                     'Email': email, 
                     'Usage Consistency (%)': consistency,
                     'Adjusted Consistency (%)': adjusted_consistency,
                     'Overall Recency': last_activity, 
                     'Usage Complexity': complexity, 
                     'Avg Tools / Report': avg_tools_per_month, 
                     'Adoption Velocity': adoption_velocity,
                     'Tool Expansion Rate': tool_expansion_rate,
                     'Days Since License': days_since_license,
                     'Usage Trend': trend,
                     'Trend Details': trend_details,
                     'Appearances': user_data['Report Refresh Date'].nunique(), 
                     'First Appearance': first_activity, 
                     'Adoption Date': adoption_date, 
                     'is_reactivated': is_reactivated
                 })
            self.utilized_metrics_df = pd.DataFrame(user_metrics)
            if self.utilized_metrics_df.empty: return {'error': "No data available for the selected users."}
            # Ensure numeric dtype to avoid Series truth-value ambiguity
            self.utilized_metrics_df['Usage Consistency (%)'] = pd.to_numeric(self.utilized_metrics_df['Usage Consistency (%)'], errors='coerce').fillna(0)
            self.utilized_metrics_df['Adjusted Consistency (%)'] = pd.to_numeric(self.utilized_metrics_df['Adjusted Consistency (%)'], errors='coerce').fillna(0)
            self.utilized_metrics_df['Usage Complexity'] = pd.to_numeric(self.utilized_metrics_df['Usage Complexity'], errors='coerce').fillna(0)
            self.utilized_metrics_df['Adoption Velocity'] = pd.to_numeric(self.utilized_metrics_df['Adoption Velocity'], errors='coerce').fillna(0)
            if 'Avg Tools / Report' in self.utilized_metrics_df.columns:
                # If this column contains Series per-row, replace non-scalars with NaN before numeric cast
                self.utilized_metrics_df['Avg Tools / Report'] = self.utilized_metrics_df['Avg Tools / Report'].apply(lambda v: v if np.isscalar(v) else np.nan)
                self.utilized_metrics_df['Avg Tools / Report'] = pd.to_numeric(self.utilized_metrics_df['Avg Tools / Report'], errors='coerce').fillna(0)
            else:
                self.utilized_metrics_df['Avg Tools / Report'] = 0.0
            
            # Calculate recency factor (decay over time)
            self.utilized_metrics_df['days_since_last_activity'] = (self.reference_date - pd.to_datetime(self.utilized_metrics_df['Overall Recency'])).dt.days
            self.utilized_metrics_df['recency_factor'] = np.exp(-self.utilized_metrics_df['days_since_last_activity'] / 30)  # 30-day half-life
            
            # Normalize metrics
            max_adj_consistency = float(self.utilized_metrics_df['Adjusted Consistency (%)'].max())
            max_complexity = float(self.utilized_metrics_df['Usage Complexity'].max())
            max_avg_complexity = float(self.utilized_metrics_df['Avg Tools / Report'].max())
            max_adoption_velocity = float(self.utilized_metrics_df['Adoption Velocity'].max())
            max_tool_expansion = float(self.utilized_metrics_df['Tool Expansion Rate'].max())
            
            self.utilized_metrics_df['adj_consistency_norm'] = self.utilized_metrics_df['Adjusted Consistency (%)'] / max_adj_consistency if max_adj_consistency > 0 else 0
            self.utilized_metrics_df['complexity_norm'] = self.utilized_metrics_df['Usage Complexity'] / max_complexity if max_complexity > 0 else 0
            self.utilized_metrics_df['avg_complexity_norm'] = self.utilized_metrics_df['Avg Tools / Report'] / max_avg_complexity if max_avg_complexity > 0 else 0
            self.utilized_metrics_df['adoption_velocity_norm'] = self.utilized_metrics_df['Adoption Velocity'] / max_adoption_velocity if max_adoption_velocity > 0 else 0
            self.utilized_metrics_df['tool_expansion_norm'] = self.utilized_metrics_df['Tool Expansion Rate'] / max_tool_expansion if max_tool_expansion > 0 else 0
            
            # Add trend momentum factor
            trend_multipliers = {
                'Accelerating': 1.15,
                'Recovering': 1.10,
                'New Momentum': 1.10,
                'Stable': 1.0,
                'Cooling': 0.95,
                'Declining': 0.90,
                'Dormant': 0.85,
                'Inactive': 0.80,
                'Increasing': 1.05,  # Legacy
                'Decreasing': 0.95,  # Legacy
                'N/A': 1.0
            }
            self.utilized_metrics_df['trend_multiplier'] = self.utilized_metrics_df['Usage Trend'].map(trend_multipliers).fillna(1.0)
            
            # New weighted engagement score with better differentiation
            # Weights: Adjusted Consistency (25%), Overall Consistency (15%), Avg Tools/Report (20%), 
            # Breadth (10%), Tool Expansion Rate (10%), Recency (20%)
            # Include both adjusted and overall consistency to maintain balance
            # Add tool expansion rate to penalize flat usage patterns
            base_score = (
                self.utilized_metrics_df['adj_consistency_norm'] * 0.25 +
                (self.utilized_metrics_df['Usage Consistency (%)'] / max_adj_consistency if max_adj_consistency > 0 else 0) * 0.15 +
                self.utilized_metrics_df['avg_complexity_norm'] * 0.20 +
                self.utilized_metrics_df['complexity_norm'] * 0.10 +
                self.utilized_metrics_df['tool_expansion_norm'] * 0.10 +
                self.utilized_metrics_df['recency_factor'] * 0.20
            )
            
            # Apply trend multiplier more aggressively
            self.utilized_metrics_df['Engagement Score'] = base_score * self.utilized_metrics_df['trend_multiplier']
            
            # Scale scores to 0-100 range for better readability
            min_score = self.utilized_metrics_df['Engagement Score'].min()
            max_score = self.utilized_metrics_df['Engagement Score'].max()
            if max_score > min_score:
                self.utilized_metrics_df['Engagement Score'] = (
                    (self.utilized_metrics_df['Engagement Score'] - min_score) / (max_score - min_score) * 100
                )
            # Sort by engagement score, then by adjusted consistency, then recency
            self.utilized_metrics_df = self.utilized_metrics_df.sort_values(
                by=["Engagement Score", "Adjusted Consistency (%)", "Avg Tools / Report", "Overall Recency", "Email"], 
                ascending=[False, False, False, False, True]
            ).reset_index(drop=True)
            self.utilized_metrics_df['Global Rank'] = self.utilized_metrics_df.index + 1
            self.update_status("3. Classifying users...")
            self.utilized_metrics_df['Classification'] = self.utilized_metrics_df.apply(self.get_manager_classification, axis=1)
            self.utilized_metrics_df['Justification'] = self.utilized_metrics_df.apply(self.get_justification, axis=1)
            reallocation_df, under_utilized_df, top_utilizers_df = self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'For Reallocation'], self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'Under-Utilized'], self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'Top Utilizer']

            self.update_status("4. Calculating usage complexity over time...")
            usage_complexity_trend_df = self.calculate_usage_complexity_over_time(utilized_emails)

            self.update_status("5. Generating reports in memory...")
            excel_bytes = self.create_excel_report(top_utilizers_df, under_utilized_df, reallocation_df, self.utilized_metrics_df, usage_complexity_trend_df)
            leaderboard_html = self.create_leaderboard_html(self.utilized_metrics_df)
            debug_files = {}
            try:
                debug_root = None
                if config.GENERATE_DEBUG_FILES:
                    debug_root = os.path.join('temp_uploads', 'debug')
                    os.makedirs(debug_root, exist_ok=True)
                    class_csv = os.path.join(debug_root, 'classification_details.csv')
                    self.utilized_metrics_df.to_csv(class_csv, index=False)
                    deep_txt = os.path.join(debug_root, 'deep_dive_dump.txt')
                    with open(deep_txt, 'w', encoding='utf-8') as f:
                        tool_cols = [col for col in self.full_usage_data.columns if 'Last activity date of' in col]
                        for _, r in self.utilized_metrics_df.iterrows():
                            email = r['Email']
                            f.write(f"{email}\n")
                            f.write(f"Classification: {r['Classification']}\n")
                            f.write(f"Justification: {r['Justification']}\n")
                            f.write(f"Adjusted Consistency: {r['Adjusted Consistency (%)']:.1f}%\n")
                            f.write(f"Original Consistency: {r['Usage Consistency (%)']:.1f}%\n")
                            f.write(f"Usage Complexity: {int(r['Usage Complexity'])}\n")
                            f.write(f"Avg Tools/Report: {r['Avg Tools / Report']:.2f}\n")
                            f.write(f"Adoption Velocity: {r['Adoption Velocity']:.4f} tools/day\n")
                            f.write(f"Days Since License: {int(r['Days Since License']) if pd.notna(r.get('Days Since License')) else 'N/A'}\n")
                            f.write(f"Engagement Score: {r['Engagement Score']:.2f}\n")
                            f.write(f"Usage Trend: {r['Usage Trend']}\n")
                            if 'Trend Details' in r and r['Trend Details']:
                                details = r['Trend Details']
                                f.write(f"  - Last 30 days avg: {details.get('recent_avg', 0):.2f} tools/report\n")
                                f.write(f"  - 31-60 days avg: {details.get('medium_avg', 0):.2f} tools/report\n")
                                f.write(f"  - 61-90 days avg: {details.get('older_avg', 0):.2f} tools/report\n")
                            adoption = r['Adoption Date'].strftime('%Y-%m-%d') if ('Adoption Date' in r and pd.notna(r['Adoption Date'])) else 'N/A'
                            first_seen = r['First Appearance'].strftime('%Y-%m-%d') if pd.notna(r['First Appearance']) else 'N/A'
                            last_seen = r['Overall Recency'].strftime('%Y-%m-%d') if pd.notna(r['Overall Recency']) else 'N/A'
                            f.write(f"Adoption Date: {adoption}\n")
                            f.write(f"First Seen: {first_seen}\n")
                            f.write(f"Last Seen: {last_seen}\n")
                            user_data = self.full_usage_data[self.full_usage_data['User Principal Name'] == email].copy()
                            if not user_data.empty:
                                f.write("Records:\n")
                                for _, row in user_data.sort_values(by='Report Refresh Date', ascending=False).iterrows():
                                    f.write(f"  Report Date: {row['Report Refresh Date'].strftime('%Y-%m-%d')}\n")
                                    tools_used_in_report = [f"    - {col.replace('Last activity date of ', '').replace(' (UTC)', '')}: {row[col].strftime('%Y-%m-%d')}" for col in tool_cols if pd.notna(row[col])]
                                    if tools_used_in_report:
                                        f.write("\n".join(tools_used_in_report) + "\n")
                                    else:
                                        f.write("    - No specific tool activity recorded for this date.\n")
                            f.write("\n")
                debug_files = {'path': debug_root} if debug_root else {}
            except Exception as _:
                pass
            self.update_status("Success! Reports are ready for download.")
            cat_counts = {
                'power_user': int((self.utilized_metrics_df['Classification'].str.startswith('Power User')).sum()),
                'consistent_user': int((self.utilized_metrics_df['Classification'].str.startswith('Consistent User')).sum()),
                'coaching': int((self.utilized_metrics_df['Classification'].str.startswith('Coaching Opportunity')).sum()),
                'new_user': int((self.utilized_metrics_df['Classification'].str.startswith('New User')).sum()),
                'recapture': int((self.utilized_metrics_df['Classification'].str.startswith('License Recapture')).sum()),
            }
            return { 'status': 'success', 'dashboard': { 'total': len(self.utilized_metrics_df), 'categories': cat_counts }, 'reports': { 'excel_bytes': excel_bytes, 'html_string': leaderboard_html }, 'deep_dive_data': { 'full_usage_data': self.full_usage_data, 'utilized_metrics_df': self.utilized_metrics_df, 'debug': debug_files } }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': f"An unexpected error occurred: {str(e)}"}


    def calculate_usage_complexity_over_time(self, utilized_emails):
        self.update_status("Calculating usage complexity trend...")
        if self.full_usage_data is None or self.full_usage_data.empty:
            return pd.DataFrame()

        # Ensure 'Report Refresh Date' is datetime
        df = self.full_usage_data.copy()
        df['Report Refresh Date'] = pd.to_datetime(df['Report Refresh Date'], errors='coerce')
        
        # Identify tool columns dynamically
        copilot_tool_cols = [col for col in df.columns if 'Last activity date of' in col]
        if not copilot_tool_cols:
            self.update_status("No tool columns found for complexity calculation.")
            return pd.DataFrame()

        # Calculate average tools used per report (similar to recent_activity in deep dive)
        df['avg_tools_per_report_recent'] = 0
        for idx, row in df.iterrows():
            recent_tools = 0
            report_date = row['Report Refresh Date']
            for col in copilot_tool_cols:
                if pd.notna(row[col]):
                    last_activity = row[col]
                    # Consider tool "recently used" if within 30 days of report
                    days_since_use = (report_date - last_activity).days
                    if days_since_use <= 30:  # Tool used in last 30 days
                        recent_tools += 1
            df.at[idx, 'avg_tools_per_report_recent'] = recent_tools

        # Create month column for grouping
        df['Month'] = df['Report Refresh Date'].dt.to_period('M').dt.to_timestamp()
        
        # Calculate average tools per month for all users
        global_monthly = df.groupby('Month')['avg_tools_per_report_recent'].agg(['mean', 'count'])
        global_complexity = global_monthly['mean'].to_frame(name='Global Average Tools Used')
        
        # Calculate average tools per month for target users only
        target_df = df[df['User Principal Name'].isin(utilized_emails)]
        if not target_df.empty:
            target_monthly = target_df.groupby('Month')['avg_tools_per_report_recent'].agg(['mean', 'count'])
            target_complexity = target_monthly['mean'].to_frame(name='Target Average Tools Used')
        else:
            # If no target users, create empty frame with same index
            target_complexity = pd.DataFrame(index=global_complexity.index, columns=['Target Average Tools Used'])
            target_complexity.fillna(0, inplace=True)
        
        # Combine into a single DataFrame
        trend_df = pd.concat([global_complexity, target_complexity], axis=1).fillna(0)
        trend_df.index.name = 'Month'
        trend_df.reset_index(inplace=True)
        trend_df['Month'] = pd.to_datetime(trend_df['Month'])
        
        # Convert month timestamp to YYYY-MM format for display
        trend_df['Report Refresh Period'] = trend_df['Month'].dt.strftime('%Y-%m')
        
        # Reorder columns for chart compatibility: Date, Global, Target, Period
        trend_df = trend_df[['Month', 'Global Average Tools Used', 'Target Average Tools Used', 'Report Refresh Period']]
        
        # Round values to 2 decimal places for better display
        trend_df['Global Average Tools Used'] = trend_df['Global Average Tools Used'].round(2)
        trend_df['Target Average Tools Used'] = trend_df['Target Average Tools Used'].round(2)
        
        self.update_status("Usage complexity trend calculated.")
        return trend_df

    def style_excel_sheet(self, worksheet, df):
        if df.empty: return
        header_fill = PatternFill(start_color="2d3748", end_color="2d3748", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for col_num, column_title in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal='center')
        stripe_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        for row_index in range(2, len(df) + 2):
            if row_index % 2 == 1:
                for col_index in range(1, len(df.columns) + 1):
                    worksheet.cell(row=row_index, column=col_index).fill = stripe_fill
        for col_num, column_title in enumerate(df.columns, 1):
            max_length = len(str(column_title))
            for cell_value in df[column_title]:
                if len(str(cell_value)) > max_length: max_length = len(str(cell_value))
            worksheet.column_dimensions[get_column_letter(col_num)].width = max_length + 2
        red, yellow, green = "F8696B", "FFEB84", "63BE7B"
        if 'Engagement Score' in df.columns:
            col_letter = get_column_letter(df.columns.get_loc('Engagement Score') + 1)
            cell_range = f"{col_letter}2:{col_letter}{len(df)+1}"
            worksheet.conditional_formatting.add(cell_range, ColorScaleRule(start_type='min', start_color=red, mid_type='percentile', mid_value=50, mid_color=yellow, end_type='max', end_color=green))
        if 'Adjusted Consistency (%)' in df.columns:
            col_letter = get_column_letter(df.columns.get_loc('Adjusted Consistency (%)') + 1)
            cell_range = f"{col_letter}2:{col_letter}{len(df)+1}"
            worksheet.conditional_formatting.add(cell_range, DataBarRule(start_type='min', end_type='max', color=green))
        if 'Adoption Velocity' in df.columns:
            col_letter = get_column_letter(df.columns.get_loc('Adoption Velocity') + 1)
            cell_range = f"{col_letter}2:{col_letter}{len(df)+1}"
            worksheet.conditional_formatting.add(cell_range, ColorScaleRule(start_type='min', start_color=yellow, mid_type='percentile', mid_value=50, mid_color=yellow, end_type='max', end_color=green))

    def create_excel_report(self, top_df, under_df, realloc_df, all_df=None, usage_complexity_trend_df=None):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            cols = ['Global Rank', 'Email', 'Adjusted Consistency (%)', 'Overall Recency', 'Total Tools Used', 'Avg Tools / Report', 'Adoption Velocity', 'Tool Expansion Rate', 'Days Since License', 'Usage Trend', 'Engagement Score']
            sheets = {
                'Leaderboard': all_df.sort_values(by="Global Rank") if all_df is not None and not all_df.empty else pd.DataFrame(),
            }
            if all_df is not None and not all_df.empty:
                # Add No Use tabs based on days of inactivity
                for days in [30, 45, 60, 90]:
                    # Calculate users with no activity in the last X days
                    inactive_users = all_df[
                        (pd.to_datetime(all_df['Overall Recency']) < (self.reference_date - pd.Timedelta(days=days))) |
                        pd.isna(all_df['Overall Recency'])
                    ]
                    if not inactive_users.empty:
                        sheets[f'No Use {days}d'] = inactive_users.sort_values(by="Global Rank")
            wrote_any = False
            
            # Create all category sheets first
            # Map internal column names to display names for Excel
            col_display_map = {
                'Usage Complexity': 'Total Tools Used'
            }
            for sheet_name, df in sheets.items():
                df_local = df.copy()
                # Rename columns for display
                for old_name, new_name in col_display_map.items():
                    if old_name in df_local.columns:
                        df_local = df_local.rename(columns={old_name: new_name})
                for c in cols:
                    if c not in df_local.columns:
                        df_local[c] = pd.Series([np.nan]*len(df_local))
                df_to_write = df_local[cols] if not df_local.empty else pd.DataFrame(columns=cols)
                df_to_write.to_excel(writer, sheet_name=sheet_name, index=False, float_format="%.2f")
                self.style_excel_sheet(writer.sheets[sheet_name], df_to_write)

                # Add disclaimer to Leaderboard
                if sheet_name == 'Leaderboard':
                    worksheet = writer.sheets[sheet_name]
                    
                    # Insert a new row at row 2, which shifts all data down
                    worksheet.insert_rows(2)
                    
                    # Merge the cells in the new row to span the table width
                    worksheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(df_to_write.columns))
                    
                    # Get the cell for the disclaimer
                    disclaimer_cell = worksheet.cell(row=2, column=1)
                    
                    # Set the disclaimer text
                    disclaimer_cell.value = "The data on this tab is only used to calculate Leaderboard Rankings, and NOT for licensing determination."
                    
                    # Define the styles to match the header
                    header_fill = PatternFill(start_color="2d3748", end_color="2d3748", fill_type="solid")
                    header_font = Font(bold=True, color="FFFFFF")
                    
                    # Apply the styles to the disclaimer cell
                    disclaimer_cell.fill = header_fill
                    disclaimer_cell.font = header_font
                    disclaimer_cell.alignment = Alignment(horizontal='center', vertical='center')
                wrote_any = wrote_any or not df_to_write.empty
            
            # Add Usage_Trend sheet at the end
            if usage_complexity_trend_df is not None and not usage_complexity_trend_df.empty:
                sheet_name = "Usage_Trend"
                
                # Create a clean version of the data for Excel
                clean_trend_df = usage_complexity_trend_df.copy()
                clean_trend_df = clean_trend_df.dropna()  # Remove any None values
                
                # Write the data to Excel
                clean_trend_df.to_excel(writer, sheet_name=sheet_name, index=False)
                trend_ws = writer.sheets[sheet_name]

                try:
                    # Create a professional Line Chart
                    chart = LineChart()
                    chart.title = "Average Tools Used Over Time"
                    chart.style = 2  # Simple, clean style
                    
                    # Set axis titles
                    chart.x_axis.title = "Period (Month)"
                    chart.y_axis.title = "Average Tools Used"
                    
                    # Position legend at the bottom without overlay
                    chart.legend.position = 'b'
                    chart.legend.overlay = False
                    # Get data range - only include actual data rows
                    num_data_rows = len(clean_trend_df)
                    if num_data_rows > 0:
                        # Data columns: B (Global) and C (Target), starting from row 1 (including headers)
                        data = Reference(trend_ws, min_col=2, min_row=1, max_col=3, max_row=num_data_rows + 1)
                        # Categories: Column D (Report Refresh Period), starting from row 2 (excluding header)
                        # Using string categories instead of dates for better Excel compatibility
                        categories = Reference(trend_ws, min_col=4, min_row=2, max_row=num_data_rows + 1)
                        
                        chart.add_data(data, titles_from_data=True)
                        chart.set_categories(categories)
                        
                        # Data labels removed - chart will show axis labels only
                        
                        # Set axis formats - x-axis is now text, y-axis is numeric
                        chart.x_axis.number_format = '@'  # Text format for string categories
                        chart.y_axis.number_format = '0.0'  # One decimal place for better readability
                        
                        # Configure axis properties for better visibility
                        # Remove explicit tick label positioning to use defaults
                        chart.x_axis.tickLblPos = None  # Use default positioning
                        chart.y_axis.tickLblPos = None  # Use default positioning
                        # Ensure axes are visible
                        chart.x_axis.delete = False
                        chart.y_axis.delete = False
                        # Configure tick marks for better visibility
                        chart.x_axis.majorTickMark = 'out'  # Show major tick marks outside
                        chart.x_axis.minorTickMark = 'none'  # No minor ticks
                        chart.y_axis.majorTickMark = 'out'  # Show major tick marks outside
                        chart.y_axis.minorTickMark = 'none'  # No minor ticks
                        # Ensure tick labels are shown
                        if hasattr(chart.x_axis, 'tickLblSkip'):
                            chart.x_axis.tickLblSkip = 1  # Show every label
                        if hasattr(chart.x_axis, 'tickMarkSkip'):
                            chart.x_axis.tickMarkSkip = 1  # Show every tick mark
                        
                        # Set explicit axis scaling for y-axis
                        y_min = clean_trend_df[['Global Average Tools Used', 'Target Average Tools Used']].min().min()
                        y_max = clean_trend_df[['Global Average Tools Used', 'Target Average Tools Used']].max().max()
                        chart.y_axis.scaling.min = max(0, y_min * 0.9)  # Start from 0 or slightly below min
                        chart.y_axis.scaling.max = y_max * 1.1  # Go slightly above max
                        
                        # Set chart size - larger to accommodate legend and labels
                        chart.width = 18
                        chart.height = 10
                        
                        # Add chart to sheet - position further right to accommodate legend
                        trend_ws.add_chart(chart, "G2")  # Position to the right of data
                        
                        # Auto-fit columns for better visibility
                        for column in trend_ws.columns:
                            max_length = 0
                            column_letter = column[0].column_letter if column else 'A'
                            for cell in column:
                                try:
                                    if cell.value and len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = max(12, max_length + 2)
                            trend_ws.column_dimensions[column_letter].width = adjusted_width

                        wrote_any = True
                except Exception as chart_error:
                    print(f"Chart creation error: {chart_error}")
                    import traceback
                    traceback.print_exc()
                    # If chart fails, still mark as wrote_any since data was written
                    wrote_any = True
            
            writer.book.active = 0
            if not wrote_any:
                return None
        output.seek(0)
        return output.getvalue()
    def create_leaderboard_html(self, all_users_df):
        if all_users_df is None or all_users_df.empty: return ""
        leaderboard_data = all_users_df.sort_values(by="Global Rank")
        
        html_head = r'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Leaderboard - Haleon Theme</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
                .leaderboard-component { border-radius: 1rem; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1); overflow: hidden; border: 1px solid #e5e7eb; }
                .title-banner { background-color: #000000; }
                .table-container { background-color: #FFFFFF; }
                .table-header { background-color: #2d3748; }
                .table-row:nth-child(even) { background-color: #f9fafb; }
                .table-row:hover { background-color: #f0f0f0; }
                .rank-badge { font-weight: 700; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: #000; }
                .progress-bar-container { background-color: #e5e7eb; border-radius: 9999px; height: 8px; width: 100%; }
                .progress-bar { background: #39FF14; border-radius: 9999px; height: 100%; }
                .trend-icon.Accelerating { color: #16a34a; }
                .trend-icon.Recovering { color: #22c55e; }
                .trend-icon.New.Momentum { color: #3b82f6; }
                .trend-icon.Stable { color: #f59e0b; }
                .trend-icon.Cooling { color: #f97316; }
                .trend-icon.Declining { color: #ef4444; }
                .trend-icon.Dormant { color: #a855f7; }
                .trend-icon.Inactive { color: #6b7280; }
                .trend-icon.Increasing { color: #16a34a; }
                .trend-icon.Decreasing { color: #ef4444; }
                .trend-icon.N\/A { color: #6b7280; }
                .neon-green-text { color: #16a34a; }
                .user-email { font-weight: 600; color: #000000; }
            </style>
        </head>
        <body class="p-4 sm:p-6 lg:p-8">
            <div class="leaderboard-component w-full max-w-5xl mx-auto">
                <div class="title-banner p-6 text-center">
                    <h1 class="text-4xl font-bold text-white mb-2">Copilot Usage Leaderboard</h1>
                    <p class="text-gray-300">Ranking by Engagement Score</p>
                </div>
                <div class="table-container">
                    <div class="overflow-x-auto">
                        <div class="min-w-full inline-block align-middle">
                            <div class="table-header">
                                <div class="grid grid-cols-12 gap-4 px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-white">
                                    <div class="col-span-1">Rank</div>
                                    <div class="col-span-5">User</div>
                                    <div class="col-span-2 text-center">Adjusted Consistency</div>
                                    <div class="col-span-2 text-center">Trend</div>
                                    <div class="col-span-2 text-right">Engagement</div>
                                </div>
                            </div>
                            <div class="divide-y divide-gray-200">
        '''
        
        html_rows = ""
        max_score = leaderboard_data['Engagement Score'].max() if not leaderboard_data.empty else 100.0
        max_consistency = leaderboard_data['Adjusted Consistency (%)'].max() if not leaderboard_data.empty else 100.0
        
        for _, user_row in leaderboard_data.iterrows():
            if pd.isna(user_row['Email']): continue
            
            rank = int(user_row['Global Rank'])
            # Use rank position for color calculation instead of score
            total_users = len(leaderboard_data)
            rank_percentage = ((total_users - rank + 1) / total_users) * 100
            hue = rank_percentage * 1.2  # Green for top ranks, red for bottom
            badge_color = f"hsl({hue}, 80%, 50%)"
            trend = user_row['Usage Trend']
            trend_icon_map = {
                'Accelerating': 'fa-rocket',
                'Recovering': 'fa-arrow-trend-up', 
                'Stable': 'fa-minus',
                'Cooling': 'fa-arrow-trend-down',
                'Declining': 'fa-angles-down',
                'New Momentum': 'fa-bolt',
                'Dormant': 'fa-pause',
                'Inactive': 'fa-stop',
                'Increasing': 'fa-arrow-trend-up',  # Legacy support
                'Decreasing': 'fa-arrow-trend-down',  # Legacy support
                'N/A': 'fa-question'
            }
            trend_icon = f"fa-solid {trend_icon_map.get(trend, 'fa-minus')}"
            
            html_rows += f'''
            <div class="grid grid-cols-12 gap-4 px-6 py-3 items-center table-row text-gray-800">
                <div class="col-span-1"><div class="rank-badge" style="background-color: {badge_color};"><span>{rank}</span></div></div>
                <div class="col-span-5"><div class="user-email">{user_row['Email']}</div></div>
                <div class="col-span-2 text-center">
                    <div class="text-sm font-semibold neon-green-text">{user_row['Adjusted Consistency (%)']:.1f}%</div>
                    <div class="progress-bar-container mt-1"><div class="progress-bar" style="width: {min(100, (user_row['Adjusted Consistency (%)'] / max_consistency) * 100):.1f}%"></div></div>
                </div>
                <div class="col-span-2 text-center"><i class="trend-icon {trend} {trend_icon} fa-lg"></i></div>
                <div class="col-span-2 text-right"><div class="text-sm font-bold neon-green-text">{user_row['Engagement Score']:.2f}</div></div>
            </div>
            '''
        
        html_foot = r'''
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html_head + html_rows + html_foot
