from flask import Flask, redirect, url_for, session, flash, render_template, request
from authlib.integrations.flask_client import OAuth
import os
import requests
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this to something secure in production

# Ensure generated external URLs use http by default in local dev
# Optionally force a specific host:port for redirect URIs by setting
# OAUTH_REDIRECT_HOST in your .env (for example: "localhost:5000").
app.config.setdefault('PREFERRED_URL_SCHEME', 'http')
redirect_host = os.getenv('OAUTH_REDIRECT_HOST')
if redirect_host:
    # Example value: 'localhost:5000' or 'example.com'
    app.config['SERVER_NAME'] = redirect_host

oauth = OAuth(app)

# ---------------- GOOGLE LOGIN ----------------
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'
    }
)

# ---------------- LINKEDIN LOGIN ----------------
# linkedin = oauth.register(
#     name='linkedin',
#     client_id=os.getenv("LINKEDIN_CLIENT_ID"),
#     client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
#     access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
#     authorize_url='https://www.linkedin.com/oauth/v2/authorization',
#     # jwks_endpoint='https://www.linkedin.com/oauth/openid/jwks',
#     client_kwargs={
#         # Request only r_liteprofile by default. r_emailaddress often requires
#         # the 'Sign In with LinkedIn' product to be added to your LinkedIn app.
#         # If you enable that product and get permission, you can add
#         # 'r_emailaddress' back here.
#         # 'scope': 'email profile',
#         # 'token_endpoint_auth_method': 'client_secret_post'
#         "scope": "openid profile email",
#     }
# )
linkedin = oauth.register(
    name='linkedin',
    client_id=os.getenv("LINKEDIN_CLIENT_ID"),
    client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
    client_kwargs={
        "scope": "openid profile email",
        'token_endpoint_auth_method': 'client_secret_post'
    }
)

# ---------------- ROUTES ----------------


@app.route("/")
def index():
    user = session.get("user")
    return render_template("login.html", user=user)


@app.route("/login/google")
def login_google():
    redirect_uri = url_for("auth_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google")
def auth_google():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get(
            'https://www.googleapis.com/oauth2/v3/userinfo')
        userinfo = resp.json()

        session["user"] = {
            "provider": "google",
            "id": userinfo.get("sub"),
            "name": userinfo.get("name"),
            "email": userinfo.get("email"),
            "picture": userinfo.get("picture")
        }

        flash("Logged in with Google!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        flash(f"Failed to log in with Google: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/login/linkedin")
def login_linkedin():
    redirect_uri = url_for("auth_linkedin", _external=True)
    return oauth.linkedin.authorize_redirect(redirect_uri)


@app.route("/auth/linkedin")
def auth_linkedin():
    try:
        code = request.args.get('code')
        if not code:
            raise Exception("No authorization code provided")

        redirect_uri = url_for("auth_linkedin", _external=True)
        token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': os.getenv("LINKEDIN_CLIENT_ID"),
            'client_secret': os.getenv("LINKEDIN_CLIENT_SECRET"),
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        resp = requests.post(token_url, data=data, headers=headers)
        resp.raise_for_status()  # Raise if HTTP error
        token = resp.json()

        access_token = token.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        # Fetch userinfo using OIDC endpoint (unchanged)
        userinfo = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        session["user"] = {
            "provider": "linkedin",
            "id": userinfo.get("sub"),
            "name": userinfo.get("name"),
            "email": userinfo.get("email"),
            "picture": userinfo.get("picture"),
        }

        flash("Logged in with LinkedIn!", "success")
        return redirect(url_for("profile"))

    except Exception as e:
        print("ERROR:", e)
        flash(f"Failed to log in with LinkedIn: {str(e)}", "danger")
        return redirect(url_for("index"))

# Debug route to show the exact redirect URIs the app will generate.


@app.route('/debug/redirects')
def debug_redirects():
    google_redirect = url_for('auth_google', _external=True)
    linkedin_redirect = url_for('auth_linkedin', _external=True)
    return {
        'google_redirect_uri': google_redirect,
        'linkedin_redirect_uri': linkedin_redirect,
        'note': 'Register these exact URIs in your Google and LinkedIn app settings. Include both http://localhost:5000 and http://127.0.0.1:5000 variations if you sometimes use the other host.'
    }


@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("index"))
    return render_template("profile.html", user=user)


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You’ve been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
