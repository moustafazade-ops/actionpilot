"""Streamlit page views; delegate all reads and actions to existing services."""
import sqlite3
from datetime import timedelta
from html import escape

import streamlit as st

from actionpilot.chat_ui import render_chat
from actionpilot.service import (
    ActionError, admin_snapshot, get_available_slots, get_order, get_payment_status,
    list_orders, reschedule_order, today,
)
from actionpilot.ui import (
    badge, brand_html, feature_card, field, icon, navigate, render_order_card,
    section_heading, select_customer,
)


def render_order_workspace(customer):
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


def render_home(customers):
    with st.container(key='home_topnav'):
        brand, assistant, dashboard, admin = st.columns([3.4, 1.3, 1.2, .9], gap='small')
        brand.markdown(brand_html(), unsafe_allow_html=True)
        assistant.button('AI Assistant', key='top_assistant', on_click=navigate, args=('AI Assistant',), width='stretch')
        dashboard.button('Dashboard', key='top_dashboard', on_click=navigate, args=('Dashboard',), width='stretch')
        admin.button('Admin', key='top_admin', on_click=navigate, args=('Admin',), width='stretch')
    hero, preview = st.columns([1.15, 1], gap='large')
    with hero:
        st.markdown(
            '<div class="ap-hero"><p class="ap-eyebrow">Beyond the ordinary chatbot</p>'
            '<h1>Customer Support That <span class="ap-gradient-text">Takes Action.</span></h1>'
            '<p>An AI assistant that doesn\'t just answer questions — it helps customers complete real service tasks.</p></div>',
            unsafe_allow_html=True,
        )
        launch, explore = st.columns(2, gap='small')
        launch.button('Launch AI Assistant', key='launch_assistant', type='primary', on_click=navigate,
                      args=('AI Assistant',), icon=':material/auto_awesome:', width='stretch')
        explore.button('Explore Dashboard', key='explore_dashboard', on_click=navigate,
                       args=('Dashboard',), icon=':material/space_dashboard:', width='stretch')
        st.markdown('<p class="ap-trust">Order-aware answers &nbsp;·&nbsp; Customer-scoped access &nbsp;·&nbsp; You approve the change</p>',
                    unsafe_allow_html=True)
        st.markdown(badge('pending', 'Hackathon demo · Synthetic data'), unsafe_allow_html=True)
    with preview, st.container(border=True, key='home_preview'):
        st.markdown('<p class="ap-eyebrow">Live product preview</p>', unsafe_allow_html=True)
        st.subheader('Your next step, grounded in data.')
        customer = select_customer(customers)
        if customer:
            orders = list_orders(customer['id'])
            if orders:
                order = get_order(customer['id'], orders[0]['id'])
                render_order_card(order, get_payment_status(customer['id'], order['id']))
            else:
                st.info('This customer has no orders yet.')
            day = today() + timedelta(days=1)
            slots = get_available_slots(day.isoformat())
            if slots:
                slot = slots[0]
                st.markdown('<div class="ap-card"><div class="ap-card-head"><span class="ap-eyebrow">Available tomorrow</span>'
                            + badge('scheduled', f"{slot['remaining_capacity']} places left") + '</div><div class="ap-fields">'
                            + field('Delivery date · Baku', slot['date'])
                            + field('Delivery window', f"{slot['start_time']}–{slot['end_time']}")
                            + '</div></div>', unsafe_allow_html=True)
            else:
                st.info('No delivery slots available tomorrow. Explore the dashboard to choose another date.')
            st.button('Manage this customer’s orders', key='preview_dashboard', on_click=navigate,
                      args=('Dashboard',), icon=':material/arrow_forward:', width='stretch')
        else:
            st.info('No demo customers are available.')
        st.caption('Current demo records. No changes are made by this preview.')
    section_heading('Built to be useful', 'Answers are just the beginning.',
                    'From a service question to a reviewed action, in one workspace.')
    cards = st.columns(3, gap='medium')
    for column, name, title, description in zip(cards, ['spark', 'bolt', 'shield'],
            ['Intelligent Answers', 'Real Actions', 'Secure Confirmations'],
            ['Find order details, payment status and delivery availability using customer-scoped records.',
             'Prepare a delivery reschedule using real slots and the existing transactional service.',
             'Review the exact order, date and window. Nothing is saved until you explicitly confirm.']):
        with column:
            feature_card(name, title, description)
    section_heading('How it works', 'A conversation. A clear next step.',
                    'You stay in control from the first question to the final confirmation.')
    steps = st.columns(3, gap='large')
    for column, number, title, description in zip(steps, ['01', '02', '03'],
            ['Ask your question.', 'AI understands and checks your order.', 'Confirm and complete your action.'],
            ['Open the assistant and ask about your order, payment or preferred delivery date.',
             'The assistant uses the selected customer’s records and checks available delivery slots.',
             'Review a delivery proposal, then confirm to save it or cancel to leave the order unchanged.']):
        with column:
            st.markdown('<div class="ap-step"><span class="ap-step-number">' + number
                        + '</span><h3>' + escape(title) + '</h3><p>' + escape(description) + '</p></div>',
                        unsafe_allow_html=True)
    section_heading('Supported today', 'Focused on real customer service.',
                    'Four supported capabilities. No invented tools or payment processing.')
    st.markdown('<div class="ap-capabilities">' + ''.join(
        '<span class="ap-capability">' + icon(name) + escape(label) + '</span>'
        for name, label in [('box', 'Order tracking'), ('wallet', 'Payment status'),
                            ('calendar', 'Delivery availability'), ('bolt', 'Delivery rescheduling')])
        + '</div>', unsafe_allow_html=True)
    st.markdown('<footer class="ap-footer"><span>ActionPilot · Customer support that takes action.</span>'
                '<span>Hackathon project · Synthetic data · Simulated customer sessions</span></footer>',
                unsafe_allow_html=True)


def render_assistant(customer):
    st.title('AI Assistant')
    st.caption('Ask a question. Review a proposal. Complete the change only when you’re ready.')
    if not customer:
        st.info('No demo customers are available.')
        return
    chat, orders = st.columns([1.5, 1], gap='large')
    with chat, st.container(border=True, key='ai_panel'):
        render_chat(customer['id'])
    with orders, st.container(border=True, key='order_panel'):
        render_order_workspace(customer)


def render_dashboard(customer):
    st.title('Dashboard')
    st.caption('Your orders and delivery planning, with status straight from the demo database.')
    if not customer:
        st.info('No demo customers are available.')
        return
    orders = list_orders(customer['id'])
    total, eligible, paid = st.columns(3)
    total.metric('Your orders', len(orders))
    eligible.metric('Can reschedule', sum(o['status'] in ('pending', 'scheduled') for o in orders))
    paid.metric('Paid orders', sum(o['payment_status'] == 'paid' for o in orders))
    st.button('Open AI Assistant', key='dashboard_assistant', on_click=navigate,
              args=('AI Assistant',), icon=':material/auto_awesome:')
    overview, manage = st.columns([1.25, 1], gap='large')
    with overview, st.container(border=True, key='dashboard_orders'):
        st.subheader('Your orders')
        st.caption('Only orders belonging to the selected demo customer.')
        if not orders:
            st.info('This customer has no orders yet.')
        for order in orders:
            render_order_card(order, order['payment_status'])
    with manage, st.container(border=True, key='order_panel'):
        render_order_workspace(customer)


def render_admin():
    st.title('Operations overview')
    st.caption('Read-only administration · All synthetic demo customers · No production authentication')
    snapshot = admin_snapshot()
    orders, slots, audit = st.columns(3)
    orders.metric('Demo orders', len(snapshot['orders']))
    slots.metric('Delivery slots', len(snapshot['slots']))
    audit.metric('Confirmed changes', len(snapshot['audit_logs']))
    tabs = st.tabs(['Orders', 'Delivery slots', 'Activity log'])
    for tab, name in zip(tabs, ['orders', 'slots', 'audit_logs']):
        with tab, st.container(border=True):
            st.subheader({'orders': 'Order records', 'slots': 'Delivery capacity', 'audit_logs': 'Confirmed delivery changes'}[name])
            st.caption({'orders': 'Stored payment and delivery status. Payments are read only.',
                        'slots': 'Delivery dates and windows are in Baku time. Disabled and full slots remain visible here.',
                        'audit_logs': 'Only committed reschedules appear here. Audit timestamps are recorded in UTC.'}[name])
            rows = snapshot[name]
            if not rows:
                st.info('No confirmed delivery changes yet.' if name == 'audit_logs' else 'No records available.')
            st.dataframe(rows, width='stretch', hide_index=True)
