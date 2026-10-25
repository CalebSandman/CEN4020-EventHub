"""Register / login / logout routes."""
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .. import identity
from .context import CSRF_KEY, CURRENCY_KEY, get_db
from .validation import clean_text

bp = Blueprint("auth", __name__)


def _rotate_session(user):
    """Fresh session on login (prevents fixation) keeping the chosen currency."""
    currency = session.get(CURRENCY_KEY)
    session.clear()
    if currency:
        session[CURRENCY_KEY] = currency
    identity.start_session(session, user)
    session.permanent = True


@bp.route("/register", methods=["GET", "POST"])
def register():
    next_url = identity.safe_next_url(request.values.get("next"))
    if request.method == "POST":
        try:
            user = identity.register_user(
                get_db(),
                clean_text(request.form.get("name"), 200),
                clean_text(request.form.get("email"), 300),
                (request.form.get("password") or "")[:500],
            )
        except identity.IdentityError as exc:
            flash(exc.message, "error")
            return render_template("register.html", next_url=next_url,
                                   form=request.form), 400
        _rotate_session(user)
        flash("Welcome to EventHub! Your account has been created.", "success")
        return redirect(next_url)
    return render_template("register.html", next_url=next_url, form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = identity.safe_next_url(request.values.get("next"))
    if request.method == "POST":
        user = identity.authenticate(
            get_db(), clean_text(request.form.get("email"), 300),
            (request.form.get("password") or "")[:500],
        )
        if user is None:
            flash("Invalid email or password.", "error")
            return render_template("login.html", next_url=next_url, form=request.form), 401
        _rotate_session(user)
        return redirect(next_url)  # back to the originally requested page
    if g.user is not None:
        return redirect(next_url)
    return render_template("login.html", next_url=next_url, form={})


@bp.post("/logout")
def logout():
    identity.end_session(session)
    session.pop(CSRF_KEY, None)
    flash("You have been logged out.", "success")
    return redirect(url_for("catalog.event_list"))
