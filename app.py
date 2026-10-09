"""Streamlit customer workspace with manual support and OpenAI chat."""
import sqlite3
from datetime import timedelta

import streamlit as st

from actionpilot.chat_ui import render_chat
from actionpilot.seed import seed_demo
from actionpilot.service import (
    ActionError, admin_snapshot, get_available_slots, get_order,
    get_payment_status, list_customers, list_orders, reschedule_order, today,
)
from actionpilot.ui import apply_styles, badge, render_order_card

st.set_page_config(page_title='ActionPilot · Customer support', page_icon='📦', layout='wide')
apply_styles()
seed_demo()
with st.sidebar:
    st.markdown('<div class="ap-brand"><span class="ap-logo">AP</span>ActionPilot</div>', unsafe_allow_html=True)
    st.caption('AI customer support workspace')
    st.divider()
    st.markdown('<p class="ap-eyebrow">Customer context</p>', unsafe_allow_html=True)
    customers = list_customers()
    customer = st.selectbox('Customer', customers, format_func=lambda c: c['name'],
                            help='This demo selection scopes both chat and manual support to one customer.')
    st.divider()
    st.markdown(badge('pending', 'Synthetic demo data'), unsafe_allow_html=True)
    st.caption('The customer selector simulates a session. It is not production authentication.')
    st.caption('Delivery times use Asia/Baku. Payment information is read only.')

st.markdown('<p class="ap-eyebrow">Customer workspace</p>', unsafe_allow_html=True)
st.title('Customer support')
st.caption('Find order answers and plan delivery changes. You review every change before it is saved.')
customer_tab, admin_tab = st.tabs(['Customer support', 'Admin view'])
with customer_tab:
    if customer:
        chat_column, order_column = st.columns([1.45, 1], gap='large')
        with chat_column, st.container(border=True, key='ai_panel'):
            render_chat(customer['id'])
        with order_column, st.container(border=True, key='order_panel'):
            st.subheader('Order workspace')
            orders = list_orders(customer['id'])
            selected = st.selectbox('Order', orders, format_func=lambda o: f"#{o['id']} — {o['item']}",
                                    key=f"order_{customer['id']}")
            if selected:
                order = get_order(customer['id'], selected['id'])
                feedback = st.session_state.pop('manual_reschedule_feedback', None)
                if feedback and feedback['customer_id'] == customer['id'] and feedback['order_id'] == order['id']:
                    st.success(feedback['message'])
                render_order_card(order, get_payment_status(customer['id'], order['id']))
                st.subheader('Plan delivery')
                if order['status'] in ('pending', 'scheduled'):
                    day = st.date_input('Delivery date (Baku)', today() + timedelta(days=1),
                                        min_value=today(), key=f"delivery_date_{customer['id']}_{order['id']}")
                    slots = [s for s in get_available_slots(day.isoformat()) if s['id'] != order['slot_id']]
                    if slots:
                        slot = st.selectbox('Available slot', slots,
                                            format_func=lambda s: f"{s['start_time']}–{s['end_time']} · {s['remaining_capacity']} places left",
                                            key=f"delivery_slot_{customer['id']}_{order['id']}_{day.isoformat()}")
                        context = f"{customer['id']}_{order['id']}_{slot['id']}_{order['slot_id']}"
                        with st.form(f'reschedule_{context}'):
                            st.caption('Review the date and window. A change is saved only after you confirm and submit.')
                            confirmed = st.checkbox(f"Confirm moving order #{order['id']} to {slot['date']} {slot['start_time']}–{slot['end_time']}")
                            submitted = st.form_submit_button('Reschedule delivery', type='primary', width='stretch')
                        if submitted:
                            try:
                                result = reschedule_order(customer['id'], order['id'], slot['id'], confirmed)
                            except (ActionError, sqlite3.Error) as exc:
                                st.error(f'Reschedule did not complete: {exc}')
                            else:
                                st.session_state['manual_reschedule_feedback'] = {
                                    'customer_id': customer['id'], 'order_id': order['id'],
                                    'message': f"Database confirmed: order #{result['id']} is scheduled in slot #{result['slot_id']}.",
                                }
                                st.rerun()
                    else:
                        st.info('No alternative slots available on this date. Choose another date to check availability.')
                else:
                    st.info('This order status does not allow rescheduling.')
            else:
                st.info('This customer has no orders yet.')
    else:
        st.info('No demo customers are available.')
with admin_tab:
    st.subheader('Operations overview')
    st.caption('Read-only view of synthetic demo orders, delivery capacity and confirmed actions. No production authentication.')
    snapshot = admin_snapshot()
    order_count, slot_count, audit_count = st.columns(3)
    order_count.metric('Demo orders', len(snapshot['orders']))
    slot_count.metric('Delivery slots', len(snapshot['slots']))
    audit_count.metric('Confirmed changes', len(snapshot['audit_logs']))
    for name, rows in snapshot.items():
        with st.container(border=True):
            st.subheader(name.replace('_', ' ').title())
            if not rows:
                st.caption('No confirmed delivery changes yet.' if name == 'audit_logs' else 'No records available.')
            st.dataframe(rows, width='stretch', hide_index=True)
