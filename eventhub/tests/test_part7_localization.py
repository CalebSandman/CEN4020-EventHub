"""Part 7 language configuration and top-level menu behavior."""
import re

from eventhub import database, identity
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


def test_admin_menu_stays_spanish_through_login(app, web):
    conn = database.connect(app.config["DATABASE_PATH"])
    identity.create_admin_user(conn, "Admin", "part7-admin@example.com", "admin-pass-123")
    conn.close()
    web.post("/locale", {"locale": "es_ES"})
    web.login("part7-admin@example.com", "admin-pass-123")
    menu = _header(web.get("/admin/"))
    assert ">Eventos</a>" in menu and ">Mis pedidos</a>" in menu
    assert ">Administración</a>" in menu and ">Cerrar sesión</button>" in menu


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
