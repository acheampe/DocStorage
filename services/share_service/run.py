from flask import Flask
from flask_cors import CORS
from app.models.share import db
from app.routes.shares import shares
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

app.register_blueprint(shares, url_prefix='/share')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3004)
