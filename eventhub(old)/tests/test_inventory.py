import pytest

from conftest import make_event
from eventhub import inventory


def test_available(conn):
    eid = make_event(conn, capacity=7)
    assert inventory.available(conn, eid) == 7
    assert inventory.available(conn, 999) is None


def test_reserve_decrements(conn):
    eid = make_event(conn, capacity=5)
    assert inventory.reserve(conn, eid, 2) is True
    assert inventory.available(conn, eid) == 3


def test_reserve_exact_remaining_then_none_left(conn):
    eid = make_event(conn, capacity=2)
    assert inventory.reserve(conn, eid, 2)
    assert inventory.available(conn, eid) == 0
    assert inventory.reserve(conn, eid, 1) is False


def test_reserve_more_than_available_changes_nothing(conn):
    eid = make_event(conn, capacity=3)
    assert inventory.reserve(conn, eid, 4) is False
    assert inventory.available(conn, eid) == 3


def test_reserve_unknown_event(conn):
    assert inventory.reserve(conn, 12345, 1) is False


@pytest.mark.parametrize("qty", [0, -1, True, "1", 1.0])
def test_reserve_rejects_bad_quantity(conn, qty):
    eid = make_event(conn)
    with pytest.raises(ValueError):
        inventory.reserve(conn, eid, qty)
