"""Tests du moteur hockey et de la garde hors-domaine.

Exécuter : `pytest tests/` ou `python tests/test_hockey.py` (runner intégré).
"""

from __future__ import annotations

from app.core.hockey import compute_probabilities, estimate_lambdas
from app.core.sports import OutOfDomainError, assert_supported, check_domain


def test_moneyline_sums_to_one():
    p = compute_probabilities(3.2, 2.8)
    s = p["moneyline_home"] + p["moneyline_away"]
    assert abs(s - 1.0) < 1e-3, f"moneyline doit sommer à 1, obtenu {s}"


def test_regulation_three_way_sums_to_one():
    p = compute_probabilities(3.0, 3.0)
    s = p["regulation_home"] + p["regulation_tie"] + p["regulation_away"]
    assert abs(s - 1.0) < 1e-3, s


def test_totals_over_under_sum_to_one():
    p = compute_probabilities(3.1, 2.9)
    for line, book in p["totals"].items():
        s = book["over"] + book["under"]
        assert abs(s - 1.0) < 1e-3, f"ligne {line}: {s}"


def test_home_ice_edge_favours_home_when_symmetric():
    # Mêmes buts pour/contre : l'avantage de la glace doit pencher côté domicile.
    lh, la = estimate_lambdas(3.0, 3.0, 3.0, 3.0)
    assert lh > la, (lh, la)
    p = compute_probabilities(lh, la)
    assert p["moneyline_home"] > p["moneyline_away"]


def test_expected_total_in_nhl_range():
    lh, la = estimate_lambdas(None, None, None, None)
    total = lh + la
    assert 5.5 <= total <= 6.7, f"total attendu hors plage NHL: {total}"


def test_stronger_team_has_higher_ot_share():
    p = compute_probabilities(3.6, 2.6)
    assert p["overtime_home_share"] > 0.5


def test_puckline_consistency():
    p = compute_probabilities(3.3, 2.7)
    assert abs((p["puckline_home_minus_1_5"] + p["puckline_away_plus_1_5"]) - 1.0) < 1e-3


def test_guard_supports_football_and_hockey():
    assert check_domain("football").supported
    assert check_domain("hockey").supported
    assert check_domain("HOCKEY").supported  # casse insensible


def test_guard_blocks_uncalibrated_sport():
    check = check_domain("basketball")
    assert not check.supported
    assert check.verdict == "NO_MODEL"
    try:
        assert_supported("basketball")
    except OutOfDomainError as exc:
        assert exc.sport == "basketball"
    else:
        raise AssertionError("assert_supported aurait dû lever OutOfDomainError")


def test_guard_defaults_to_football():
    assert assert_supported(None) == "football"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    raise SystemExit(1 if failed else 0)
