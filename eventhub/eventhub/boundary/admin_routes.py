"""Administrator-only routes. Thin adapter over ``administration``."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import administration, audit, identity
from .context import get_db
from .validation import clean_text

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def _admin_only():
    """Runs for every /admin route: login required, then administrator role."""
    if g.user is None:
        return redirect(url_for(identity.LOGIN_ENDPOINT, next=request.path if request.method == "GET" else "/"))
    if not identity.has_role(g.user, identity.ROLE_ADMIN):
        abort(403)


@bp.get("/")
def dashboard():
    return render_template("admin_dashboard.html")


@bp.route("/rates", methods=["GET", "POST"])
def rates():
    db = get_db()
    if request.method == "POST":
        try:
            administration.update_rate(
                db, g.user, clean_text(request.form.get("currency"), 10),
                clean_text(request.form.get("rate"), 40),
            )
            flash("Exchange rate updated.", "success")
        except administration.AdminError as exc:
            flash(exc.message, "error")
        return redirect(url_for("admin.rates"))
    return render_template("admin_rates.html", rates=administration.list_rates(db, g.user))


@bp.get("/audit")
def audit_log():
    outcome = clean_text(request.args.get("outcome"), 10)
    if outcome not in audit.OUTCOMES:
        outcome = ""
    records = administration.review_audit(
        get_db(), g.user, outcome=outcome,
        user_email=clean_text(request.args.get("email"), 100),
        reason_code=clean_text(request.args.get("reason"), 40),
    )
    return render_template("admin_audit.html", records=records, outcome=outcome,
                           email=clean_text(request.args.get("email"), 100),
                           reason=clean_text(request.args.get("reason"), 40))
