
import pandas as pd
import pytest
import os
from analysis_logic import AnalysisRunner
from unittest.mock import Mock

# Define dummy CSV data for testing
DUMMY_USAGE_DATA = """User Principal Name,Report Refresh Date,Last activity date of Copilot,Last activity date of Copilot Chat
user1@example.com,2024-01-01,2024-01-01,
user1@example.com,2024-02-01,,2024-02-01
user2@example.com,2024-01-01,2024-01-01,2024-01-01
user2@example.com,2024-02-01,2024-02-01,
user3@example.com,2024-01-01,,
"""

DUMMY_TARGET_DATA = """UserPrincipalName,Company,Department,City,ManagerLine
user1@example.com,CompanyA,DeptX,City1,Manager1
user2@example.com,CompanyB,DeptY,City2,Manager2
user3@example.com,CompanyA,DeptX,City1,Manager1
"""

# Fixture to create dummy files
@pytest.fixture
def setup_dummy_files(tmp_path):
    usage_file_path = tmp_path / "usage_data.csv"
    usage_file_path.write_text(DUMMY_USAGE_DATA)

    target_file_path = tmp_path / "target_data.csv"
    target_file_path.write_text(DUMMY_TARGET_DATA)
    
    # Create the nested directory structure similar to the original temp_uploads
    temp_uploads_path = tmp_path / "temp_uploads" / "050b01f0-8f53-4d0c-86ff-a30b7479b3a0"
    temp_uploads_path.mkdir(parents=True, exist_ok=True)
    
    # Create dummy files in the expected nested path
    (temp_uploads_path / "2025_07_01_CopilotActivityUserDetail.csv").write_text(DUMMY_USAGE_DATA)
    (temp_uploads_path / "2025_07_04_User_Activity_Report.csv").write_text(DUMMY_USAGE_DATA)
    (temp_uploads_path / "202507Jul-30 - ManagerReport.csv").write_text(DUMMY_TARGET_DATA)


    return {
        "usage_files": {
            "file1": str(temp_uploads_path / "2025_07_01_CopilotActivityUserDetail.csv"),
            "file2": str(temp_uploads_path / "2025_07_04_User_Activity_Report.csv")
        },
        "target_file": str(temp_uploads_path / "202507Jul-30 - ManagerReport.csv")
    }


def test_analysis_logic_with_filters(setup_dummy_files):
    usage_files = setup_dummy_files["usage_files"]
    target_file = setup_dummy_files["target_file"]

    filters = {
        'companies': ['CompanyA']  # Filter by CompanyA
    }

    runner = AnalysisRunner(Mock(), Mock())
    runner.update_status = Mock() # Mock the update_status method

    results = runner.execute_analysis(usage_files, target_file, filters)

    assert 'error' not in results
    assert results['status'] == 'success'
    assert len(results['deep_dive_data']['utilized_metrics_df']) > 0

    metrics_df = results['deep_dive_data']['utilized_metrics_df']
    assert 'Tool Expansion Rate' in metrics_df.columns
    assert 'Engagement Score' in metrics_df.columns

    # Check if excel_bytes are generated
    assert 'excel_bytes' in results['reports']
    assert results['reports']['excel_bytes'] is not None

def test_usage_complexity_over_time(setup_dummy_files):
    usage_files = setup_dummy_files["usage_files"]
    target_file = setup_dummy_files["target_file"]

    filters = {} # No filters for this test, so all users are target

    runner = AnalysisRunner(Mock(), Mock())
    runner.update_status = Mock() # Mock the update_status method
    
    # Run execute_analysis to populate full_usage_data and utilized_metrics_df
    results = runner.execute_analysis(usage_files, target_file, filters)
    assert 'error' not in results

    # Now call the method to test
    utilized_emails = runner.utilized_metrics_df['Email'].tolist()
    trend_df = runner.calculate_usage_complexity_over_time(utilized_emails)

    assert not trend_df.empty
    assert 'Report Refresh Period' in trend_df.columns
    assert 'Global Usage Complexity' in trend_df.columns
    assert 'Target Usage Complexity' in trend_df.columns
    assert len(trend_df) == 2 # Expecting data for Jan and Feb 2024
    
    # Check some expected values
    # In DUMMY_USAGE_DATA, for Jan 2024:
    # user1: Copilot (1 tool)
    # user2: Copilot, Copilot Chat (2 tools)
    # user3: (0 tools)
    # Global complexity for Jan: 1+2+0 = 3
    # Target complexity will be the same as global since no filter applied
    assert trend_df[trend_df['Report Refresh Period'] == '2024-01']['Global Usage Complexity'].iloc[0] == pytest.approx(1.0)
    assert trend_df[trend_df['Report Refresh Period'] == '2024-01']['Target Usage Complexity'].iloc[0] == pytest.approx(1.0)

    # For Feb 2024:
    # user1: Copilot Chat (1 tool)
    # user2: Copilot (1 tool)
    # user3: (0 tools)
    # Global complexity for Feb: (1+1+0)/3 = 0.666...
    assert trend_df[trend_df['Report Refresh Period'] == '2024-02']['Global Usage Complexity'].iloc[0] == pytest.approx(2/3)
    assert trend_df[trend_df['Report Refresh Period'] == '2024-02']['Target Usage Complexity'].iloc[0] == pytest.approx(2/3)
