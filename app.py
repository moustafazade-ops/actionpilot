"""Minimal synthetic customer support demo. No authentication or LLM calls."""
import sqlite3
from datetime import timedelta
import streamlit as st
from actionpilot.seed import seed_demo
from actionpilot.service import (
    ActionError, admin_snapshot, get_available_slots, get_order,
    get_payment_status, list_customers, list_orders, reschedule_order, today,
)

st.set_page_config(page_title='ActionPilot', page_icon='📦')
seed_demo()
st.title('ActionPilot')
st.caption('Milestone 1 • synthetic demo data • customer selector is not authentication')
customer_tab, admin_tab = st.tabs(['Customer support', 'Admin view'])
with customer_tab:
    customers = list_customers()
    customer = st.selectbox('Customer', customers, format_func=lambda c: c['name'])
    orders = list_orders(customer['id'])
    selected = st.selectbox('Order', orders, format_func=lambda o: f"#{o['id']} — {o['item']}", key=f"order_{customer['id']}")
    if selected:
        order = get_order(customer['id'], selected['id'])
        st.json(order)
        st.write('Payment status:', get_payment_status(customer['id'], order['id']))
        if order['status'] in ('pending', 'scheduled'):
            day = st.date_input('Delivery date (Baku)', today() + timedelta(days=1), min_value=today())
            slots = [s for s in get_available_slots(day.isoformat()) if s['id'] != order['slot_id']]
            if slots:
                slot = st.selectbox('Available slot', slots, format_func=lambda s: f"{s['start_time']}–{s['end_time']} ({s['remaining_capacity']} places)")
                context = f"{customer['id']}_{order['id']}_{slot['id']}_{order['slot_id']}"
                with st.form(f'reschedule_{context}'):
                    confirmed = st.checkbox(f"Confirm moving order #{order['id']} to {slot['date']} {slot['start_time']}–{slot['end_time']}")
                    submitted = st.form_submit_button('Reschedule delivery')
                if submitted:
                    try:
                        result = reschedule_order(customer['id'], order['id'], slot['id'], confirmed)
                    except (ActionError, sqlite3.Error) as exc:
                        st.error(f'Reschedule did not complete: {exc}')
                    else:
                        st.success(f"Database confirmed: order #{result['id']} is scheduled in slot #{result['slot_id']}.")
                        st.json(result)
            else:
                st.info('No alternative slots available on this date.')
        else:
            st.info('This order status does not allow rescheduling.')
with admin_tab:
    st.caption('Read-only demo admin view; no authentication in milestone 1.')
    for name, rows in admin_snapshot().items():
        st.subheader(name.replace('_', ' ').title())
        st.dataframe(rows, width='stretch')
