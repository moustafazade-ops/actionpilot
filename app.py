"""ActionPilot: Home, AI Assistant, Dashboard and read-only Admin in Streamlit."""
import streamlit as st

from actionpilot.login import require_login
from actionpilot.seed import seed_demo
from actionpilot.service import list_customers
from actionpilot.ui import apply_styles, badge, navigate, render_account_panel, select_customer
from actionpilot.views import render_admin, render_assistant, render_dashboard, render_home, render_settings

PAGES = {'Home': 'home', 'AI Assistant': 'auto_awesome', 'Dashboard': 'space_dashboard', 'Admin': 'admin_panel_settings', 'Settings': 'settings'}
st.set_page_config(page_title='ActionPilot · Customer support that takes action', page_icon='✦', layout='wide')
apply_styles()
require_login()
seed_demo()
page = st.session_state.setdefault('page', 'Home')
if page not in PAGES:
    page = st.session_state['page'] = 'Home'
customers = list_customers()
with st.sidebar:
    st.markdown('<div class="ap-brand"><span class="ap-logo">AP</span>ActionPilot</div>', unsafe_allow_html=True)
    st.caption('Customer support that takes action')
    st.divider()
    for name, symbol in PAGES.items():
        st.button(name, key=f'nav_{name}', type='primary' if page == name else 'secondary',
                  icon=f':material/{symbol}:', width='stretch', on_click=navigate, args=(name,))
    st.divider()
    render_account_panel()
if page == 'Home':
    render_home(customers)
elif page == 'Settings':
    render_settings()
else:
    with st.sidebar:
        st.divider()
        st.markdown('<p class="ap-eyebrow">Customer context</p>', unsafe_allow_html=True)
        customer = select_customer(customers)
        st.divider()
        st.markdown(badge('pending', 'Synthetic demo data'), unsafe_allow_html=True)
        st.caption('This selector simulates a session. It is not production authentication.')
        st.caption('Delivery times use Asia/Baku. Payment information is read only.')
    st.markdown('<p class="ap-eyebrow">Workspace / ' + page + '</p>', unsafe_allow_html=True)
    if page == 'AI Assistant':
        render_assistant(customer)
    elif page == 'Dashboard':
        render_dashboard(customer)
    else:
        render_admin()
