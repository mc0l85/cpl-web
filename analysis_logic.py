import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule

class AnalysisRunner:
    def __init__(self, socketio, sid):
        self.socketio = socketio
        self.sid = sid
        self.full_usage_data = None
        self.utilized_metrics_df = None

    def update_status(self, message):
        self.socketio.emit('status_update', {'message': message}, to=self.sid)
        self.socketio.sleep(0.1)

    def _get_justification(self, row, total_months, grace_period_check_date, sixty_days_ago, ninety_days_ago):
        if row['Classification'] == 'Top Utilizer':
            return "High Engagement"
        reasons = []
        is_new_user = pd.notna(row['First Appearance']) and row['First Appearance'] > grace_period_check_date
        if is_new_user: reasons.append("New user (in 90-day grace period)")
        if row.get('is_reactivated', False): reasons.append("Reactivation Possible")
        if row['Usage Complexity'] == 0 and not is_new_user: reasons.append("No tool usage recorded")
        elif pd.notna(row['Overall Recency']) and row['Overall Recency'] < ninety_days_ago: reasons.append("No activity in 90+ days")
        elif pd.notna(row['Overall Recency']) and (ninety_days_ago <= row['Overall Recency'] < sixty_days_ago): reasons.append("No activity in 60-89 days")
        if row['Usage Trend'] == 'Decreasing': reasons.append("Downward usage trend")
        active_months = int(row['Usage Consistency (%)'] * total_months / 100) if total_months > 0 else 0
        if row['Appearances'] == 1 and not is_new_user: reasons.append("Single report appearance")
        elif row['Usage Consistency (%)'] < 50 and not is_new_user: reasons.append(f"Low consistency (active in {active_months} of {total_months} months)")
        return "; ".join(reasons) if reasons else "High Engagement"

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
            if target_user_path:
                self.update_status("Applying filters...")
                target_df = pd.read_csv(target_user_path, encoding='utf-8-sig')
                target_df['UserPrincipalName'] = target_df['UserPrincipalName'].str.lower()
                if filters.get('companies'):
                    vals = set([v.lower() for v in filters['companies']])
                    target_df = target_df[target_df['Company'].str.lower().isin(vals)]
                if filters.get('departments'):
                    vals = set([v.lower() for v in filters['departments']])
                    target_df = target_df[target_df['Department'].str.lower().isin(vals)]
                if filters.get('locations'):
                    vals = set([v.lower() for v in filters['locations']])
                    target_df = target_df[target_df['City'].str.lower().isin(vals)]
                if filters.get('managers'):
                    target_df['ManagerLine_lc'] = target_df['ManagerLine'].str.lower().fillna('')
                    managers_lc = [m.strip().lower() for m in filters['managers']]
                    target_df = target_df[target_df['ManagerLine_lc'].apply(lambda s: any(m in s for m in managers_lc))]
                utilized_emails = utilized_emails.intersection(set(target_df['UserPrincipalName'].str.lower()))
            if not utilized_emails: return {'error': "No matching users found to analyze."}
            self.update_status("2. Calculating user metrics...")
            matched_users_df = usage_df[usage_df['User Principal Name'].isin(utilized_emails)].copy()
            copilot_tool_cols = [col for col in matched_users_df.columns if 'Last activity date of' in col]
            min_report_date, max_report_date = usage_df['Report Refresh Date'].min(), usage_df['Report Refresh Date'].max()
            total_months_in_period = (max_report_date.year - min_report_date.year) * 12 + max_report_date.month - min_report_date.month + 1
            user_metrics = []
            for email in utilized_emails:
                user_data = matched_users_df[matched_users_df['User Principal Name'] == email]
                user_data_sorted = user_data.sort_values(by='Report Refresh Date')
                user_data_sorted['Row Recency'] = user_data_sorted[copilot_tool_cols].max(axis=1)
                is_reactivated = False
                recency_series = user_data_sorted['Row Recency'].dropna()
                if len(recency_series) >= 3:
                    latest_date, prev_date_1, prev_date_2 = recency_series.iloc[-1], recency_series.iloc[-2], recency_series.iloc[-3]
                    if pd.notna(latest_date) and pd.notna(prev_date_1) and pd.notna(prev_date_2):
                        if prev_date_1 == prev_date_2 and latest_date > prev_date_1: is_reactivated = True
                activity_dates = pd.to_datetime(user_data[copilot_tool_cols].stack().dropna().unique())
                if len(activity_dates) == 0:
                    first_activity, last_activity, active_months, complexity, avg_tools_per_month, trend = pd.NaT, pd.NaT, 0, 0, 0, "N/A"
                    report_dates = user_data['Report Refresh Date'].unique()
                    if len(report_dates) > 0: first_activity = pd.to_datetime(report_dates).min()
                else:
                    first_activity, last_activity = activity_dates.min(), activity_dates.max()
                    active_months = len(pd.to_datetime(activity_dates).to_period('M').unique())
                    complexity = user_data[copilot_tool_cols].notna().any().sum()
                    monthly_activity = user_data[copilot_tool_cols].stack().dropna().reset_index().rename(columns={'level_1': 'Tool', 0: 'Date'})
                    monthly_activity['Month'] = pd.to_datetime(monthly_activity['Date']).dt.to_period('M')
                    avg_tools_per_month = monthly_activity.groupby('Month')['Tool'].nunique().mean() if not monthly_activity.empty else 0
                    trend = "N/A"
                    if len(activity_dates) > 1:
                        trend = "Stable"
                        timeline_midpoint = first_activity + (last_activity - first_activity) / 2
                        first_half_activity, second_half_activity = monthly_activity[monthly_activity['Date'] <= timeline_midpoint], monthly_activity[monthly_activity['Date'] > timeline_midpoint]
                        if not first_half_activity.empty and not second_half_activity.empty:
                            if second_half_activity['Tool'].nunique() > first_half_activity['Tool'].nunique(): trend = "Increasing"
                            elif second_half_activity['Tool'].nunique() < first_half_activity['Tool'].nunique(): trend = "Decreasing"
                consistency = (active_months / total_months_in_period) * 100 if total_months_in_period > 0 else 0
                user_metrics.append({'Email': email, 'Usage Consistency (%)': consistency, 'Overall Recency': last_activity, 'Usage Complexity': complexity, 'Avg Tools / Report': avg_tools_per_month, 'Usage Trend': trend, 'Appearances': user_data['Report Refresh Date'].nunique(), 'First Appearance': first_activity, 'is_reactivated': is_reactivated})
            self.utilized_metrics_df = pd.DataFrame(user_metrics)
            if self.utilized_metrics_df.empty: return {'error': "No data available for the selected users."}
            max_consistency, max_complexity, max_avg_complexity = self.utilized_metrics_df['Usage Consistency (%)'].max(), self.utilized_metrics_df['Usage Complexity'].max(), self.utilized_metrics_df['Avg Tools / Report'].max()
            self.utilized_metrics_df['consistency_norm'] = self.utilized_metrics_df['Usage Consistency (%)'] / max_consistency if max_consistency > 0 else 0
            self.utilized_metrics_df['complexity_norm'] = self.utilized_metrics_df['Usage Complexity'] / max_complexity if max_complexity > 0 else 0
            self.utilized_metrics_df['avg_complexity_norm'] = self.utilized_metrics_df['Avg Tools / Report'] / max_avg_complexity if max_avg_complexity > 0 else 0
            self.utilized_metrics_df['Engagement Score'] = self.utilized_metrics_df['consistency_norm'] + self.utilized_metrics_df['complexity_norm'] + self.utilized_metrics_df['avg_complexity_norm']
            self.utilized_metrics_df = self.utilized_metrics_df.sort_values(by=["Engagement Score", "Usage Complexity"], ascending=[False, False]).reset_index(drop=True)
            self.utilized_metrics_df['Global Rank'] = self.utilized_metrics_df.index + 1
            self.update_status("3. Classifying users...")
            reference_date = usage_df['Report Refresh Date'].max()
            grace_period_check_date, sixty_days_ago, ninety_days_ago = reference_date - timedelta(days=90), reference_date - timedelta(days=60), reference_date - timedelta(days=90)
            self.utilized_metrics_df['Classification'] = 'Top Utilizer'
            for index, row in self.utilized_metrics_df.iterrows():
                is_new_user = pd.notna(row['First Appearance']) and row['First Appearance'] > grace_period_check_date
                if is_new_user:
                    self.utilized_metrics_df.loc[index, 'Classification'] = 'Under-Utilized'
                    continue

                # Reallocation criteria (strictest)
                if (row['Usage Complexity'] == 0) or \
                   (pd.notna(row['Overall Recency']) and row['Overall Recency'] < ninety_days_ago) or \
                   ((row['Usage Consistency (%)'] < 25) and not is_new_user):
                    self.utilized_metrics_df.loc[index, 'Classification'] = 'For Reallocation'

                # Under-utilized criteria (less strict)
                elif (pd.notna(row['Overall Recency']) and (ninety_days_ago <= row['Overall Recency'] < sixty_days_ago)) or \
                     (row['Usage Trend'] == 'Decreasing') or \
                     (row['Appearances'] == 1 and not is_new_user) or \
                     (row.get('is_reactivated', False)) or \
                     ((row['Usage Consistency (%)'] < 50) and not is_new_user):
                    self.utilized_metrics_df.loc[index, 'Classification'] = 'Under-Utilized'
            self.utilized_metrics_df['Justification'] = self.utilized_metrics_df.apply(self._get_justification, axis=1, total_months=total_months_in_period, grace_period_check_date=grace_period_check_date, sixty_days_ago=sixty_days_ago, ninety_days_ago=ninety_days_ago)
            reallocation_df, under_utilized_df, top_utilizers_df = self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'For Reallocation'], self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'Under-Utilized'], self.utilized_metrics_df[self.utilized_metrics_df['Classification'] == 'Top Utilizer']
            self.update_status("4. Generating reports in memory...")
            excel_bytes = self.create_excel_report(top_utilizers_df, under_utilized_df, reallocation_df)
            leaderboard_html = self.create_leaderboard_html(self.utilized_metrics_df)
            self.update_status("Success! Reports are ready for download.")
            return { 'status': 'success', 'dashboard': { 'total': len(self.utilized_metrics_df), 'top': len(top_utilizers_df), 'under': len(under_utilized_df), 'reallocate': len(reallocation_df) }, 'reports': { 'excel_bytes': excel_bytes, 'html_string': leaderboard_html }, 'deep_dive_data': { 'full_usage_data': self.full_usage_data, 'utilized_metrics_df': self.utilized_metrics_df } }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': f"An unexpected error occurred: {str(e)}"}

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
        if 'Usage Consistency (%)' in df.columns:
            col_letter = get_column_letter(df.columns.get_loc('Usage Consistency (%)') + 1)
            cell_range = f"{col_letter}2:{col_letter}{len(df)+1}"
            worksheet.conditional_formatting.add(cell_range, DataBarRule(start_type='min', end_type='max', color=green))

    def create_excel_report(self, top_df, under_df, realloc_df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            cols = ['Global Rank', 'Email', 'Classification', 'Usage Consistency (%)', 'Overall Recency', 'Usage Complexity', 'Avg Tools / Report', 'Usage Trend', 'Engagement Score', 'Justification']
            sheets = {
                'Leaderboard': pd.concat([top_df, under_df, realloc_df]).sort_values(by="Global Rank"),
                'Top Utilizers': top_df.sort_values(by="Global Rank"),
                'Under-Utilized': under_df.sort_values(by="Global Rank"),
                'For Reallocation': realloc_df.sort_values(by="Engagement Score", ascending=True)
            }
            for sheet_name, df in sheets.items():
                if not df.empty:
                    df_to_write = df[cols].copy()
                    df_to_write.to_excel(writer, sheet_name=sheet_name, index=False, float_format="%.2f")
                    self.style_excel_sheet(writer.sheets[sheet_name], df_to_write)
        return output.getvalue()

    def create_leaderboard_html(self, all_users_df):
        if all_users_df is None or all_users_df.empty: return ""
        leaderboard_data = all_users_df.sort_values(by="Global Rank")
        html_head = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Leaderboard - Haleon Theme</title><script src="https://cdn.tailwindcss.com"></script><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }.leaderboard-component { border-radius: 1rem; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1); overflow: hidden; border: 1px solid #e5e7eb; }.title-banner { background-color: #000000; }.table-container { background-color: #FFFFFF; }.table-header { background-color: #2d3748; }.table-row:nth-child(even) { background-color: #f9fafb; }.table-row:hover { background-color: #f0f0f0; }.rank-badge { font-weight: 700; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: #000; }.progress-bar-container { background-color: #e5e7eb; border-radius: 9999px; height: 8px; width: 100%; }.progress-bar { background: #39FF14; border-radius: 9999px; height: 100%; }.trend-icon.Increasing { color: #16a34a; }.trend-icon.Stable { color: #f59e0b; }.trend-icon.Decreasing { color: #ef4444; }.trend-icon.N\\/A { color: #6b7280; }.neon-green-text { color: #16a34a; }.user-email { font-weight: 600; color: #000000; }</style></head><body class="p-4 sm:p-6 lg:p-8"><div class="leaderboard-component w-full max-w-5xl mx-auto"><div class="title-banner p-6 text-center"><h1 class="text-4xl font-bold text-white mb-2">Copilot Usage Leaderboard</h1><p class="text-gray-300">Ranking by Engagement Score</p></div><div class="table-container"><div class="overflow-x-auto"><div class="min-w-full inline-block align-middle"><div class="table-header"><div class="grid grid-cols-12 gap-4 px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-white"><div class="col-span-1">Rank</div><div class="col-span-5">User</div><div class="col-span-2 text-center">Consistency</div><div class="col-span-2 text-center">Trend</div><div class="col-span-2 text-right">Engagement</div></div></div><div class="divide-y divide-gray-200">"""
        html_rows = ""
        max_score = leaderboard_data['Engagement Score'].max() if not leaderboard_data.empty else 3.0
        for _, user_row in leaderboard_data.iterrows():
            if pd.isna(user_row['Email']): continue
            rank = int(user_row['Global Rank'])
            score_percentage = (user_row['Engagement Score'] / max_score) * 100 if max_score > 0 else 0
            hue = score_percentage * 1.2
            badge_color = f"hsl({hue}, 80%, 50%)"
            trend = user_row['Usage Trend']
            trend_icon_map = {'Increasing': 'fa-arrow-trend-up', 'Decreasing': 'fa-arrow-trend-down', 'Stable': 'fa-minus', 'N/A': 'fa-question'}
            trend_icon = f"fa-solid {trend_icon_map.get(trend, 'fa-minus')}"
            html_rows += f"""<div class="grid grid-cols-12 gap-4 px-6 py-3 items-center table-row text-gray-800"><div class="col-span-1"><div class="rank-badge" style="background-color: {badge_color};"><span>{rank}</span></div></div><div class="col-span-5"><div class="user-email">{user_row['Email']}</div></div><div class="col-span-2 text-center"><div class="text-sm font-semibold neon-green-text">{user_row['Usage Consistency (%)']:.1f}%</div><div class="progress-bar-container mt-1"><div class="progress-bar" style="width: {user_row['Usage Consistency (%)']}%"></div></div></div><div class="col-span-2 text-center"><i class="trend-icon {trend} {trend_icon} fa-lg"></i></div><div class="col-span-2 text-right"><div class="text-sm font-bold neon-green-text">{user_row['Engagement Score']:.2f}</div></div></div>"""
        html_foot = """</div></div></div></div></div></body></html>"""
        return html_head + html_rows + html_foot
