"""Native Streamlit account forms and server-owned session authentication."""
import os

import streamlit as st

from actionpilot.auth import AccountStore, AuthError, MAX_PASSWORD_LENGTH, REMEMBER_SECONDS
from actionpilot.ui import brand

_REMEMBER_COOKIE = 'actionpilot_remember'


def account_store():
    """Secrets take precedence; SQLite is an explicit development-only option."""
    try:
        database_url = st.secrets.get('AUTH_DATABASE_URL')
        sqlite_path = st.secrets.get('AUTH_SQLITE_PATH')
    except FileNotFoundError:
        database_url = sqlite_path = None
    return AccountStore(database_url=database_url or os.environ.get('AUTH_DATABASE_URL'),
                        sqlite_path=sqlite_path or os.environ.get('AUTH_SQLITE_PATH'))


def _clear_session():
    # Remove customer context, transcripts, pending actions and credential widgets.
    for key in list(st.session_state):
        del st.session_state[key]


def logout():
    token = st.session_state.get('remember_token')
    if token:
        try:
            account_store().revoke_remember_session(token)
        except AuthError:
            st.session_state['_logout_error'] = 'Could not revoke saved sign-in. Please try signing out again.'
            return
    _clear_session()
    st.session_state['_remember_checked'] = True
    st.session_state['_cookie_write'] = ''


def _remember_cookie():
    return st.context.cookies.get(_REMEMBER_COOKIE, '')


def _write_remember_cookie():
    token = st.session_state.pop('_cookie_write', None)
    if token is None:
        return
    # Only application-generated hex tokens enter JavaScript; never emails/passwords.
    if token and (len(token) != 64 or any(c not in '0123456789abcdef' for c in token)):
        raise ValueError('Invalid remembered session token')
    max_age = REMEMBER_SECONDS if token else 0
    st.iframe(f'''<script>
    (() => {{
      const page = window.parent.location;
      const secure = page.protocol === 'https:';
      const local = ['localhost', '127.0.0.1', '[::1]'].includes(page.hostname);
      if (secure || local || {str(not bool(token)).lower()}) {{
        document.cookie = '{_REMEMBER_COOKIE}={token}; Max-Age={max_age}; Path=/; SameSite=Strict'
          + (secure ? '; Secure' : '');
      }}
    }})();
    </script>''', height=1, width=1, tab_index=-1)


def _sign_in(email, password, remember=False):
    store = account_store()
    verified_email = store.login(email, password)
    token = store.create_remember_session(verified_email) if remember is True else None
    _clear_session()
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = verified_email
    st.session_state['page'] = 'Home'
    st.session_state['_remember_checked'] = True
    st.session_state['_cookie_write'] = token or ''
    if token:
        st.session_state['remember_token'] = token
    st.rerun()


def _finish_submission(tab, message, success=False):
    st.session_state['_auth_feedback'] = (tab, message, success)
    # clear_on_submit is a browser behavior; also remove credentials server-side.
    for key in ('signin_password', 'signup_password', 'signup_confirmation'):
        st.session_state.pop(key, None)
    st.rerun()


def require_login():
    state = st.session_state
    _write_remember_cookie()
    logout_error = state.pop('_logout_error', None)
    if logout_error:
        st.error(logout_error)
    if state.get('logged_in') is True and isinstance(state.get('user_email'), str) and state['user_email']:
        return
    # Existing passwordless sessions must authenticate with their new account.
    if state.get('logged_in'):
        _clear_session()
    if not state.get('_remember_checked'):
        state['_remember_checked'] = True
        token = _remember_cookie()
        if token:
            try:
                email = account_store().restore_remember_session(token)
            except AuthError as error:
                st.error(str(error))
            else:
                if email:
                    state['logged_in'] = True
                    state['user_email'] = email
                    state['remember_token'] = token
                    state['page'] = 'Home'
                    return
                state['_cookie_write'] = ''
                _write_remember_cookie()
    feedback = state.pop('_auth_feedback', None)
    _, center, _ = st.columns([1, 1.6, 1])
    with center:
        st.markdown(brand(), unsafe_allow_html=True)
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
                    remember = st.checkbox('Remember me', key='signin_remember',
                                           help='Stay signed in on this device for 30 days. Use only on a trusted device. Requires HTTPS, except on localhost.')
                    submitted = st.form_submit_button('Log in', type='primary', width='stretch')
                if submitted:
                    try:
                        with st.spinner('Signing in…'):
                            _sign_in(email, password, remember)
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
