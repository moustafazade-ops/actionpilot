"""Small presentation helpers; no database reads or actions."""
from html import escape
from pathlib import Path
from base64 import b64encode
from functools import lru_cache

import streamlit as st

_STATUS_COLORS = {
    'paid': 'green', 'delivered': 'green', 'scheduled': 'blue',
    'dispatched': 'blue', 'pending': 'amber', 'failed': 'red',
    'cancelled': 'neutral', 'refunded': 'neutral',
}


_ASSETS = Path(__file__).with_name('assets')
_ICONS = {
    'spark': 'message-chatbot', 'bolt': 'bolt', 'shield': 'shield-check',
    'box': 'package', 'wallet': 'credit-card', 'calendar': 'calendar-clock',
    'arrow': 'arrow-up-right', 'check': 'check', 'chat': 'message-circle',
    'dashboard': 'layout-dashboard', 'home': 'home', 'admin': 'adjustments-horizontal',
    'refresh': 'calendar-event', 'send': 'arrow-right',
}


@lru_cache(maxsize=None)
def icon(name):
    """Vendored Tabler outline SVGs, not application-generated paths."""
    return (_ASSETS / 'icons' / f'{_ICONS[name]}.svg').read_text().replace(
        '<svg ', '<svg aria-hidden="true" focusable="false" ', 1,
    ).replace('stroke-width="2"', 'stroke-width="1.75"')


@lru_cache(maxsize=1)
def _asset_styles():
    css = ''
    for family, filename in [('Geist', 'Geist.woff2'), ('Geist Mono', 'GeistMono.woff2')]:
        font = b64encode((_ASSETS / 'fonts' / filename).read_bytes()).decode('ascii')
        css += (f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{font}) '
                'format("woff2");font-style:normal;font-weight:100 900;font-display:swap;}')
    # Keep native Streamlit buttons and their accessible labels. Only the visual
    # material glyph is replaced by the same Tabler family used in HTML panels.
    for selector, name in [
        ('.st-key-launch_assistant', 'chat'), ('.st-key-explore_dashboard', 'dashboard'),
        ('.st-key-preview_dashboard', 'arrow'), ('.st-key-dashboard_assistant', 'chat'),
        ('[class*="st-key-nav_Home"]', 'home'),
        ('[class*="st-key-nav_AI"]', 'chat'),
        ('[class*="st-key-nav_Dashboard"]', 'dashboard'),
        ('[class*="st-key-nav_Admin"]', 'admin'),
    ]:
        svg = b64encode(icon(name).replace('currentColor', 'black').encode()).decode('ascii')
        css += (f'{selector} [data-testid="stIconMaterial"]{{font-size:0;width:19px;height:19px;'
                f'background:currentColor;mask:url("data:image/svg+xml;base64,{svg}") center/contain no-repeat;}}')
    return css


def apply_styles():
    css = Path(__file__).with_name('dashboard.css').read_text() + _asset_styles()
    st.html('<style>' + css + '</style>')


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
        f'<span class="ap-order-id">{icon("box")} Order #{escape(str(order["id"]))}</span>'
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
        + field('Time · Baku', f"{slot['start_time']}-{slot['end_time']}")
        + '</div></section>', unsafe_allow_html=True,
    )


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
    st.markdown('<div class="ap-section-heading">'
                + ('<p class="ap-eyebrow">' + escape(eyebrow) + '</p>' if eyebrow else '')
                + '<h2>' + escape(title) + '</h2><p>' + escape(subtitle) + '</p></div>',
                unsafe_allow_html=True)


def feature_card(name, title, description, visual=''):
    return ('<article class="ap-feature ap-feature--' + name + '"><span class="ap-icon">' + icon(name)
            + '</span><h3>' + escape(title) + '</h3><p>' + escape(description)
            + '</p>' + visual + '</article>')
