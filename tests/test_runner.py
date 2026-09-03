def test_existing_event_schema(existing_event):
    assert set(existing_event) == {
        "date", "time", "name", "venue", "city", "category",
        "cost", "url", "source", "age", "featured", "new"
    }
