import app


class _DictResponseRibbonQuery:
    def __init__(self, payload):
        self.payload = payload

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return {"data": self.payload}


class _DictResponseSupabase:
    def __init__(self, payload):
        self.payload = payload

    def table(self, table_name):
        assert table_name == "ribbon_schedule"
        return _DictResponseRibbonQuery(self.payload)


def test_lookup_ribbon_accepts_dict_response_from_supabase(monkeypatch):
    monkeypatch.setattr(app, "supabase", _DictResponseSupabase({"color_name": "Cam"}))

    assert app.lookup_ribbon(1, 2026, 24) == "Cam"


def test_lookup_ribbon_accepts_empty_dict_response_from_supabase(monkeypatch):
    monkeypatch.setattr(app, "supabase", _DictResponseSupabase(None))

    assert app.lookup_ribbon(1, 2026, 24) is None
