import pytest

from eventhub import audit, database
from test_app_routes import register_and_login


def test_unicode_csrf_is_rejected(web):
    assert web.post('/login', {'csrf_token': '\u00e9'}).status_code == 400


@pytest.mark.parametrize('path', ['/events/{identifier}', '/orders/{identifier}'])
def test_oversized_identifiers_are_not_found(web, path):
    register_and_login(web)
    assert web.get(path.format(identifier=2**80)).status_code == 404


@pytest.mark.parametrize('action', ['checkout', 'purchase', 'quick-buy'])
def test_anonymous_attempt_is_audited_once(app, web, action):
    if action == 'checkout':
        response = web.get('/events/1/checkout?quantity=1&currency=USD')
    else:
        response = web.post(f'/events/1/{action}', {'quantity': '1', 'currency': 'USD'})
    assert response.status_code == 302
    connection = database.connect(app.config['DATABASE_PATH'])
    try:
        records = audit.query(connection)
        assert len(records) == 1
        assert records[0].reason_code == 'NOT_AUTHENTICATED'
        assert records[0].user_id is None
        assert records[0].quantity == '1'
        assert records[0].currency == 'USD'
        assert connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0
        assert connection.execute('SELECT tickets_available FROM events WHERE id = 1').fetchone()[0] == 200
    finally:
        connection.close()


def test_oversized_purchase_identifier_is_audited(app, web):
    register_and_login(web)
    assert web.post(f'/events/{2**80}/purchase', {'quantity': '1', 'currency': 'USD'}).status_code == 302
    connection = database.connect(app.config['DATABASE_PATH'])
    try:
        record = audit.query(connection)[0]
        assert record.reason_code == 'EVENT_NOT_FOUND'
        assert record.event_name is None
    finally:
        connection.close()
