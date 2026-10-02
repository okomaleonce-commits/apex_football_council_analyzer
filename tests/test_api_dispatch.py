"""Tests d'intégration de l'API : dispatch football / hockey / hors-domaine."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _payload(**overrides):
    base = {
        "match_date": "2026-10-01",
        "country": "USA",
        "league": "NHL",
        "home": "Edmonton Oilers",
        "away": "Vancouver Canucks",
    }
    base.update(overrides)
    return base


def test_hockey_request_uses_hockey_engine():
    resp = client.post("/api/analyze", json=_payload(sport="hockey"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_pack_summary"]["sport"] == "hockey"
    assert "moneyline_home" in body["probabilities"]
    # Sans cote branchée + début de saison : jamais de BET.
    assert body["final_verdict"] in {"NO_BET", "WAIT_DATA", "MONITOR_LIVE"}


def test_out_of_domain_sport_returns_no_model():
    resp = client.post("/api/analyze", json=_payload(sport="basketball"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_verdict"] == "NO_MODEL"
    assert "football" in body["supported_sports"] and "hockey" in body["supported_sports"]


def test_football_default_still_works():
    resp = client.post("/api/analyze", json=_payload(
        home="Arsenal", away="Chelsea", country="England", league="Premier League"
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert "home_win" in body["probabilities"]  # forme football


def test_sports_endpoint_lists_calibrated_engines():
    resp = client.get("/api/sports")
    assert resp.status_code == 200
    keys = {s["key"] for s in resp.json()["sports"]}
    assert {"football", "hockey"} <= keys


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    raise SystemExit(1 if failed else 0)
