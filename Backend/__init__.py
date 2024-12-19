from flask import Flask

from Backend import pages


import secrets
def create_app():
    app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

    app.secret_key = secrets.token_hex(16)
    app.register_blueprint(pages.bp)
    return app