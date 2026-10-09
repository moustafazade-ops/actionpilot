"""Streamlit integration; binds agent state to the application customer context."""
import os
import sqlite3

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from actionpilot.agent import AgentError, SupportAgent, create_client
from actionpilot.service import ActionError


def _api_key():
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if key:
        return key
    try:
        value = st.secrets.get('OPENAI_API_KEY', '')
        return value.strip() if isinstance(value, str) else ''
    except (StreamlitSecretNotFoundError, FileNotFoundError):
        return ''


def render_chat(customer_id):
    st.subheader('AI support assistant')
    st.caption('The selected demo customer is your session context. Chat can propose changes; confirmation below executes them.')
    state = st.session_state.get('support_chat')
    model = os.environ.get('OPENAI_MODEL', '').strip()
    if state is None or state['customer_id'] != customer_id or state['model'] != model:
        # Switching context discards prior transcripts and pending confirmations.
        state = {'customer_id': customer_id, 'model': model, 'agent': None, 'display': []}
        st.session_state['support_chat'] = state
    key = _api_key()
    if not key:
        st.info('AI chat needs OPENAI_API_KEY in the environment or Streamlit secrets. Manual support remains available.')
        state['agent'] = None
    elif state['agent'] is None:
        try:
            state['agent'] = SupportAgent(customer_id, create_client(key), model=model or None)
        except AgentError as exc:
            st.error(str(exc))
    agent = state['agent']
    for message in state['display']:
        with st.chat_message(message['role']):
            st.text(message['content'])
    text = st.chat_input('Ask about an order, payment, or delivery date', disabled=agent is None,
                         key=f'chat_input_{customer_id}')
    if text and agent:
        state['display'].append({'role': 'user', 'content': text})
        with st.spinner('Checking your request…'):
            try:
                reply = agent.ask(text)
            except AgentError as exc:
                reply = str(exc)
        state['display'].append({'role': 'assistant', 'content': reply})
        st.rerun()
    if agent and agent.pending:
        proposal = agent.pending
        slot = proposal.slot
        st.warning(f"Review: move order #{proposal.order['id']} to {slot['date']} {slot['start_time']}–{slot['end_time']} (Baku). This has not been executed.")
        if st.button('Confirm delivery change', key=f'confirm_{proposal.token}'):
            try:
                result = agent.confirm(proposal.token)
            except ActionError as exc:
                reply = f'Confirmation rejected: {exc}'
            except sqlite3.Error:
                reply = 'Database operation failed. No delivery change was confirmed. Prepare a new proposal.'
            else:
                reply = f"Database confirmed: order #{result['id']} is scheduled in slot #{result['slot_id']}."
            state['display'].append({'role': 'assistant', 'content': reply})
            st.rerun()
        if st.button('Cancel proposal', key=f'cancel_{proposal.token}'):
            agent.cancel(proposal.token)
            state['display'].append({'role': 'assistant', 'content': 'Delivery proposal cancelled. No order was changed.'})
            st.rerun()
