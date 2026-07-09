"""Test that domain/ has zero framework imports. Ponytail: smallest test that satisfies AC 1.5."""
import sys
# Clear cached modules to force fresh import
for mod in list(sys.modules.keys()):
    if 'backend.domain' in mod:
        del sys.modules[mod]

# import domain entities — no fastapi, no sqlite3
from backend.domain.entities import EnergyBattery, BrainDump
from backend.domain.usecases import energy_envelope, detect_boom_bust

def test_no_framework_imports():
    """Verify domain modules have zero framework dependencies from their own code."""
    import backend.domain.entities as e
    import backend.domain.usecases as u
    # Check that the code we wrote doesn't import restricted modules
    import ast
    for mod_name, mod in [("entities", e), ("usecases", u)]:
        src = open(str(mod.__file__)).read()
        tree = ast.parse(src)
        imports = {node.names[0].name.split('.')[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))}
        restricted = {'fastapi', 'sqlite3', 'httpx', 'pydantic'}
        assert not (imports & restricted), f'{mod_name} imports restricted: {imports & restricted}'

def test_energy_battery():
    b = EnergyBattery(80)
    assert b.percentage == 80
    assert b.traffic_light == 'green'
    b.drain(70)
    assert b.percentage == 10
    assert b.traffic_light == 'red'

def test_envelope():
    r = energy_envelope(40, 8, [])
    assert 'status' in r

def test_boom_bust():
    r = detect_boom_bust([80, 90, 85, 20, 15, 10])
    assert r['pattern'] == 'boom-bust'
    assert r['confidence'] > 0.7

def test_brain_dump():
    bd = BrainDump("clean kitchen, call mom")
    bd.add_task("clean kitchen")
    bd.add_note("call mom")
    assert len(bd.tasks) == 1
    assert len(bd.notes) == 1
