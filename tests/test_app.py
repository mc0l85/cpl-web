import pytest
from app import app
from config import TARGET_PRESETS
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_no_target(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"window.preSelectedManagers = [];" in rv.data

def test_index_valid_target(client):
    rv = client.get('/?target=qsc')
    assert rv.status_code == 200
    assert b'window.preSelectedManagers' in rv.data
    html = rv.data.decode('utf-8')
    start_managers = html.find('window.preSelectedManagers = ') + len('window.preSelectedManagers = ')
    end_managers = html.find(';', start_managers)
    pre_selected_managers = json.loads(html[start_managers:end_managers])
    assert pre_selected_managers == TARGET_PRESETS['qsc']['managers']

def test_index_invalid_target(client):
    rv = client.get('/?target=invalid')
    assert rv.status_code == 200
    assert b"window.preSelectedManagers = [];" in rv.data
