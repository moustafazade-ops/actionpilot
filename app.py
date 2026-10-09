"""Synthetic support demo with manual operations and OpenAI tool-based chat."""
import sqlite3
from datetime import timedelta
import streamlit as st
from actionpilot.seed import seed_demo
from actionpilot.chat_ui import render_chat
from actionpilot.service import (
    ActionError, admin_snapshot, get_available_slots, get_order,
    get_payment_status, list_customers, list_orders, reschedule_order, today,
)

st.set_page_config(page_title='ActionPilot', page_icon='📦', layout='wide')
seed_demo()
st.title('📦 ActionPilot')
st.caption('Order support, payment updates and delivery planning in one place.')
st.caption('Synthetic demo data • customer selector is not production authentication • delivery times are in Baku')
customer_tab, admin_tab = st.tabs(['Customer support', 'Admin view'])
with customer_tab:
    customers = list_customers()
    customer = st.selectbox('Customer', customers, format_func=lambda c: c['name'],
                            help='Choose the demo customer whose orders you want to manage.')
    if customer:
        orders = list_orders(customer['id'])
        manual_column, chat_column = st.columns([1, 1], gap='large')
        with manual_column, st.container(border=True):
            st.subheader('Your orders')
            selected = st.selectbox('Order', orders,
                                    format_func=lambda o: f"#{o['id']} — {o['item']}",
                                    key=f"order_{customer['id']}")
            if selected:
                order = get_order(customer['id'], selected['id'])
                feedback = st.session_state.pop('manual_reschedule_feedback', None)
                if feedback and feedback['customer_id'] == customer['id'] and feedback['order_id'] == order['id']:
                    st.success(feedback['message'])
                st.subheader(f"Order #{order['id']}")
                st.text(order['item'])
                status_column, payment_column = st.columns(2)
                status_column.metric('Order status', order['status'].replace('_', ' ').title())
                payment_column.metric('Payment status', get_payment_status(customer['id'], order['id']).replace('_', ' ').title())
                st.caption(f"Current delivery slot: #{order['slot_id']}" if order['slot_id'] is not None
                           else 'No delivery slot assigned yet.')
                with st.expander('Order details'):
                    st.json(order)
                st.divider()
                st.subheader('Plan your delivery')
                if order['status'] in ('pending', 'scheduled'):
                    day = st.date_input('Delivery date (Baku)', today() + timedelta(days=1),
                                        min_value=today(), key=f"delivery_date_{customer['id']}_{order['id']}")
                    slots = [s for s in get_available_slots(day.isoformat()) if s['id'] != order['slot_id']]
                    if slots:
                        slot = st.selectbox('Available slot', slots,
                                            format_func=lambda s: f"{s['start_time']}–{s['end_time']} ({s['remaining_capacity']} places)",
                                            key=f"delivery_slot_{customer['id']}_{order['id']}_{day.isoformat()}")
                        st.caption('Review the date and time, then check the confirmation box to approve the change.')
                        context = f"{customer['id']}_{order['id']}_{slot['id']}_{order['slot_id']}"
                        with st.form(f'reschedule_{context}'):
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
                    st.info(f"This order is {order['status']}. This order status does not allow rescheduling.")
            else:
                st.info('This customer has no orders yet.')
        with chat_column, st.container(border=True):
            render_chat(customer['id'])
    else:
        st.info('No demo customers are available.')
with admin_tab:
    st.subheader('Operations overview')
    st.caption('Read-only demo admin view; no production authentication.')
    snapshot = admin_snapshot()
    orders_column, slots_column, audit_column = st.columns(3)
    orders_column.metric('Orders', len(snapshot['orders']))
    slots_column.metric('Delivery slots', len(snapshot['slots']))
    audit_column.metric('Confirmed changes', len(snapshot['audit_logs']))
    for name, rows in snapshot.items():
        with st.container(border=True):
            st.subheader(name.replace('_', ' ').title())
            if not rows:
                st.caption('No confirmed delivery changes yet.' if name == 'audit_logs' else 'No records available.')
            st.dataframe(rows, width='stretch', hide_index=True)
