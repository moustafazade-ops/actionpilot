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
LOGO_PATH = _ASSETS / 'ap_green.png'


@lru_cache(maxsize=1)
def brand():
    logo = b64encode(LOGO_PATH.read_bytes()).decode('ascii')
    return ('<div class="ap-brand"><span class="ap-logo">'
            f'<img src="data:image/png;base64,{logo}" alt="ActionPilot logo">'
            '</span>ActionPilot</div>')


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
        ('[class*="st-key-nav_Settings"]', 'admin'),
    ]:
        svg = b64encode(icon(name).replace('currentColor', 'black').encode()).decode('ascii')
        css += (f'{selector} [data-testid="stIconMaterial"]{{font-size:0;width:19px;height:19px;'
                f'background:currentColor;mask:url("data:image/svg+xml;base64,{svg}") center/contain no-repeat;}}')
    return css


_THEMES = {
    'Light': {
        'scheme': 'light', 'bg': '#f3f9f8', 'surface': '#ffffff',
        'raised': '#edf5f4', 'sidebar': '#e7f2ef', 'border': '#ccdeda',
        'text': '#173b3a', 'muted': '#506d6a', 'blue': '#087b89',
        'accent': '#b8e895', 'accent-hover': '#a4dc7c', 'on-accent': '#234326',
        'tint': '#d7f2f3', 'hover': '#e0eeeb', 'green-bg': '#eaf6e2',
        'green-text': '#356522', 'amber-bg': '#fcf0d9', 'amber-text': '#795517',
        'red-bg': '#fbe7e7', 'red-text': '#a13746',
        'shadow': '#2a716415', 'glint': '#ffffff80', 'table-filter': 'none',
    },
    'Dark': {
        'scheme': 'dark', 'bg': '#101e21', 'surface': '#182a2d',
        'raised': '#203539', 'sidebar': '#132427', 'border': '#385356',
        'text': '#e7f4ef', 'muted': '#a3bdb7', 'blue': '#8bdde3',
        'accent': '#b8e895', 'accent-hover': '#ceeeb5', 'on-accent': '#234326',
        'tint': '#24464b', 'hover': '#2b4246', 'green-bg': '#233c2f',
        'green-text': '#c0e6aa', 'amber-bg': '#423822', 'amber-text': '#efce8d',
        'red-bg': '#452c33', 'red-text': '#f0b4bb',
        'shadow': '#07141650', 'glint': '#ffffff15',
        'table-filter': 'invert(0.9) hue-rotate(180deg)',
    },
}


def apply_styles():
    theme = _THEMES.get(st.session_state.get('theme_mode', 'Light'), _THEMES['Light'])
    tokens = ':root{' + ''.join(f'--ap-{key}:{value};' for key, value in theme.items()) + '}'
    css = Path(__file__).with_name('dashboard.css').read_text() + _asset_styles()
    st.html('<style>' + tokens + css + '</style>')


def render_account_panel():
    """Display only the authenticated account, separate from demo customer context."""
    from actionpilot.login import logout
    email = st.session_state['user_email']
    initial = escape(email[:1].upper())
    with st.container(key='account_panel'):
        st.markdown('<div class="ap-account-header"><span class="ap-avatar">' + initial
                    + '</span><div><strong>Your account</strong><small>Support workspace</small>'
                    + '</div></div>', unsafe_allow_html=True)
        st.caption(f'Signed in as {email}')
        st.button('Account settings', key='account_settings', on_click=navigate,
                  args=('Settings',), width='stretch')
        st.button('Sign out', on_click=logout, width='stretch')


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
