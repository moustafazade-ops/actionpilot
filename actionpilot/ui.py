"""Small presentation helpers; no database reads or actions."""
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
