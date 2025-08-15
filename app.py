import os
import shutil
import uuid
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit
import pandas as pd
import base64
import io
# removed unused matplotlib import
from analysis_logic import CopilotAnalyzer
import traceback
from config import TARGET_PRESETS

async_mode = "eventlet"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-different-secret-key-for-sure!'
TEMP_FOLDER = 'temp_uploads'
app.config['TEMP_FOLDER'] = TEMP_FOLDER

socketio = SocketIO(app, async_mode=async_mode)

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['file_paths'] = {'usage': {}, 'target': None}
    
    target_preset_key = request.args.get('target')
    preset_data = TARGET_PRESETS.get(target_preset_key, {})
    pre_selected_managers = preset_data.get('managers', [])
    
    return render_template('index.html', pre_selected_managers=pre_selected_managers)

@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Session not found. Please refresh the page.'}), 400
    
    user_id = session['user_id']
    session_folder = os.path.join(app.config['TEMP_FOLDER'], user_id)
    os.makedirs(session_folder, exist_ok=True)

    file = request.files.get('file')
    file_type = request.form.get('file_type')
    if not file or not file_type:
        return jsonify({'status': 'error', 'message': 'Missing file or file type.'}), 400
    
    save_path = os.path.join(session_folder, file.filename)
    file.save(save_path)

    if 'file_paths' not in session:
        session['file_paths'] = {'usage': {}, 'target': None}

    if file_type == 'target':
        session['file_paths']['target'] = save_path
        session.modified = True
        try:
            df = pd.read_csv(save_path, usecols=['UserPrincipalName', 'Company', 'Department', 'City', 'ManagerLine'], dtype=str, encoding='utf-8-sig')
            df.fillna('', inplace=True)

            filters = {
                'companies': sorted(df['Company'].unique().tolist()),
                'departments': sorted(df['Department'].unique().tolist()),
                'locations': sorted(df['City'].unique().tolist())
            }
            
            # Check if a preset was used to determine manager filter behavior
            target_preset_key = request.args.get('target')
            if target_preset_key and target_preset_key in TARGET_PRESETS:
                # If a preset is active, use its managers for the filter dropdown
                filters['managers'] = TARGET_PRESETS[target_preset_key].get('managers', [])
            else:
                # Otherwise, extract all managers from the uploaded file
                all_managers = set()
                for chain in df['ManagerLine']:
                    all_managers.update([m.strip() for m in chain.split('->') if m])
                filters['managers'] = sorted(list(all_managers))
            
            return jsonify({'status': 'success', 'type': 'target', 'filters': filters})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': f'Error parsing CSV: {e}'}), 500

    elif file_type == 'usage':
        session['file_paths']['usage'][file.filename] = save_path
        session.modified = True
        return jsonify({'status': 'success', 'type': 'usage', 'filename': file.filename})

@app.before_request
def clear_stale_temp():
    if getattr(app, "_temp_cleared", False):
        return
    if os.path.exists(app.config['TEMP_FOLDER']):
        for entry in os.listdir(app.config['TEMP_FOLDER']):
            path = os.path.join(app.config['TEMP_FOLDER'], entry)
            try:
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            except Exception:
                pass
    app._temp_cleared = True

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    user_id = session.get('user_id')
    if user_id:
        session_folder = os.path.join(app.config['TEMP_FOLDER'], user_id)
        if os.path.exists(session_folder):
            print(f"Cleaning up session folder: {session_folder}")
            shutil.rmtree(session_folder)

@socketio.on('start_analysis')
def handle_analysis_request(data):
    print("Received start_analysis request from client.") # Diagnostic print
    user_id = session.get('user_id')
    if not user_id:
        emit('analysis_error', {'message': 'User session not found. Please refresh the page.'})
        return

    client_usage_filenames = data.get('usage_filenames', [])
    if not client_usage_filenames:
        emit('analysis_error', {'message': 'No usage report files were specified by the client.'})
        return

    session_folder = os.path.join(app.config['TEMP_FOLDER'], user_id)
    analysis_target_files = {
        filename: os.path.join(session_folder, filename)
        for filename in client_usage_filenames
    }
    
    # Verify that the files actually exist
    for path in analysis_target_files.values():
        if not os.path.exists(path):
            emit('analysis_error', {'message': f'Server-side error: File not found at {path}. Please try re-uploading.'})
            return

    target_file = session.get('file_paths', {}).get('target')
        
    runner = CopilotAnalyzer(socketio, request.sid)
    socketio.start_background_task(run_analysis_and_emit, runner, analysis_target_files, target_file, data['filters'], request.sid, user_id)

def run_analysis_and_emit(runner, usage_file_paths, target_file_path, filters, sid, user_id):
    results = runner.execute_analysis(usage_file_paths, target_file_path, filters)
    
    if 'error' in results:
        socketio.emit('analysis_error', {'message': results['error']}, to=sid)
    else:
        deep_dive_data = results.pop('deep_dive_data')
        deep_dive_data['filters_applied'] = filters # Store the filters that were applied
        session_folder = os.path.join(app.config['TEMP_FOLDER'], user_id)
        os.makedirs(session_folder, exist_ok=True)
        deep_dive_path = os.path.join(session_folder, 'deep_dive_data.pkl')
        pd.to_pickle(deep_dive_data, deep_dive_path)
        
        excel_bytes = results['reports']['excel_bytes']
        if excel_bytes is None:
            excel_b64 = ''
        else:
            try:
                print(f"Excel bytes length: {len(excel_bytes)}")
            except Exception:
                print("Excel bytes length: <unavailable>")
            excel_b64 = base64.b64encode(excel_bytes).decode('ascii') if isinstance(excel_bytes, (bytes, bytearray)) else ''
        html_b64 = base64.b64encode(results['reports']['html_string'].encode('utf-8')).decode('ascii')
        payload = { 'dashboard': results['dashboard'], 'reports': { 'excel_b64': excel_b64, 'html_b64': html_b64 } }
        socketio.emit('analysis_complete', payload, to=sid)

@socketio.on('perform_deep_dive')
def handle_deep_dive(data):
    user_id = session.get('user_id')
    session_folder = os.path.join(app.config['TEMP_FOLDER'], user_id)
    deep_dive_path = os.path.join(session_folder, 'deep_dive_data.pkl')

    if not os.path.exists(deep_dive_path):
        emit('deep_dive_error', {'message': 'No analysis data found.'})
        return

    deep_dive_data = pd.read_pickle(deep_dive_path)
    try:
        user_email = data['email'].strip().lower()
    except (KeyError, AttributeError):
        emit('deep_dive_error', {'message': 'Invalid email provided for deep dive.'})
        return

    full_usage_data = deep_dive_data['full_usage_data']
    utilized_metrics_df = deep_dive_data['utilized_metrics_df']
    filters_applied = deep_dive_data.get('filters_applied', {}) # Retrieve stored filters

    user_data = full_usage_data[full_usage_data['User Principal Name'] == user_email].copy()
    user_metrics = utilized_metrics_df[utilized_metrics_df['Email'] == user_email]

    if user_data.empty or user_metrics.empty:
        emit('deep_dive_result', {'text': f"No records found for '{user_email}'.", 'chart_user': None, 'chart_group': None})
        return

    metrics = user_metrics.iloc[0]
    text_result = f"--- Summary for {user_email} ---\nClassification: {metrics['Classification']}\nJustification: {metrics['Justification']}\n\nGlobal Rank: {int(metrics['Global Rank'])}\nAdjusted Consistency: {metrics['Adjusted Consistency (%)']:.1f}%\nOriginal Consistency: {metrics['Usage Consistency (%)']:.1f}%\nAdoption Date: {metrics['Adoption Date'].strftime('%Y-%m-%d') if pd.notna(metrics.get('Adoption Date')) else 'N/A'}\nFirst Seen: {metrics['First Appearance'].strftime('%Y-%m-%d') if pd.notna(metrics['First Appearance']) else 'N/A'}\nLast Seen: {metrics['Overall Recency'].strftime('%Y-%m-%d') if pd.notna(metrics['Overall Recency']) else 'N/A'}\nDays Since License: {int(metrics['Days Since License']) if pd.notna(metrics.get('Days Since License')) else 'N/A'}\nUsage Complexity (Total Tools): {int(metrics['Usage Complexity'])}\nAvg Tools per Report: {metrics['Avg Tools / Report']:.2f}\nAdoption Velocity: {metrics['Adoption Velocity']:.4f} tools/day\nEngagement Score: {metrics['Engagement Score']:.2f}\nUsage Trend: {metrics['Usage Trend']}\n\n"
    tool_cols = [col for col in full_usage_data.columns if 'Last activity date of' in col]
    if metrics['Usage Complexity'] > 0:
        text_result += f"--- Detailed Records ---\n"
        for _, row in user_data.sort_values(by="Report Refresh Date", ascending=False).iterrows():
            text_result += f"\nReport Date: {row['Report Refresh Date'].strftime('%Y-%m-%d')}\n"
            tools_used_in_report = [f"  - {col.replace('Last activity date of ', '').replace(' (UTC)', '')}: {row[col].strftime('%Y-%m-%d')}" for col in tool_cols if pd.notna(row[col])]
            if tools_used_in_report:
                text_result += "\n".join(tools_used_in_report) + "\n"
            else:
                text_result += "  - No specific tool activity recorded for this date.\n"
    
    # Prepare chart data
    chart_data = {
        'categories': [],
        'series': [
            {'name': 'User', 'data': []},
            {'name': 'Sample Group', 'data': []},
            {'name': 'Global', 'data': []}
        ]
    }
    try:
        # Calculate actual recent activity for user
        user_data['recent_activity'] = 0
        for idx, row in user_data.iterrows():
            recent_tools = 0
            report_date = row['Report Refresh Date']
            for col in tool_cols:
                if pd.notna(row[col]):
                    last_activity = row[col]
                    # Consider tool "recently used" if within 30 days of report
                    days_since_use = (report_date - last_activity).days
                    if days_since_use <= 30:  # Tool used in last 30 days
                        recent_tools += 1
            user_data.at[idx, 'recent_activity'] = recent_tools

        # Group by report date - use mean to show average activity level
        graph_data_user = user_data.groupby('Report Refresh Date')['recent_activity'].mean().sort_index()

        # Filtered group data - apply same logic
        if not filters_applied or all(not v for v in filters_applied.values()):
            filtered_group_usage_data = full_usage_data.copy()
        else:
            filtered_user_emails = utilized_metrics_df['Email'].str.lower().tolist()
            filtered_group_usage_data = full_usage_data[full_usage_data['User Principal Name'].isin(filtered_user_emails)].copy()

        # Calculate recent activity for group
        filtered_group_usage_data['recent_activity'] = 0
        for idx, row in filtered_group_usage_data.iterrows():
            recent_tools = 0
            report_date = row['Report Refresh Date']
            for col in tool_cols:
                if pd.notna(row[col]):
                    last_activity = row[col]
                    days_since_use = (report_date - last_activity).days
                    if days_since_use <= 30:
                        recent_tools += 1
            filtered_group_usage_data.at[idx, 'recent_activity'] = recent_tools

        graph_data_group = filtered_group_usage_data.groupby('Report Refresh Date')['recent_activity'].mean().sort_index()

        # Global data - apply same logic
        all_usage_data = full_usage_data.copy()
        all_usage_data['recent_activity'] = 0
        for idx, row in all_usage_data.iterrows():
            recent_tools = 0
            report_date = row['Report Refresh Date']
            for col in tool_cols:
                if pd.notna(row[col]):
                    last_activity = row[col]
                    days_since_use = (report_date - last_activity).days
                    if days_since_use <= 30:
                        recent_tools += 1
            all_usage_data.at[idx, 'recent_activity'] = recent_tools

        graph_data_global = all_usage_data.groupby('Report Refresh Date')['recent_activity'].mean().sort_index()

        # Combine all date indexes
        all_dates = sorted(list(set(graph_data_user.index) | set(graph_data_group.index) | set(graph_data_global.index)))
        chart_data['categories'] = [d.strftime('%Y-%m-%d') for d in all_dates]

        # Reindex and fill data - use float for accuracy, not int
        chart_data['series'][0]['data'] = graph_data_user.reindex(all_dates, fill_value=0).round(2).tolist()
        chart_data['series'][1]['data'] = graph_data_group.reindex(all_dates, fill_value=0).round(2).tolist()
        chart_data['series'][2]['data'] = graph_data_global.reindex(all_dates, fill_value=0).round(2).tolist()

    except Exception as e:
        print(f"Error generating chart data: {e}")
        emit('deep_dive_error', {'message': 'Error preparing chart data.'})
        return

    emit('deep_dive_result', {'text': text_result, 'chart_data': chart_data})

if __name__ == '__main__':
    print("Starting server... Access from your network at http://<your-ip-address>:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
