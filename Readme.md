# Social Login Flask Example

This repository contains a minimal Flask app demonstrating social login via Google and LinkedIn using OpenID Connect (OIDC) and OAuth2.

The main application file is `app1.py` which registers two OAuth clients (Google and LinkedIn) with `authlib` and exposes routes to:

- initiate login (/login/google, /login/linkedin)
- handle callbacks (/auth/google, /auth/linkedin)
- show a simple profile page (/profile)
- debug the redirect URIs the app generates (/debug/redirects)

This README explains how to set up, configure, run, and troubleshoot the project.

## Table of Contents

- Requirements
- Quick start (setup & run)
- Environment variables
- Registering OAuth apps (Google, LinkedIn)
- How the app works (overview)
- Debugging & troubleshooting
- Security notes
- Next steps / enhancements


## Requirements

- Python 3.10+ (the repo was run with 3.14 in dev, but 3.10+ should be fine)
- pip
- A Google OAuth client (OIDC) and a LinkedIn app with appropriate products/scopes

Python packages (install with pip):

- Flask
- Authlib
- python-dotenv
- requests

You can install the packages with:

```bash
python -m venv .venv
source .venv/bin/activate
pip install Flask authlib python-dotenv requests
```


## Quick start — setup & run

1. Create a `.env` file in the project root. See the "Environment variables" section below for variables to add.

2. (Optional) Register your apps in Google and LinkedIn and configure redirect URIs to match what the app will generate. You can view the exact URIs by running the app and visiting `/debug/redirects` (see below).

3. Run the app:

```bash
# activate virtualenv if not already
source .venv/bin/activate
python app1.py
```

4. Open http://127.0.0.1:5000/ (or http://localhost:5000/) in your browser and try logging in with Google or LinkedIn.


## Environment variables

Create a `.env` file with the following keys (example values shown):

```
# Flask
SECRET_KEY=supersecretkey

# Google
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LinkedIn
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# Optional: explicitly set a host:port used when building redirect URLs
# Example: OAUTH_REDIRECT_HOST=localhost:5000
# If unset, Flask will generate redirects using the current host used to reach the app.
OAUTH_REDIRECT_HOST=localhost:5000
```

Notes:
- `SECRET_KEY` is used by Flask for sessions and flash messages. Replace it with a secure random value in production.
- `OAUTH_REDIRECT_HOST` (optional) lets you force `url_for(..., _external=True)` to produce a specific host:port when generating redirect URIs. This is useful if your OAuth app registration expects a fixed redirect URI such as `http://localhost:5000/auth/google`.


## Registering OAuth apps

Below are condensed instructions for creating OAuth credentials and what values to set for redirect URIs.

### Google (OpenID Connect)

1. Go to Google Cloud Console → APIs & Services → Credentials.
2. Create an OAuth 2.0 Client ID (Application type: Web application).
3. Add Authorized redirect URIs. Use the exact redirect URI shown by the app's `/debug/redirects` endpoint (for example: `http://localhost:5000/auth/google`). If you sometimes use `127.0.0.1`, register both variants.
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` file.

Scopes used by the app: `openid email profile` (configured in `app1.py`).

### LinkedIn

> Note: LinkedIn's API and products can require you to request specific products on your LinkedIn Developer app dashboard (e.g., 'Sign In with LinkedIn') before r_emailaddress is available. The LinkedIn OIDC and profile APIs also vary over time — follow LinkedIn's developer docs for the current endpoints and required scopes.

1. Go to LinkedIn Developer Portal → Your App → Auth.
2. Add the redirect URI(s) shown by `/debug/redirects` (e.g. `http://localhost:5000/auth/linkedin`). Register both `localhost` and `127.0.0.1` variants if you switch between them.
3. On the 'Products' tab, add the required products (e.g., 'Sign In with LinkedIn' for email access if needed).
4. Set `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` in your `.env` file.

Scopes used in `app1.py`: `openid profile email` (configured in the code). The app performs a token exchange manually for LinkedIn and then attempts to call `https://api.linkedin.com/v2/userinfo` to fetch user claims.


## How the app works (overview)

- `authlib.integrations.flask_client.OAuth` registers providers for Google and LinkedIn.
- For Google: `authlib` uses Google's OIDC discovery endpoint to handle the full flow automatically (`server_metadata_url` is set).
- For LinkedIn: the code registers LinkedIn with `server_metadata_url` and also contains a manual token exchange in `/auth/linkedin`. The manual exchange builds a POST to LinkedIn's token endpoint and then calls an OIDC userinfo endpoint.
- After a successful login the app stores a minimal `session['user']` dictionary with provider, id, name, email, and picture, and redirects to `/profile`.


## Debugging & troubleshooting

Before diving into OAuth provider settings, use the app's debug endpoint to confirm redirect URIs:

- Visit `http://localhost:5000/debug/redirects` after starting the app. It prints the exact URIs the app will register with the OAuth providers.

Common problems and fixes:

- redirect_uri_mismatch (common):
	- Provider error says the redirect URI in the request doesn't match the one registered in the app settings. Ensure the exact URI (scheme, host, port, path) returned by `/debug/redirects` is registered.
	- If you run locally and sometimes use `127.0.0.1` and other times `localhost`, register both.

- Invalid client / unauthorized_client:
	- Check that the client ID and client secret are correct in `.env` and were copied from the provider dashboard.

- Missing authorization code (`No authorization code provided` in `/auth/linkedin`):
	- That means the OAuth provider did not return `?code=...` to your callback. Confirm the redirect URI the provider uses is the same you registered and the same as what the app expects.

- LinkedIn specific issues (no userinfo, unexpected responses):
	- LinkedIn has historically changed endpoints and required product access for email/profile fields. If `https://api.linkedin.com/v2/userinfo` returns 404 or unexpected JSON, consult LinkedIn docs and/or use LinkedIn's v2 endpoints such as `https://api.linkedin.com/v2/me` and `https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))` to fetch profile & email.
	- The code in this repo uses a simple userinfo call—if LinkedIn rejects it, replace the userinfo call with the multi-endpoint calls above.

- Token exchange errors and HTTP 400/401:
	- The manual token exchange in `/auth/linkedin` sets `Content-Type: application/x-www-form-urlencoded` and POSTs the `grant_type`, `code`, `redirect_uri`, `client_id`, and `client_secret`. Make sure these values match the provider's expectations. Check provider logs and response body for detailed error messages.

Collecting debug info to help:

- Reproduce the error and capture the browser URL and any query parameters on redirect.
- Check the Flask console output for exception stacks printed by the app.
- Use the `/debug/redirects` page to verify redirect URIs.
- If using LinkedIn, try the token exchange manually with curl (inspect returned JSON). Example (optional):

```bash
curl -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
	-d grant_type=authorization_code \
	-d code=THE_CODE_FROM_CALLBACK \
	-d redirect_uri="http://localhost:5000/auth/linkedin" \
	-d client_id=... \
	-d client_secret=...
```


## Security notes

- Do not hardcode `SECRET_KEY` or OAuth client secrets in repository. Use environment variables or a secrets manager.
- In production, always use HTTPS and register HTTPS redirect URIs with providers.
- Consider using server-side session storage (Redis, database) instead of default signed cookies for larger apps.
- Validate and sanitize any data you display from provider responses.


## Next steps / enhancements

- Add a `requirements.txt` or `pyproject.toml` to lock dependencies.
- Improve LinkedIn handling: use `https://api.linkedin.com/v2/me` + email endpoint and map fields reliably.
- Add unit tests for the Flask routes (mocking OAuth responses).
- Add logout with provider revocation if needed.


## Files of interest

- `app1.py` — main application and OAuth flows.
- `templates/` — simple templates used by the app: `login.html`, `profile.html`, `base.html`.


## Example: minimal `.env` for local testing

```
SECRET_KEY=replace-with-secure-value
GOOGLE_CLIENT_ID=your-google-id
GOOGLE_CLIENT_SECRET=your-google-secret
LINKEDIN_CLIENT_ID=your-linkedin-id
LINKEDIN_CLIENT_SECRET=your-linkedin-secret
OAUTH_REDIRECT_HOST=localhost:5000
```


Screenshots of the flow:
Google:
<img width="1707" height="979" alt="Screenshot 2025-11-04 at 11 17 51 PM" src="https://github.com/user-attachments/assets/3deac68e-adb7-4880-a526-55c62d26ae5c" />
<img width="1392" height="840" alt="Screenshot 2025-11-04 at 11 18 08 PM" src="https://github.com/user-attachments/assets/dfe506a9-b893-4721-b636-1e5423e82da5" />
<img width="1615" height="875" alt="Screenshot 2025-11-04 at 11 20 39 PM" src="https://github.com/user-attachments/assets/1d48d6fb-dea6-4894-9a8c-ad547b4449a4" />
<img width="1651" height="915" alt="Screenshot 2025-11-04 at 11 20 54 PM" src="https://github.com/user-attachments/assets/d1465607-4f4d-4d14-b099-ed2968c71e4b" />
<img width="1710" height="724" alt="Screenshot 2025-11-04 at 11 22 21 PM" src="https://github.com/user-attachments/assets/0365abc9-f9d0-427e-878e-7cd44ee2f742" />
<img width="1709" height="684" alt="Screenshot 2025-11-04 at 11 19 07 PM" src="https://github.com/user-attachments/assets/c654100e-927d-4c51-b036-ee94527911ec" />


LinkedIn:
<img width="1707" height="979" alt="Screenshot 2025-11-04 at 11 17 51 PM" src="https://github.com/user-attachments/assets/3deac68e-adb7-4880-a526-55c62d26ae5c" />
<img width="1709" height="684" alt="Screenshot 2025-11-04 at 11 19 07 PM" src="https://github.com/user-attachments/assets/d27ba9ca-315a-414e-b08a-7fa4f7fa63f9" />
<img width="1709" height="834" alt="Screenshot 2025-11-04 at 11 19 39 PM" src="https://github.com/user-attachments/assets/29e8e3ad-8129-4c22-863c-6c7bb90b35f5" />






