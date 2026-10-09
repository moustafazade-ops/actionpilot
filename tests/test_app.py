from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_ui_customer_admin_and_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'ui.db'))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert len(app.tabs) == 2
    assert len(app.dataframe) == 3
    app.button[0].click().run()
    assert not app.exception
    assert 'confirmation' in app.error[0].value
    app.checkbox[0].check()
    app.button[0].click().run()
    assert not app.exception
    assert 'Database confirmed' in app.success[0].value
    from actionpilot.service import get_order, admin_snapshot
    assert get_order(1, 1)['slot_id'] == 1
    assert len(admin_snapshot()['audit_logs']) == 1
