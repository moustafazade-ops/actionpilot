"""Session-local email verification using Gmail SMTP and Streamlit secrets."""
import hmac
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage

import streamlit as st

CODE_LIFETIME = 300
RESEND_DELAY = 60
MAX_ATTEMPTS = 5
_CHALLENGE_KEYS = ('verification_code', 'verification_time', 'verification_email',
                   'verification_attempts')


def clear_challenge():
    for key in _CHALLENGE_KEYS:
        st.session_state.pop(key, None)


def valid_email(email):
    return (len(email) <= 254 and
            re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}", email) is not None)


def send_verification_code(to_email):
    """Return safe feedback; activate a challenge only after SMTP accepts delivery."""
    to_email = to_email.strip()
    if not valid_email(to_email):
        return False, 'Enter a valid email address.'
    now = time.time()
    last_send = st.session_state.get('verification_last_send')
    if last_send is not None and now - last_send < RESEND_DELAY:
        return False, 'Please wait 60 seconds before requesting another code.'
    try:
        sender = st.secrets['EMAIL_USER']
        password = st.secrets['EMAIL_PASS']
        if not isinstance(sender, str) or not isinstance(password, str) or not sender or not password:
            raise KeyError('email configuration')
    except (KeyError, FileNotFoundError):
        return False, 'Email login is not configured. Add EMAIL_USER and EMAIL_PASS in Streamlit secrets.'

    clear_challenge()
    # Count send attempts too, preventing immediate retries on SMTP failures.
    st.session_state['verification_last_send'] = now
    code = str(secrets.randbelow(900000) + 100000)
    message = EmailMessage()
    message['Subject'] = 'ActionPilot Verification Code'
    message['From'] = sender
    message['To'] = to_email
    message.set_content(f'Your ActionPilot verification code is: {code}\n\n'
                        'This code expires in 5 minutes. Do not share it.\n'
                        'If you did not request this code, ignore this email.')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15,
                              context=ssl.create_default_context()) as server:
            server.login(sender, password)
            refused = server.send_message(message)
            if refused:
                raise smtplib.SMTPException('Recipient refused')
    except (smtplib.SMTPException, OSError, ValueError):
        return False, 'Could not send the code. Check Gmail SMTP settings and try again after 60 seconds.'

    st.session_state.update(verification_code=code, verification_time=time.time(),
                            verification_email=to_email, verification_attempts=0)
    return True, 'Code sent. Check your inbox or spam folder. It expires in 5 minutes.'


def verify_code(email, code):
    state = st.session_state
    if 'verification_code' not in state:
        return False, 'Request a new code first.'
    if time.time() - state['verification_time'] >= CODE_LIFETIME:
        clear_challenge()
        return False, 'Code expired'
    if email.strip() != state['verification_email']:
        return False, 'Your email changed. Send a new code for this address.'
    state['verification_attempts'] += 1
    if re.fullmatch(r'[0-9]{6}', code.strip()) and hmac.compare_digest(code.strip(), state['verification_code']):
        state['logged_in'] = True
        state['login_email'] = state['verification_email']
        clear_challenge()
        return True, 'Email verified.'
    if state['verification_attempts'] >= MAX_ATTEMPTS:
        clear_challenge()
        return False, 'Too many incorrect attempts. Request a new code.'
    return False, 'Incorrect code. Please try again.'


def logout():
    # Clear customer context, transcripts and pending actions along with login.
    for key in list(st.session_state):
        del st.session_state[key]


def require_login():
    if st.session_state.get('logged_in') is True:
        return
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="ap-brand"><span class="ap-logo">AP</span>ActionPilot</div>', unsafe_allow_html=True)
        st.title('Your support workspace awaits.')
        st.caption('Verify your email to open ActionPilot. No password required.')
        with st.container(border=True, key='login_panel'):
            email = st.text_input('Email address', key='login_email_input', placeholder='you@example.com', max_chars=254)
            if st.button('Send code', type='primary', width='stretch'):
                with st.spinner('Sending verification code…'):
                    ok, feedback = send_verification_code(email)
                (st.success if ok else st.error)(feedback)
            st.caption('Enter the six-digit code from your email within 5 minutes. Resend after 60 seconds.')
            with st.form('verify_login'):
                code = st.text_input('Verification code', max_chars=6, placeholder='6-digit code')
                submitted = st.form_submit_button('Verify', type='primary', width='stretch')
            if submitted:
                ok, feedback = verify_code(email, code)
                if ok:
                    st.rerun()
                st.error(feedback)
        st.caption('Synthetic demo workspace · Email verification does not assign a customer account. '
                   'Keep this tab open while checking your email.')
    st.stop()
