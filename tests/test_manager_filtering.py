from unittest.mock import patch
import pytest
import pandas as pd
from unittest.mock import Mock
from analysis_logic import CopilotAnalyzer

@pytest.fixture
def mock_socketio():
    return Mock()

@pytest.fixture
def mock_sid():
    return "test_sid"

@pytest.fixture
def analyzer(mock_socketio, mock_sid):
    return CopilotAnalyzer(mock_socketio, mock_sid)

@pytest.fixture
def dummy_usage_df():
    return pd.DataFrame({
        'User Principal Name': ['user1@example.com', 'user2@example.com', 'user3@example.com', 'user4@example.com'],
        'Report Refresh Date': [pd.to_datetime('2023-01-01')] * 4,
        'Last activity date of ToolA': [pd.to_datetime('2022-12-01')] * 4,
        'Last activity date of ToolB': [pd.to_datetime('2022-12-15')] * 4,
    })

@pytest.fixture
def dummy_target_df():
    # Create a DataFrame with the exact column names expected by the code
    return pd.DataFrame({
        'User Principal Name': ['user1@example.com', 'user2@example.com', 'user3@example.com', 'user4@example.com'],
        'Company': ['CompanyA', 'CompanyB', 'CompanyA', 'CompanyC'],
        'Department': ['DeptX', 'DeptY', 'DeptX', 'DeptZ'],
        'City': ['City1', 'City2', 'City1', 'City3'],
        'ManagerLine': [
            'ManagerA -> ManagerB -> ManagerC',
            'ManagerD -> ManagerE',
            'ManagerA -> ManagerF',
            'ManagerG'
        ]
    })

def test_manager_filtering_single_manager(analyzer, dummy_usage_df, dummy_target_df):
    usage_file_paths = {'usage1.csv': 'path/to/usage1.csv'}
    
    # Create a custom side effect function to ensure the correct DataFrame is returned
    def read_csv_side_effect(path, *args, **kwargs):
        if path == 'path/to/target.csv':
            return dummy_target_df
        else:
            return dummy_usage_df
    
    with (
        patch('pandas.read_csv', side_effect=read_csv_side_effect),
        patch('pandas.concat', return_value=dummy_usage_df),
        patch.object(analyzer, 'calculate_usage_complexity_over_time', return_value=pd.DataFrame(columns=['Month', 'Global Usage Complexity', 'Target Usage Complexity', 'Report Refresh Period']))
    ):
        filters = {'managers': ['ManagerB']}
        result = analyzer.execute_analysis(
            usage_file_paths=usage_file_paths,
            target_user_path='path/to/target.csv',
            filters=filters
        )
        
        assert 'error' not in result
        assert len(analyzer.utilized_metrics_df) == 1
        assert 'user1@example.com' in analyzer.utilized_metrics_df['Email'].tolist()

def test_manager_filtering_multiple_managers(analyzer, dummy_usage_df, dummy_target_df):
    usage_file_paths = {'usage1.csv': 'path/to/usage1.csv'}
    
    # Create a custom side effect function to ensure the correct DataFrame is returned
    def read_csv_side_effect(path, *args, **kwargs):
        if path == 'path/to/target.csv':
            return dummy_target_df
        else:
            return dummy_usage_df
    
    with (
        patch('pandas.read_csv', side_effect=read_csv_side_effect),
        patch('pandas.concat', return_value=dummy_usage_df),
        patch.object(analyzer, 'calculate_usage_complexity_over_time', return_value=pd.DataFrame(columns=['Month', 'Global Usage Complexity', 'Target Usage Complexity', 'Report Refresh Period']))
    ):
        filters = {'managers': ['ManagerE', 'ManagerF']}
        result = analyzer.execute_analysis(
            usage_file_paths=usage_file_paths,
            target_user_path='path/to/target.csv',
            filters=filters
        )
        
        assert 'error' not in result
        assert len(analyzer.utilized_metrics_df) == 2
        assert 'user2@example.com' in analyzer.utilized_metrics_df['Email'].tolist()
        assert 'user3@example.com' in analyzer.utilized_metrics_df['Email'].tolist()

def test_manager_filtering_no_match(analyzer, dummy_usage_df, dummy_target_df):
    usage_file_paths = {'usage1.csv': 'path/to/usage1.csv'}
    
    # Create a custom side effect function to ensure the correct DataFrame is returned
    def read_csv_side_effect(path, *args, **kwargs):
        if path == 'path/to/target.csv':
            return dummy_target_df
        else:
            return dummy_usage_df
    
    with (
        patch('pandas.read_csv', side_effect=read_csv_side_effect),
        patch('pandas.concat', return_value=dummy_usage_df),
        patch.object(analyzer, 'calculate_usage_complexity_over_time', return_value=pd.DataFrame(columns=['Month', 'Global Usage Complexity', 'Target Usage Complexity', 'Report Refresh Period']))
    ):
        filters = {'managers': ['NonExistentManager']}
        result = analyzer.execute_analysis(
            usage_file_paths=usage_file_paths,
            target_user_path='path/to/target.csv',
            filters=filters
        )
        
        assert 'error' in result
        assert "No matching users found to analyze." in result['error']

def test_manager_filtering_empty_managers_list(analyzer, dummy_usage_df, dummy_target_df):
    usage_file_paths = {'usage1.csv': 'path/to/usage1.csv'}
    
    # Create a custom side effect function to ensure the correct DataFrame is returned
    def read_csv_side_effect(path, *args, **kwargs):
        if path == 'path/to/target.csv':
            return dummy_target_df
        else:
            return dummy_usage_df
    
    with (
        patch('pandas.read_csv', side_effect=read_csv_side_effect),
        patch('pandas.concat', return_value=dummy_usage_df),
        patch.object(analyzer, 'calculate_usage_complexity_over_time', return_value=pd.DataFrame(columns=['Month', 'Global Usage Complexity', 'Target Usage Complexity', 'Report Refresh Period']))
    ):
        filters = {'managers': []}
        result = analyzer.execute_analysis(
            usage_file_paths=usage_file_paths,
            target_user_path='path/to/target.csv',
            filters=filters
        )
        
        assert 'error' not in result
        assert len(analyzer.utilized_metrics_df) == len(dummy_usage_df)

def test_manager_filtering_no_manager_filter_key(analyzer, dummy_usage_df, dummy_target_df):
    usage_file_paths = {'usage1.csv': 'path/to/usage1.csv'}
    
    # Create a custom side effect function to ensure the correct DataFrame is returned
    def read_csv_side_effect(path, *args, **kwargs):
        if path == 'path/to/target.csv':
            return dummy_target_df
        else:
            return dummy_usage_df
    
    with (
        patch('pandas.read_csv', side_effect=read_csv_side_effect),
        patch('pandas.concat', return_value=dummy_usage_df),
        patch.object(analyzer, 'calculate_usage_complexity_over_time', return_value=pd.DataFrame(columns=['Month', 'Global Usage Complexity', 'Target Usage Complexity', 'Report Refresh Period']))
    ):
        filters = {'companies': ['CompanyA']}
        result = analyzer.execute_analysis(
            usage_file_paths=usage_file_paths,
            target_user_path='path/to/target.csv',
            filters=filters
        )
        
        assert 'error' not in result
        assert len(analyzer.utilized_metrics_df) == 2