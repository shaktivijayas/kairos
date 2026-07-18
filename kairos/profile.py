import json
import os

PROFILE_PATH = os.path.join("data", "profile.json")

DEFAULT_PROFILE = {
    "legal_business_name": None,
    "trade_style": None,
    "business_category": None,
    "tax_scheme": "regular",
}


def load_profile(path=None):
    p = path or PROFILE_PATH
    if not os.path.exists(p):
        return dict(DEFAULT_PROFILE)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(profile, path=None):
    p = path or PROFILE_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(profile, f)
