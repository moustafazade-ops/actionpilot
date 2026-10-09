"""Small presentation helpers; no database reads or actions."""
from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st

_STATUS_COLORS = {
    'paid': 'green', 'delivered': 'green', 'scheduled': 'blue',
    'dispatched': 'blue', 'pending': 'amber', 'failed': 'red',
    'cancelled': 'neutral', 'refunded': 'neutral',
}


def apply_styles():
    st.html('<style>' + Path(__file__).with_name('dashboard.css').read_text() + '</style>')


def brand_html():
    logo = Path(__file__).with_name('assets').joinpath('logo.svg').read_bytes()
    encoded = b64encode(logo).decode('ascii')
    return ('<div class="ap-brand">'
            f'<img class="ap-logo" src="data:image/svg+xml;base64,{encoded}" '
            'alt="ActionPilot AP logo" width="68" height="38">ActionPilot</div>')


def badge(status, label=None):
    color = _STATUS_COLORS.get(status, 'neutral')
    text = label if label is not None else status.replace('_', ' ').title()
    return f'<span class="ap-badge ap-badge--{color}">{escape(str(text))}</span>'


def field(label, value):
    return (f'<div><span class="ap-label">{escape(str(label))}</span>'
            f'<span class="ap-value">{escape(str(value))}</span></div>')


def render_order_card(order, payment_status):
    slot = f"Slot #{order['slot_id']}" if order['slot_id'] is not None else 'Not assigned'
    # The schema stores cents but no currency; avoid inventing a currency code.
    amount = f"{order['amount_cents']:,} cents"
    st.markdown(
        '<section class="ap-card" aria-label="Order summary">'
        '<div class="ap-card-head">'
        f'<span class="ap-eyebrow">Order #{escape(str(order["id"]))}</span>'
        f'{badge(order["status"], "Delivery · " + order["status"].title())}</div>'
        f'<p class="ap-card-title">{escape(order["item"])}</p>'
        '<div class="ap-fields">'
        f'<div><span class="ap-label">Payment</span>{badge(payment_status)}</div>'
        + field('Order amount', amount)
        + field('Delivery assignment', slot)
        + field('Data source', 'Synthetic demo')
        + '</div></section>', unsafe_allow_html=True,
    )


def render_proposal_card(order, slot):
    st.markdown(
        '<section class="ap-card" aria-label="Proposed delivery change">'
        '<div class="ap-card-head"><span class="ap-eyebrow">Delivery proposal</span>'
        + badge('pending', 'Awaiting confirmation') + '</div>'
        + f'<p class="ap-card-title">Order #{escape(str(order["id"]))} · {escape(order["item"])}</p>'
        + '<div class="ap-fields">'
        + field('Delivery date', slot['date'])
        + field('Time · Baku', f"{slot['start_time']}–{slot['end_time']}")
        + '</div></section>', unsafe_allow_html=True,
    )


# One icon family: small, consistent outline SVGs without external assets.
_ICON_PATHS = {
    'spark': '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/>',
    'bolt': '<path d="m13 2-9 12h7l-1 8 10-13h-7Z"/>',
    'shield': '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    'box': '<path d="m12 3 9 5-9 5-9-5Z"/><path d="M3 8v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5"/>',
    'wallet': '<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 9h18m-6 4h6m-4 3h1"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18m-14 5h3m4 0h3"/>',
}


def icon(name):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + _ICON_PATHS[name] + '</svg>')


def navigate(page):
    st.session_state['page'] = page


def select_customer(customers):
    names = {c['id']: c['name'] for c in customers}
    customer_id = st.selectbox('Customer', list(names), format_func=lambda cid: names[cid],
                               key='active_customer', help='Synthetic customer context for both chat and manual support.')
    state = st.session_state.get('support_chat')
    if state and state['customer_id'] != customer_id:
        # Invalidate context even when switching on Home, Dashboard or Admin.
        del st.session_state['support_chat']
    return next((c for c in customers if c['id'] == customer_id), None)


def section_heading(eyebrow, title, subtitle=''):
    st.markdown('<div class="ap-section-heading"><p class="ap-eyebrow">' + escape(eyebrow)
                + '</p><h2>' + escape(title) + '</h2><p>' + escape(subtitle) + '</p></div>',
                unsafe_allow_html=True)


def feature_card(name, title, description):
    st.markdown('<article class="ap-feature"><span class="ap-icon">' + icon(name)
                + '</span><h3>' + escape(title) + '</h3><p>' + escape(description) + '</p></article>',
                unsafe_allow_html=True)
