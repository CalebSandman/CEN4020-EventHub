import importlib.util
from pathlib import Path


def load_checker():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'check_spec_alignment.py'
    spec = importlib.util.spec_from_file_location('alignment', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nested_code_without_spec_warns(monkeypatch):
    checker = load_checker()
    monkeypatch.setattr(checker, 'changed', lambda base: {'eventhub/eventhub/catalog.py'})
    assert checker.main(['--strict']) == 1


def test_nested_spec_update_satisfies_check(monkeypatch):
    checker = load_checker()
    monkeypatch.setattr(checker, 'changed', lambda base: {
        'eventhub/eventhub/catalog.py', 'eventhub/spec/requirements_ticket-purchasing.md'
    })
    assert checker.main(['--strict']) == 0


def test_old_application_does_not_trigger_check(monkeypatch):
    checker = load_checker()
    monkeypatch.setattr(checker, 'changed', lambda base: {'eventhub(old)/eventhub/catalog.py'})
    assert checker.main(['--strict']) == 0
