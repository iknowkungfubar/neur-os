"""Tests for Phase 5: E2EE sync relay and admin night mode."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

tmp = tempfile.mkdtemp()

from fastapi.testclient import TestClient
import backend.main as m
from conftest import unwrap
from backend.store import SqliteStore

store = SqliteStore(m.Path(tmp) / 'neur-os.db')
store.init_schema()
store._seed_defaults()
m.set_store(store)

c = TestClient(m.app)


def test_sync_upload():
    r = c.post('/api/sync/upload', json={
        'device_id': 'device-a', 'collection': 'tasks',
        'encrypted_blob': 'dGhpcyBpcyBlbmNyeXB0ZWQ=', 'version': 1
    })
    assert unwrap(r)['status'] == 'ok'


def test_sync_download():
    r = c.get('/api/sync/download?device_id=device-a&collection=tasks')
    data = unwrap(r)
    assert len(data['blobs']) >= 1


def test_sync_download_empty():
    r = c.get('/api/sync/download?device_id=nonexistent&collection=tasks')
    assert len(unwrap(r)['blobs']) == 0


def test_admin_create_room():
    r = c.post('/api/admin-night/rooms')
    assert 'room_id' in unwrap(r)


def test_admin_list_rooms():
    r = c.get('/api/admin-night/rooms')
    assert 'rooms' in unwrap(r)
