import json

import pytest

from eventhub import catalog


def test_seed_loads_events_and_is_idempotent(conn, tmp_path):
    from conftest import EVENT_SEED
    first = catalog.load_seed(conn, EVENT_SEED)
    assert first == len(json.loads(EVENT_SEED.read_text())["events"]) > 0
    assert catalog.load_seed(conn, EVENT_SEED) == 0  # restart doesn't duplicate


def test_seed_does_not_reset_inventory(seeded):
    seeded.execute("UPDATE events SET tickets_available = 1 WHERE id = 1")
    from conftest import EVENT_SEED
    catalog.load_seed(seeded, EVENT_SEED)
    assert catalog.get_event(seeded, 1).tickets_available == 1


def test_seed_rejects_bad_data(conn, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"events": [{"name": "x", "artist": "a", "venue": "v", "city": "c",
                                           "starts_at": "2030-01-01T10:00", "base_price_usd": "-5", "capacity": 10}]}))
    with pytest.raises(ValueError):
        catalog.load_seed(conn, bad)


def test_prices_loaded_as_exact_cents(seeded):
    assert {e.base_price_cents for e in catalog.list_events(seeded)} >= {5550, 4825, 9999}


def test_browse_lists_all_events(seeded):
    assert len(catalog.list_events(seeded)) == 10


def test_search_by_artist_case_insensitive_substring(seeded):
    res = catalog.search(seeded, "artist", "luna")
    assert {e.artist for e in res.events} == {"Luna Vega"} and len(res.events) == 2
    assert not res.no_match


def test_search_by_venue(seeded):
    res = catalog.search(seeded, "venue", "ORPHEUM")
    assert len(res.events) == 2 and all(e.venue == "The Orpheum" for e in res.events)


def test_no_match_shows_message_and_full_list(seeded):
    res = catalog.search(seeded, "artist", "zzzz")
    assert res.no_match and res.message == catalog.NO_MATCH_MESSAGE
    assert len(res.events) == len(catalog.list_events(seeded))


def test_blank_search_returns_everything_without_message(seeded):
    res = catalog.search(seeded, "venue", "   ")
    assert not res.no_match and len(res.events) == 10


@pytest.mark.parametrize("text", ["%", "_", "' OR 1=1 --", "\\", "<script>"])
def test_search_treats_input_literally(seeded, text):
    res = catalog.search(seeded, "artist", text)
    assert res.no_match  # wildcards and SQL are not interpreted


def test_search_rejects_unknown_field(seeded):
    with pytest.raises(ValueError):
        catalog.search(seeded, "name; DROP TABLE events", "x")


def test_get_event(seeded):
    assert catalog.get_event(seeded, 1).name
    assert catalog.get_event(seeded, 9999) is None
    assert catalog.get_event(seeded, "abc") is None
