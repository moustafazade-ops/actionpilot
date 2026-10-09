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


def test_chat_missing_key_is_graceful(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'no_key.db'))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert app.chat_input[0].disabled
    assert any('OPENAI_API_KEY' in message.value for message in app.info)
    assert len(app.dataframe) == 3  # existing admin preserved


def _mock_chat(monkeypatch, tmp_path):
    import json
    from unittest.mock import MagicMock
    from datetime import timedelta
    from openai.types.chat import ChatCompletion
    from actionpilot.service import today
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'chat.db'))
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-key')
    client = MagicMock()
    proposal = ChatCompletion.model_validate({
        'id': 'mock', 'created': 0, 'model': 'mock', 'object': 'chat.completion',
        'choices': [{'index': 0, 'finish_reason': 'tool_calls', 'message': {
            'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': 'call', 'type': 'function', 'function': {
                    'name': 'propose_reschedule', 'arguments': json.dumps({
                        'order_id': 1, 'slot_id': 5,
                        'date': (today() + timedelta(days=2)).isoformat(),
                    }),
                },
            }],
        }}],
    })
    final = ChatCompletion.model_validate({
        'id': 'mock', 'created': 0, 'model': 'mock', 'object': 'chat.completion',
        'choices': [{'index': 0, 'finish_reason': 'stop',
                     'message': {'role': 'assistant', 'content': 'A proposal is ready.'}}],
    })
    client.chat.completions.create.side_effect = [proposal, final]
    monkeypatch.setattr('actionpilot.chat_ui.create_client', lambda key: client)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.chat_input[0].set_value('Reschedule order 1 to the day after tomorrow').run()
    assert not app.exception
    return app, client


def test_chat_confirm_button_commits_once(tmp_path, monkeypatch):
    from actionpilot.service import get_order, admin_snapshot
    app, client = _mock_chat(monkeypatch, tmp_path)
    assert get_order(1, 1)['slot_id'] is None
    button = next(b for b in app.button if b.label == 'Confirm delivery change')
    button.click().run()
    assert not app.exception
    assert get_order(1, 1)['slot_id'] == 5
    assert len(admin_snapshot()['audit_logs']) == 1
    assert not any(b.label == 'Confirm delivery change' for b in app.button)
    assert any('Database confirmed' in m.value for m in app.get('text'))
    assert client.chat.completions.create.call_count == 2  # confirm does not invoke AI


def test_chat_cancel_button_never_writes(tmp_path, monkeypatch):
    from actionpilot.service import get_order, admin_snapshot
    app, _ = _mock_chat(monkeypatch, tmp_path)
    next(b for b in app.button if b.label == 'Cancel proposal').click().run()
    assert not app.exception
    assert get_order(1, 1)['slot_id'] is None
    assert admin_snapshot()['audit_logs'] == []
    assert not any(b.label == 'Confirm delivery change' for b in app.button)


def test_customer_switch_discards_transcript_and_pending(tmp_path, monkeypatch):
    from actionpilot.service import get_order
    app, _ = _mock_chat(monkeypatch, tmp_path)
    app.selectbox[0].select_index(1).run()
    assert not app.exception
    state = app.session_state['support_chat']
    assert state['customer_id'] == 2
    assert state['agent'].customer_id == 2
    assert state['agent'].pending is None
    assert state['display'] == []
    assert get_order(1, 1)['slot_id'] is None
    assert not any(b.label == 'Confirm delivery change' for b in app.button)


def test_chat_execution_rejection_is_displayed(tmp_path, monkeypatch):
    from actionpilot.db import connect
    from actionpilot.service import get_order
    app, _ = _mock_chat(monkeypatch, tmp_path)
    with connect() as conn:
        conn.execute('UPDATE delivery_slots SET enabled = 0 WHERE id = 5')
    next(b for b in app.button if b.label == 'Confirm delivery change').click().run()
    assert not app.exception
    assert get_order(1, 1)['slot_id'] is None
    assert any('Confirmation rejected' in m.value for m in app.get('text'))
    assert not any(b.label == 'Confirm delivery change' for b in app.button)


def test_streamlit_secret_and_environment_precedence(monkeypatch):
    import actionpilot.chat_ui as ui
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(ui.st, 'secrets', {'OPENAI_API_KEY': 'secret-key'})
    assert ui._api_key() == 'secret-key'
    monkeypatch.setenv('OPENAI_API_KEY', 'environment-key')
    assert ui._api_key() == 'environment-key'


def test_manual_summary_refreshes_after_confirmed_change(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'summary.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Order status') == 'Pending'
    assert next(m.value for m in app.metric if m.label == 'Payment status') == 'Paid'
    app.checkbox[0].check()
    next(b for b in app.button if b.label == 'Reschedule delivery').click().run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Order status') == 'Scheduled'
    assert any('Current delivery slot: #1' in c.value for c in app.caption)
    assert next(m.value for m in app.metric if m.label == 'Confirmed changes') == '1'
    assert any('Database confirmed' in m.value for m in app.success)


def test_delivery_date_is_scoped_to_selected_order(tmp_path, monkeypatch):
    from datetime import timedelta
    from actionpilot.service import today
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'date_context.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    chosen_day = today() + timedelta(days=2)
    app.date_input[0].set_value(chosen_day).run()
    app.selectbox[1].select_index(1).run()
    assert not app.exception
    assert app.date_input[0].value == today() + timedelta(days=1)
    app.selectbox[1].select_index(0).run()
    assert not app.exception
    # A restored or reset date must always match the available slot's date.
    selected_slot = app.selectbox[2].value
    assert selected_slot['date'] == app.date_input[0].value.isoformat()
    assert not app.checkbox[0].value


def test_customer_with_no_orders_keeps_chat_available(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'empty_orders.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    monkeypatch.setattr('actionpilot.service.list_orders', lambda customer_id: [])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert any('no orders yet' in m.value for m in app.info)
    assert len(app.chat_input) == 1
    assert not any(b.label == 'Reschedule delivery' for b in app.button)
    assert len(app.dataframe) == 3


def test_blocked_order_shows_status_without_reschedule_controls(tmp_path, monkeypatch):
    from actionpilot.service import admin_snapshot
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'blocked_order.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.selectbox[0].select_index(1).run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Order status') == 'Dispatched'
    assert any('does not allow rescheduling' in m.value for m in app.info)
    assert not app.date_input
    assert not any(b.label == 'Reschedule delivery' for b in app.button)
    assert admin_snapshot()['audit_logs'] == []


def test_no_customers_displays_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'empty_customers.db'))
    monkeypatch.setattr('actionpilot.service.list_customers', lambda: [])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert any('No demo customers' in m.value for m in app.info)
    assert len(app.dataframe) == 3
