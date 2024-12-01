from flask import Flask
from extensions import db, migrate, cors
from routes.auth import auth_bp
from routes.motor import motor_bp
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(motor_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)