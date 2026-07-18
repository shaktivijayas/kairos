from kairos import profile


def test_load_profile_returns_default_when_missing(tmp_path):
    path = str(tmp_path / "profile.json")
    result = profile.load_profile(path=path)
    assert result["tax_scheme"] == "regular"
    assert result["legal_business_name"] is None


def test_save_and_load_profile_roundtrip(tmp_path):
    path = str(tmp_path / "profile.json")
    data = {
        "legal_business_name": "Sharma Traders Pvt Ltd",
        "trade_style": "Sharma Traders",
        "business_category": "Retail",
        "tax_scheme": "composition",
    }
    profile.save_profile(data, path=path)
    assert profile.load_profile(path=path) == data


def test_save_profile_overwrites_existing(tmp_path):
    path = str(tmp_path / "profile.json")
    profile.save_profile({"tax_scheme": "regular"}, path=path)
    profile.save_profile({"tax_scheme": "composition"}, path=path)
    assert profile.load_profile(path=path)["tax_scheme"] == "composition"


def test_default_path_is_used_when_monkeypatched(tmp_path, monkeypatch):
    patched_path = str(tmp_path / "profile.json")
    monkeypatch.setattr(profile, "PROFILE_PATH", patched_path)
    profile.save_profile({"tax_scheme": "composition"})
    assert profile.load_profile()["tax_scheme"] == "composition"
