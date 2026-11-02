"""Checkout, mock payment, order history and confirmation."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import identity, purchasing
from .context import get_db
from .validation import clean_text

bp = Blueprint("purchase", __name__)


@bp.before_request
def audit_anonymous_attempt():
    if g.user is None and request.endpoint in {"purchase.checkout", "purchase.purchase"}:
        source = request.args if request.method == "GET" else request.form
        quantity, currency = _form_values(source)
        purchasing.record_unauthenticated_attempt(
            get_db(), request.view_args["event_id"], quantity, currency
        )


def _form_values(source):
    return clean_text(source.get("quantity"), 32), clean_text(source.get("currency"), 10)


@bp.get("/events/<int:event_id>/checkout")
@identity.login_required
def checkout(event_id):
    """Summary of quantity, currency, event and total. Nothing is stored or held."""
    quantity, currency = _form_values(request.args)
    try:
        preview = purchasing.preview_checkout(get_db(), g.user, event_id, quantity, currency)
    except purchasing.PurchaseError as exc:
        if exc.code == purchasing.EVENT_NOT_FOUND:
            abort(404)
        flash(exc.message, "error")
        return redirect(url_for("catalog.event_detail", event_id=event_id))
    return render_template("checkout.html", preview=preview)


@bp.post("/events/<int:event_id>/purchase")
@identity.login_required
def purchase(event_id):
    quantity, currency = _form_values(request.form)
    try:
        order = purchasing.purchase(get_db(), g.user, event_id, quantity, currency)
    except purchasing.PurchaseError as exc:
        flash(exc.message, "error")
        return redirect(url_for("catalog.event_detail", event_id=event_id))
    flash("Purchase complete. This confirmation is shown on screen only; no email is sent.", "success")
    return redirect(url_for("purchase.order_confirmation", order_id=order.id))


@bp.get("/orders")
@identity.login_required
def order_history():
    return render_template("orders.html", orders=purchasing.list_orders(get_db(), g.user))


@bp.get("/orders/<int:order_id>")
@identity.login_required
def order_confirmation(order_id):
    order = purchasing.get_order(get_db(), g.user, order_id)
    if order is None:
        abort(404)
    return render_template("order.html", order=order)
