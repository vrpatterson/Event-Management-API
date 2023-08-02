from flask import Flask, Blueprint, json, jsonify, request, redirect, render_template, session, url_for
from dotenv import load_dotenv, find_dotenv
from os import environ as env
from google.cloud import datastore
from authlib.integrations.flask_client import OAuth
from urllib.parse import quote_plus, urlencode
from six.moves.urllib.request import urlopen
from jose import jwt
import requests


ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

client = datastore.Client()
bp = Blueprint('users', __name__, url_prefix='/')
bp.secret_key = env.get('APP_SECRET_KEY')

CLIENT_ID = env.get("AUTH0_CLIENT_ID")
CLIENT_SECRET = env.get("AUTH0_CLIENT_SECRET")
DOMAIN = env.get("AUTH0_DOMAIN")

ALGORITHMS = ["RS256"]

oauth = OAuth()

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
server_metadata_url=f'https://{DOMAIN}/.well-known/openid-configuration'
)


# The following code for class AuthError(), handle_auth_error function, and verify_jwt function is adapted from:
#  https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@bp.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError({"code": "no auth header",
                            "description":
                                "Authorization header is missing"}, 401)
    
    jsonurl = urlopen("https://"+ DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
    if unverified_header["alg"] == "HS256":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://"+ DOMAIN+"/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                            "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                            "description":
                                "incorrect claims,"
                                " please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Unable to parse authentication"
                                " token."}, 401)

        return payload
    else:
        raise AuthError({"code": "no_rsa_key",
                            "description":
                                "No RSA key in JWKS"}, 401)
    
@bp.route('/decode', methods=['GET'])
def decode_jwt():
    """ Decodes the JWT supplied in the Authorization header """
    payload = verify_jwt(request)
    return payload   

@bp.route('/login_user', methods=['POST'])
def login_user():
    """ Logs in the user using oauth"""
    content = request.get_json()
    username = content["username"]
    password = content["password"]
    body = {'grant_type':'password',
            'username':username,
            'password':password,
            'client_id':CLIENT_ID,
            'client_secret':CLIENT_SECRET
           }
    headers = { 'content-type': 'application/json' }
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)
    auth_response = r.json()

    return r.text, r.status_code, {'Content-Type':'application/json'}    

# Code for login() ,callback(), and logout() functions was modified from:
# https://auth0.com/docs/quickstart/webapp/python
 
@bp.route("/login")
def login():
    """ Triggers authentication """
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("users.callback", _external=True)
    )

@bp.route("/callback", methods=["GET", "POST"])
def callback():
    """ Finalizes authentication - saves session for the user"""
    token = oauth.auth0.authorize_access_token()
    resp = oauth.auth0.get('userinfo')
    userinfo = resp.json()
    session["jwt_payload"] = userinfo
    session["users"] = token
    user_id = userinfo['sub']
    add_new_user(user_id)
    return render_template("userinfo.html", session=session, user_id=user_id)

def add_new_user(user_id):
    """ Used for creating a new user """
    query = client.query(kind='User')
    query.add_filter('user_id', '=', user_id)
    users = list(query.fetch())
    if len(users) == 0:
        new_user = datastore.entity.Entity(key=client.key('User'))
        new_user.update({"user_id": user_id})
        client.put(new_user)

@bp.route("/logout")
def logout():
    """ Logs out user """
    session.clear()
    return redirect(
        "https://" + DOMAIN
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("users.home", _external=True),
                "client_id": CLIENT_ID,
            },
            quote_via=quote_plus
        )
    )

@bp.route('/')
def home():
    return render_template('index.html', session=session.get('users'), pretty=json.dumps(session.get('users'), indent=4))