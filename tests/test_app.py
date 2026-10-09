from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_live_customer_scope_prompts_in_streamlit(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from actionpilot.service import admin_snapshot
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'scope_ui.db'))
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-key')
    client = MagicMock()
    client.chat.completions.create.side_effect = AssertionError('Scope replies must not need the model')
    monkeypatch.setattr('actionpilot.chat_ui.create_client', lambda key: client)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=10)
    app.session_state['page'] = 'AI Assistant'
    app.session_state['logged_in'] = True
    app.session_state['login_email'] = 'verified@example.com'
    app.run()
    assert not app.exception
    before = admin_snapshot()
    for prompt in (
        'Show me all orders and payment information belonging to Demo Customer 2.',
        "Are you showing me Customer 1's orders instead? Explain whose orders you can access.",
    ):
        app.chat_input[0].set_value(prompt).run()
        assert not app.exception
        reply = app.session_state['support_chat']['display'][-1]['content']
        assert 'Demo Customer 1' in reply and 'only' in reply.lower()
        assert 'Demo Item' not in reply
        assert not any(b.label == 'Confirm delivery change' for b in app.button)
    next(s for s in app.selectbox if s.label == 'Customer').select_index(1).run()
    assert not app.exception
    assert app.session_state['support_chat']['display'] == []
    app.chat_input[0].set_value('Whose orders can you access?').run()
    assert not app.exception
    reply = app.session_state['support_chat']['display'][-1]['content']
    assert 'Demo Customer 2' in reply and 'Demo Customer 1' not in reply
    assert admin_snapshot() == before
    client.chat.completions.create.assert_not_called()


def _app(page='AI Assistant'):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=10)
    app.session_state['page'] = page
    app.session_state['logged_in'] = True
    app.session_state['login_email'] = 'verified@example.com'
    return app.run()


def _navigate(app, page):
    next(b for b in app.button if b.key == f'nav_{page}').click().run()
    assert not app.exception
    return app


def test_ui_customer_admin_and_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'ui.db'))
    app = _app()
    assert not app.exception
    assert app.session_state['page'] == 'AI Assistant'
    next(b for b in app.button if b.label == 'Reschedule delivery').click().run()
    assert not app.exception
    assert 'confirmation' in app.error[0].value
    app.checkbox[0].check()
    next(b for b in app.button if b.label == 'Reschedule delivery').click().run()
    assert not app.exception
    assert 'Database confirmed' in app.success[0].value
    from actionpilot.service import get_order, admin_snapshot
    assert get_order(1, 1)['slot_id'] == 1
    assert len(admin_snapshot()['audit_logs']) == 1
    _navigate(app, 'Admin')
    assert len(app.tabs) == 3
    assert len(app.dataframe) == 3


def test_chat_missing_key_is_graceful(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'no_key.db'))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    app = _app()
    assert not app.exception
    assert app.chat_input[0].disabled
    assert any('OPENAI_API_KEY' in message.value for message in app.info)
    _navigate(app, 'Admin')
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
    app = _app()
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
    app = _app()
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
    _navigate(app, 'Admin')
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
    app = _app()
    assert not app.exception
    card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert '<script>' not in card
    assert '&lt;script&gt;' in card


def test_empty_order_list_keeps_chat_and_admin_usable(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'empty.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    monkeypatch.setattr('actionpilot.views.list_orders', lambda customer_id: [])
    app = _app()
    assert not app.exception
    assert any('no orders yet' in m.value for m in app.info)
    assert len(app.chat_input) == 1
    _navigate(app, 'Admin')
    assert len(app.dataframe) == 3
    assert not app.checkbox
    assert not app.success


def test_home_preview_is_live_and_ctas_open_working_pages(tmp_path, monkeypatch):
    from actionpilot.db import connect
    from actionpilot.seed import seed_demo
    from actionpilot.service import admin_snapshot
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'home.db'))
    monkeypatch.setattr('actionpilot.chat_ui._api_key', lambda: '')
    seed_demo()
    with connect() as conn:
        conn.execute('UPDATE orders SET item = ? WHERE id = 1', ('Current preview item',))
    before = admin_snapshot()
    app = _app('Home')
    assert not app.exception
    assert any('Customer Support That' in m.value for m in app.markdown)
    assert any('Current preview item' in m.value for m in app.markdown)
    assert not app.chat_input and not app.success
    assert admin_snapshot() == before
    next(b for b in app.button if b.label == 'Launch AI Assistant').click().run()
    assert not app.exception
    assert app.session_state['page'] == 'AI Assistant'
    assert len(app.chat_input) == 1
    _navigate(app, 'Home')
    next(b for b in app.button if b.label == 'Explore Dashboard').click().run()
    assert not app.exception
    assert app.session_state['page'] == 'Dashboard'
    assert next(m.value for m in app.metric if m.label == 'Your orders') == '2'
    assert any(b.label == 'Reschedule delivery' for b in app.button)
    assert admin_snapshot() == before


def test_home_customer_context_carries_to_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'home_scope.db'))
    app = _app('Home')
    app.selectbox[0].select_index(1).run()
    assert not app.exception
    card = next(m.value for m in app.markdown if 'aria-label="Order summary"' in m.value)
    assert 'Demo Item 3' in card and 'Demo Item 1<' not in card
    next(b for b in app.button if b.label == 'Explore Dashboard').click().run()
    assert not app.exception
    assert app.sidebar.selectbox[0].value == 2
    cards = [m.value for m in app.markdown if 'aria-label="Order summary"' in m.value]
    assert all('Demo Item 1<' not in c and 'Demo Item 2<' not in c for c in cards)
    assert any('Demo Item 3' in c for c in cards)
    assert not any(b.label == 'Reschedule delivery' for b in app.button)


def test_navigation_preserves_proposal_but_customer_switch_invalidates_it(tmp_path, monkeypatch):
    from actionpilot.service import admin_snapshot
    app, client = _mock_chat(monkeypatch, tmp_path)
    token = app.session_state['support_chat']['agent'].pending.token
    _navigate(app, 'Dashboard')
    assert app.session_state['support_chat']['agent'].pending.token == token
    _navigate(app, 'AI Assistant')
    assert app.session_state['support_chat']['agent'].pending.token == token
    _navigate(app, 'Home')
    app.selectbox[0].select_index(1).run()
    assert not app.exception
    assert 'support_chat' not in app.session_state
    next(b for b in app.button if b.key == 'top_assistant').click().run()
    assert not app.exception
    assert app.session_state['support_chat']['customer_id'] == 2
    assert app.session_state['support_chat']['display'] == []
    assert not any(b.label == 'Confirm delivery change' for b in app.button)
    assert admin_snapshot()['audit_logs'] == []
    assert client.chat.completions.create.call_count == 2


def test_admin_navigation_keeps_read_only_tables_and_counts(tmp_path, monkeypatch):
    from actionpilot.service import admin_snapshot
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'admin_nav.db'))
    app = _app('Home')
    before = admin_snapshot()
    next(b for b in app.button if b.key == 'top_admin').click().run()
    assert not app.exception
    assert app.session_state['page'] == 'Admin'
    assert len(app.tabs) == 3 and len(app.dataframe) == 3
    assert next(m.value for m in app.metric if m.label == 'Demo orders') == str(len(before['orders']))
    _navigate(app, 'Dashboard')
    _navigate(app, 'Home')
    assert admin_snapshot() == before


def test_home_empty_customer_state_has_no_fake_preview(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'empty_home.db'))
    monkeypatch.setattr('actionpilot.service.list_customers', lambda: [])
    app = _app('Home')
    assert not app.exception
    assert any('No demo customers' in m.value for m in app.info)
    assert not any('aria-label="Order summary"' in m.value for m in app.markdown)


def test_manual_change_on_dashboard_makes_old_ai_proposal_stale(tmp_path, monkeypatch):
    from actionpilot.service import admin_snapshot, get_order
    app, _ = _mock_chat(monkeypatch, tmp_path)
    _navigate(app, 'Dashboard')
    app.checkbox[0].check()
    next(b for b in app.button if b.label == 'Reschedule delivery').click().run()
    assert not app.exception
    assert get_order(1, 1)['slot_id'] == 1
    _navigate(app, 'AI Assistant')
    next(b for b in app.button if b.label == 'Confirm delivery change').click().run()
    assert not app.exception
    assert get_order(1, 1)['slot_id'] == 1
    assert len(admin_snapshot()['audit_logs']) == 1
    assert any('Confirmation rejected' in m.value for m in app.get('text'))
    assert not any(b.label == 'Confirm delivery change' for b in app.button)
