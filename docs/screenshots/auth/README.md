# Authentication recovery browser checks

Captured from this recovery branch using Chromium at localhost on 2026-10-09.
These are new captures, not screenshots copied from the historical implementation.

- `login.png`: desktop Login form at 1440 × 1000.
- `signup.png`: desktop Sign Up form at 1440 × 1000.
- `login-mobile.png`: Login after sign-out at 390 × 844.

Both forms rendered with masked password inputs. A synthetic account was created
in a disposable local PostgreSQL 16 database over TLS, then used to log in, open
Home and sign out. No public deployment, provider database or live OpenAI call
was tested. Current main branding is unchanged; the AP SVG removed by the earlier
snapshot restoration is not present in the main baseline.
