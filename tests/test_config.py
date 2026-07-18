import importlib


def test_default_cash_limit(monkeypatch):
    monkeypatch.delenv("CASH_LIMIT_INR", raising=False)
    from kairos import config
    importlib.reload(config)
    assert config.CASH_LIMIT_INR == 10000


def test_cash_limit_from_env(monkeypatch):
    monkeypatch.setenv("CASH_LIMIT_INR", "5000")
    from kairos import config
    importlib.reload(config)
    assert config.CASH_LIMIT_INR == 5000


def test_gemma_model_is_fixed():
    from kairos import config
    assert config.GEMMA_MODEL == "gemma-3-27b-it"
