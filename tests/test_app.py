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
    app.sidebar.selectbox[0].select_index(1).run()
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


def test_order_card_replaces_json_and_refreshes_after_save(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'cards.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert not app.get('json')
    card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert 'Demo Item 1' in card and 'Delivery · Pending' in card
    assert 'Paid' in card and 'Not assigned' in card and '1,250 cents' in card
    assert 'Synthetic demo' in card
    assert not app.success
    app.checkbox[0].check()
    next(b for b in app.button if b.label == 'Reschedule delivery').click().run()
    assert not app.exception
    card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert 'Delivery · Scheduled' in card and 'Slot #1' in card
    assert 'Database confirmed' in app.success[0].value
    assert next(m.value for m in app.metric if m.label == 'Confirmed changes') == '1'
    assert not app.get('json')


def test_proposal_card_is_review_only_until_confirmed(tmp_path, monkeypatch):
    from actionpilot.service import admin_snapshot
    app, _ = _mock_chat(monkeypatch, tmp_path)
    proposal = app.session_state['support_chat']['agent'].pending
    card = next(m.value for m in app.markdown if 'aria-label="Proposed delivery change"' in m.value)
    assert 'Awaiting confirmation' in card and 'Order #1' in card
    assert proposal.slot['date'] in card
    assert f"{proposal.slot['start_time']}–{proposal.slot['end_time']}" in card
    assert 'Baku' in card
    assert not app.success
    assert admin_snapshot()['audit_logs'] == []
    next(b for b in app.button if b.label == 'Confirm delivery change').click().run()
    assert not app.exception
    assert any('saved to the database' in m.value for m in app.success)
    order_card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert 'Slot #5' in order_card and 'Delivery · Scheduled' in order_card


def test_card_escapes_customer_order_content(tmp_path, monkeypatch):
    from actionpilot.db import connect
    from actionpilot.seed import seed_demo
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'escaped.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    seed_demo()
    with connect() as conn:
        conn.execute('UPDATE orders SET item = ? WHERE id = 1', ('<script>alert("test")</script>',))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert '<script>' not in card
    assert '&lt;script&gt;' in card


def test_empty_order_list_keeps_chat_and_admin_usable(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'empty.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    monkeypatch.setattr('actionpilot.service.list_orders', lambda customer_id: [])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.exception
    assert any('no orders yet' in m.value for m in app.info)
    assert len(app.chat_input) == 1
    assert len(app.dataframe) == 3
    assert not app.checkbox
    assert not app.success
