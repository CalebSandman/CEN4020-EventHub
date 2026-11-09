"""HTTP Boundary component: Flask blueprints, CSRF, safe rendering, error pages.

All request-level concerns live here; business rules live in the components.
"""
from __future__ import annotations

import hmac
from datetime import timedelta

from flask import abort, current_app, g, render_template, request, session

from .. import identity, localization, pricing
from . import admin_routes, auth_routes, catalog_routes, purchase_routes
from .context import CSRF_KEY, csrf_token, get_db, session_currency, session_locale

_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def _format_dt(value: str) -> str:
    return localization.format_date(value, session_locale())


def _money(minor, currency, decimals) -> str:
    return localization.format_money(minor, currency, decimals, session_locale())


def register_boundary(app) -> None:
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(catalog_routes.bp)
    app.register_blueprint(purchase_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.jinja_env.filters["dt"] = _format_dt
    app.jinja_env.filters["money"] = _money

    @app.before_request
    def _load_user_and_check_csrf():
        g.user = identity.load_session_user(
            get_db(), session,
            lifetime=timedelta(minutes=current_app.config["SESSION_LIFETIME_MINUTES"]),
        )
        if request.method in _UNSAFE and current_app.config["CSRF_ENABLED"]:
            sent = request.form.get("csrf_token", "")
            expected = session.get(CSRF_KEY, "")
            if not expected or not hmac.compare_digest(str(sent).encode("utf-8"), str(expected).encode("utf-8")):
                abort(400, description="Invalid or missing CSRF token.")

    @app.teardown_request
    def _close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def _template_globals():
        db = get_db()
        return {
            "current_user": getattr(g, "user", None),
            "csrf_token": csrf_token,
            "supported_currencies": pricing.supported_currencies(db),
            "active_currency": session_currency(db),
            "active_locale": session_locale(),
            "locales": localization.LOCALES,
            "tr": lambda message: localization.translate(message, session_locale()),
            "currency_decimals": lambda code: pricing.load_currencies(db)[code].decimals,
        }

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        # Pages with personal or purchase data must not be cached or stored.
        if request.path.startswith(("/orders", "/admin")) or "/checkout" in request.path:
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def _error(code, title, text):
        def handler(err):
            desc = getattr(err, "description", None) if code == 400 else None
            return render_template("error.html", code=code, title=title, text=desc or text), code
        return handler

    app.register_error_handler(400, _error(400, "Bad request", "The request could not be processed."))
    app.register_error_handler(403, _error(403, "Access denied", "You do not have permission to view this page."))
    app.register_error_handler(404, _error(404, "Not found", "We could not find that page."))
    app.register_error_handler(405, _error(405, "Method not allowed", "That action is not allowed here."))
    app.register_error_handler(413, _error(413, "Request too large", "The request was too large."))
    app.register_error_handler(500, _error(500, "Server error", "Something went wrong on our side."))
