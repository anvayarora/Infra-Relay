from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from .api.routes import api
from .resource_types import resource_types_api
from .config import config
from .engine import runtime
from .extensions import db, jwt
from .seed import seed


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.secret_key,
        JWT_SECRET_KEY=config.jwt_secret_key,
        SQLALCHEMY_DATABASE_URI=config.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        JWT_TOKEN_LOCATION=["headers", "query_string"],
        JWT_QUERY_STRING_NAME="access_token",
        SEED_DATA=False,
        REQUEUE_EXECUTIONS=True,
    )
    if test_config:
        app.config.update(test_config)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [origin.strip() for origin in config.cors_origins.split(",") if origin.strip()]
            }
        },
    )
    db.init_app(app)
    jwt.init_app(app)
    app.register_blueprint(api)
    app.register_blueprint(resource_types_api)
    runtime.bind(app)

    @app.get("/")
    def index():
        return {
            "name": "InfraRelay HITL IaaS Runtime",
            "api": "/api/v1",
            "health": "/api/v1/health",
        }

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Not found"), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled request error", exc_info=error)
        return jsonify(error="Internal server error"), 500

    with app.app_context():
        db.create_all()
        if app.config.get("SEED_DATA", True):
            seed()
        if app.config.get("REQUEUE_EXECUTIONS", True):
            from .models import Execution

            pending = Execution.query.filter(Execution.status.in_(["queued", "running"])).all()
            for execution in pending:
                execution.status = "queued"
            db.session.commit()
            for execution in pending:
                runtime.submit(execution.id)

    return app
