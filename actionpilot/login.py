"""Native Streamlit account forms and server-owned session authentication."""
import os

import streamlit as st

from actionpilot.auth import AccountStore, AuthError, MAX_PASSWORD_LENGTH


def account_store():
    """Secrets take precedence; SQLite is an explicit development-only option."""
    try:
        database_url = st.secrets.get('AUTH_DATABASE_URL')
        sqlite_path = st.secrets.get('AUTH_SQLITE_PATH')
    except FileNotFoundError:
        database_url = sqlite_path = None
    return AccountStore(database_url=database_url,
                        sqlite_path=sqlite_path or os.environ.get('AUTH_SQLITE_PATH'))


def logout():
    # Remove customer context, transcripts, pending actions and credential widgets.
    for key in list(st.session_state):
        del st.session_state[key]


def _sign_in(email, password):
    verified_email = account_store().login(email, password)
    logout()
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = verified_email
    st.session_state['page'] = 'Home'
    st.rerun()


def _finish_submission(tab, message, success=False):
    st.session_state['_auth_feedback'] = (tab, message, success)
    # clear_on_submit is a browser behavior; also remove credentials server-side.
    for key in ('signin_password', 'signup_password', 'signup_confirmation'):
        st.session_state.pop(key, None)
    st.rerun()


def require_login():
    state = st.session_state
    if state.get('logged_in') is True and isinstance(state.get('user_email'), str) and state['user_email']:
        return
    # Existing passwordless sessions must authenticate with their new account.
    if state.get('logged_in'):
        logout()
    feedback = state.pop('_auth_feedback', None)
    _, center, _ = st.columns([1, 1.6, 1])
    with center:
        st.markdown('<div class="ap-brand"><span class="ap-logo">AP</span>ActionPilot</div>', unsafe_allow_html=True)
        st.markdown('<p class="ap-eyebrow">Your support workspace</p>', unsafe_allow_html=True)
        st.title('Welcome to ActionPilot.')
        st.caption('Sign in to manage support, explore your dashboard, and work with your AI assistant.')
        with st.container(border=True, key='login_panel'):
            login_tab, signup_tab = st.tabs(['Login', 'Sign Up'])
            with login_tab:
                st.subheader('Welcome back')
                if feedback and feedback[0] == 'login':
                    st.error(feedback[1])
                with st.form('login_form', clear_on_submit=True):
                    email = st.text_input('Email address', key='signin_email', placeholder='you@gmail.com', max_chars=254)
                    password = st.text_input('Password', type='password', key='signin_password', max_chars=MAX_PASSWORD_LENGTH)
                    submitted = st.form_submit_button('Log in', type='primary', width='stretch')
                if submitted:
                    try:
                        with st.spinner('Signing in…'):
                            _sign_in(email, password)
                    except AuthError as error:
                        _finish_submission('login', str(error))
            with signup_tab:
                st.subheader('Create your account')
                st.caption('Use your Gmail or another email address and a password with 15–128 characters.')
                if feedback and feedback[0] == 'signup':
                    (st.success if feedback[2] else st.error)(feedback[1])
                with st.form('signup_form', clear_on_submit=True):
                    email = st.text_input('Email address', key='signup_email', placeholder='you@gmail.com', max_chars=254)
                    password = st.text_input('Password', type='password', key='signup_password', max_chars=MAX_PASSWORD_LENGTH)
                    confirmation = st.text_input('Confirm password', type='password', key='signup_confirmation', max_chars=MAX_PASSWORD_LENGTH)
                    submitted = st.form_submit_button('Create account', type='primary', width='stretch')
                if submitted:
                    try:
                        with st.spinner('Creating your account…'):
                            account_store().sign_up(email, password, confirmation)
                    except AuthError as error:
                        _finish_submission('signup', str(error))
                    else:
                        _finish_submission('signup', 'Account created. Open the Login tab to sign in.', True)
        st.caption('ActionPilot demo · The workspace uses synthetic customers and orders.')
    st.stop()
