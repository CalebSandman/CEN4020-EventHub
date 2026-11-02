from eventhub.boundary.validation import clean_text


def test_clean_text():
    assert clean_text("  hi  ", 10) == "hi"
    assert clean_text("a\x00b\r\nc", 10) == "abc"
    assert clean_text("x" * 50, 5) == "xxxxx"
    assert clean_text(None, 5) == ""
    assert clean_text(123, 5) == "123"
