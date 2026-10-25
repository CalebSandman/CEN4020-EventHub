"""Browsing, searching, event detail, currency selection, double-click buy."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from .. import catalog, identity, pricing, purchasing
from .context import CURRENCY_KEY, get_db, session_currency
from .validation import clean_text

bp = Blueprint("catalog", __name__)


def price_label(conn, event, currency: str) -> str:
    quote = pricing.calculate_price(conn, event.base_price_cents, 1, False, currency)
    return pricing.format_money(quote.unit_minor, quote.currency, quote.decimals)


@bp.get("/")
def home():
    return redirect(url_for("catalog.event_list"))


@bp.get("/events")
def event_list():
    db = get_db()
    field = request.args.get("field", "artist")
    if field not in catalog.SEARCH_FIELDS:
        field = "artist"
    result = catalog.search(db, field, clean_text(request.args.get("q"), catalog.MAX_SEARCH_LENGTH))
    currency = session_currency(db)
    cards = [(e, price_label(db, e, currency)) for e in result.events]
    return render_template("events.html", result=result, cards=cards, field=field, currency=currency)


@bp.get("/events/<int:event_id>")
def event_detail(event_id):
    db = get_db()
    event = catalog.get_event(db, event_id)
    if event is None:
        abort(404)
    currency = session_currency(db)
    return render_template(
        "event_detail.html", event=event, currency=currency,
        price=price_label(db, event, currency), max_qty=purchasing.MAX_TICKETS_PER_ORDER,
    )


@bp.post("/currency")
def set_currency():
    """Select a currency; rejected unless it is on the server's supported list."""
    db = get_db()
    code = pricing.normalize_currency(clean_text(request.form.get("currency"), 10))
    if code in pricing.supported_currencies(db):
        session[CURRENCY_KEY] = code
    else:
        flash("That currency is not supported.", "error")
    return redirect(identity.safe_next_url(request.form.get("next"), url_for("catalog.event_list")))


@bp.post("/events/<int:event_id>/quick-buy")
def quick_buy(event_id):
    """Double-click on an event card: buy exactly one ticket (event-browsing-007).

    Goes through the same purchase path as normal checkout: validation,
    pricing, atomic inventory, audit. Unauthenticated users are sent to log in
    and nothing is created.
    """
    if g.user is None:
        return redirect(url_for(identity.LOGIN_ENDPOINT, next=url_for("catalog.event_detail", event_id=event_id)))
    db = get_db()
    try:
        order = purchasing.purchase(db, g.user, event_id, 1, session_currency(db))
    except purchasing.PurchaseError as exc:
        flash(exc.message, "error")
        return redirect(url_for("catalog.event_list"))
    flash("Your ticket has been purchased.", "success")
    return redirect(url_for("purchase.order_confirmation", order_id=order.id))
