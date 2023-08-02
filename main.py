from flask import Flask, render_template
from flask_cors import CORS
from os import environ as env
import events
import users
import coordinators

app = Flask(__name__)
CORS(app)

app.secret_key = env.get('APP_SECRET_KEY')

app.register_blueprint(events.bp)
app.register_blueprint(users.bp)
app.register_blueprint(coordinators.bp)

users.oauth.init_app(app)

@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)