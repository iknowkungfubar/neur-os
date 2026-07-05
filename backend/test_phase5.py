"""Phase 5: E2EE sync relay + admin night WebSocket tests."""
import sys; sys.path.insert(0, '.')
import tempfile, os; tmp = tempfile.mkdtemp()
os.environ['LM_STUDIO_URL'] = 'http://localhost:9999/v1'
import backend.main as m; m.DB_PATH = m.Path(tmp)/'neur-os.db'; m.DATA_DIR = m.Path(tmp); m.BACKUP_DIR = m.Path(tmp)/'backups'; m.BACKUP_DIR.mkdir(); m.init_db()
from fastapi.testclient import TestClient
c = TestClient(m.app)

def test_sync_upload():
    r = c.post('/api/sync/upload', json={
        'device_id': 'device-a', 'collection': 'tasks',
        'encrypted_blob': 'dGhpcyBpcyBlbmNyeXB0ZWQ=', 'version': 1
    })
    assert r.json()['status'] == 'ok'

def test_sync_download():
    r = c.get('/api/sync/download?device_id=device-a&collection=tasks')
    data = r.json()
    assert len(data['blobs']) >= 1
    assert data['blobs'][0]['encrypted_blob'] == 'dGhpcyBpcyBlbmNyeXB0ZWQ='

def test_sync_download_empty():
    r = c.get('/api/sync/download?device_id=nonexistent&collection=tasks')
    assert len(r.json()['blobs']) == 0

def test_admin_create_room():
    r = c.post('/api/admin-night/rooms')
    data = r.json()
    assert 'room_id' in data
    assert len(data['room_id']) == 8

def test_admin_list_rooms():
    r = c.get('/api/admin-night/rooms')
    assert 'rooms' in r.json()
