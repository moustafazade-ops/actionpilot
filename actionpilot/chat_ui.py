"""Streamlit integration; binds agent state to the application customer context."""
import os
import sqlite3

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from actionpilot.agent import AgentError, SupportAgent, create_client
from actionpilot.service import ActionError
from actionpilot.ui import badge, icon, render_proposal_card


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
    st.caption('Order answers, payment status and delivery planning for the selected demo customer.')
    state = st.session_state.get('support_chat')
    model = os.environ.get('OPENAI_MODEL', '').strip()
    if state is None or state['customer_id'] != customer_id or state['model'] != model:
        # Switching context discards prior transcripts and pending confirmations.
        state = {'customer_id': customer_id, 'model': model, 'agent': None, 'display': []}
        st.session_state['support_chat'] = state
    key = _api_key()
    if not key:
        state['agent'] = None
    elif state['agent'] is None:
        try:
            state['agent'] = SupportAgent(customer_id, create_client(key), model=model or None)
        except AgentError as exc:
            st.error(str(exc))
    agent = state['agent']
    st.markdown(badge('scheduled' if agent else 'pending', 'AI configured' if agent else 'Setup required'),
                unsafe_allow_html=True)
    if state['display'] and state['display'][-1]['role'] == 'assistant':
        latest = state['display'][-1]['content']
        if latest.startswith('Database confirmed:'):
            st.success('Delivery change saved to the database.')
        elif latest.startswith(('Confirmation rejected:', 'Database operation failed.')):
            st.error('The delivery change was not confirmed. Review the message below and prepare a new proposal.')
        elif latest.startswith('Delivery proposal cancelled.'):
            st.info('Proposal cancelled. Your order is unchanged.')
    with st.container(height=260, border=False):
        if not state['display']:
            st.markdown(
                '<div class="ap-welcome"><div class="ap-welcome-icon">' + icon('spark') + '</div>'
                '<h4>How can I help with your order?</h4>'
                '<p>Ask a question below. Here are a few places to start:</p>'
                '<div class="ap-example">Show my orders</div>'
                '<div class="ap-example">Check payment for one of my orders</div>'
                '<div class="ap-example">What delivery slots are available tomorrow?</div></div>',
                unsafe_allow_html=True,
            )
        for message in state['display']:
            with st.chat_message(message['role']):
                st.text(message['content'])
    text = st.chat_input('Ask about an order, payment, or delivery date', disabled=agent is None,
                         key=f'chat_input_{customer_id}')
    st.caption('Chat can propose a delivery change. Only the confirmation button saves it.')
    if not key:
        st.info('Configure OPENAI_API_KEY to enable AI chat. Manual support remains available.')
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
        st.warning('Review your delivery proposal. This change has not been executed.')
        render_proposal_card(proposal.order, slot)
        if st.button('Confirm delivery change', key=f'confirm_{proposal.token}', type='primary', width='stretch'):
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
        if st.button('Cancel proposal', key=f'cancel_{proposal.token}', width='stretch'):
            agent.cancel(proposal.token)
            state['display'].append({'role': 'assistant', 'content': 'Delivery proposal cancelled. No order was changed.'})
            st.rerun()
