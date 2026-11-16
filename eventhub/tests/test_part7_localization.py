"""Part 7 language configuration and top-level menu behavior."""
import re
import json
from pathlib import Path

from eventhub import database, identity
from eventhub import localization
from eventhub.app import create_app


def _header(response):
    html = response.data.decode("utf-8")
    return re.search(r"<header class=\"site-header\">(.*?)</header>", html, re.S).group(1)


def test_guest_can_switch_both_languages_and_menu_follows(web):
    english = _header(web.get("/events"))
    assert 'aria-label="Main"' in english
    assert ">Events</a>" in english
    assert ">Log in</a>" in english and ">Sign up</a>" in english

    assert web.post("/locale", {"locale": "es_ES", "next": "/events"}).status_code == 302
    spanish = _header(web.get("/events"))
    assert 'aria-label="Principal"' in spanish
    assert ">Eventos</a>" in spanish
    assert ">Iniciar sesión</a>" in spanish and ">Registrarse</a>" in spanish
    assert '<option value="es_ES" selected>' in spanish

    assert web.post("/locale", {"locale": "en_US", "next": "/events"}).status_code == 302
    assert ">Events</a>" in _header(web.get("/events"))


def test_buyer_menu_stays_spanish_through_registration_navigation_and_logout(web):
    web.post("/locale", {"locale": "es_ES"})
    web.post("/register", {
        "name": "Buyer", "email": "part7-buyer@example.com", "password": "buyer-pass-123"
    })
    for path in ("/events", "/orders"):
        menu = _header(web.get(path))
        assert ">Eventos</a>" in menu and ">Mis pedidos</a>" in menu
        assert ">Cerrar sesión</button>" in menu
        assert ">Admin</a>" not in menu
    web.post("/logout")
    assert ">Iniciar sesión</a>" in _header(web.get("/events"))
    web.login("part7-buyer@example.com", "buyer-pass-123")
    web.post("/locale", {"locale": "en_US"})
    english = _header(web.get("/orders"))
    assert ">Events</a>" in english and ">My orders</a>" in english
    assert ">Log out</button>" in english


def test_admin_menu_stays_spanish_through_login(app, web):
    conn = database.connect(app.config["DATABASE_PATH"])
    identity.create_admin_user(conn, "Admin", "part7-admin@example.com", "admin-pass-123")
    conn.close()
    web.post("/locale", {"locale": "es_ES"})
    web.login("part7-admin@example.com", "admin-pass-123")
    menu = _header(web.get("/admin/"))
    assert ">Eventos</a>" in menu and ">Mis pedidos</a>" in menu
    assert ">Administración</a>" in menu and ">Cerrar sesión</button>" in menu
    web.post("/locale", {"locale": "en_US"})
    english = _header(web.get("/admin/"))
    assert ">Events</a>" in english and ">My orders</a>" in english
    assert ">Admin</a>" in english and ">Log out</button>" in english


def test_configured_default_and_invalid_locale_fallback(db_path, monkeypatch):
    monkeypatch.setenv("EVENTHUB_DEFAULT_LOCALE", "es_ES")
    app = create_app({
        "TESTING": True, "DATABASE_PATH": str(db_path), "SECRET_KEY": "part7-test",
        "CSRF_ENABLED": False,
    })
    client = app.test_client()
    spanish = client.get("/events").data.decode("utf-8")
    assert '<html lang="es">' in spanish and ">Eventos</a>" in spanish
    client.post("/locale", data={"locale": "unsupported", "next": "/events"})
    assert ">Eventos</a>" in client.get("/events").data.decode("utf-8")
    client.post("/locale", data={"locale": "en_US", "next": "/events"})
    assert ">Events</a>" in client.get("/events").data.decode("utf-8")

    app.config["DEFAULT_LOCALE"] = "unsupported"
    fresh = app.test_client()
    assert ">Events</a>" in fresh.get("/events").data.decode("utf-8")


def test_spanish_dynamic_validation_messages_and_english_service_values(web):
    web.post("/locale", {"locale": "es_ES"})
    short = web.post("/register", {
        "name": "Buyer", "email": "part7-short@example.com", "password": "short",
    }).data.decode("utf-8")
    assert "La contraseña debe tener al menos 8 caracteres." in short
    assert localization.translate("Password must be at least 8 characters.") == (
        "Password must be at least 8 characters."
    )
    web.post("/register", {
        "name": "Buyer", "email": "part7-valid@example.com", "password": "long-enough",
    })
    page = web.post("/events/1/purchase", {
        "quantity": "11", "currency": "USD",
    }, follow_redirects=True).data.decode("utf-8")
    assert "Puede comprar como máximo 10 entradas por pedido." in page


def test_every_static_template_translation_has_spanish_text():
    templates = Path(__file__).resolve().parents[1] / "eventhub" / "templates"
    keys = set()
    for template in templates.glob("*.html"):
        keys.update(re.findall(r"\btr\('([^']+)'\)", template.read_text(encoding="utf-8")))
    resources = Path(localization.RESOURCES)
    translated = set()
    for name in ("es_ES.json", "es_ES_errors.json"):
        translated.update(json.loads((resources / name).read_text(encoding="utf-8")))
    missing = sorted(keys - translated)
    assert not missing
