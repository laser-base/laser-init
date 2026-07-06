"""
Test client for unwpp-service.

Usage:
    python test_client.py [--url http://localhost:8100]

Runs a series of checks against a live unwpp-service instance:
  - /health responds OK
  - /demographics returns expected shape and value ranges
  - Edge cases: unknown ISO, inverted year range, boundary years
"""

import argparse
import sys

import httpx

BASE = "http://localhost:8100"


def get(path: str, **params) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", params=params, timeout=30)


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def test_health():
    print("── /health ─────────────────────────────────────────────")
    r = get("/health")
    check("HTTP 200", r.status_code == 200)
    body = r.json()
    check("status == ok", body.get("status") == "ok")
    loaded = body.get("loaded", [])
    for key in ("age_dist", "indicators", "life_1950", "life_2024"):
        check(f"dataset loaded: {key}", key in loaded)


def test_demographics_basic():
    print("── GET /demographics/NGA (2000–2025) ───────────────────")
    r = get("/demographics/NGA", start_year=2000, end_year=2025)
    check("HTTP 200", r.status_code == 200)
    body = r.json()
    check("iso == NGA", body["iso"] == "NGA")

    cxr = body["cxr"]
    check("cxr has 26 rows", len(cxr) == 26, f"got {len(cxr)}")
    check("cxr first year == 2000", cxr[0]["year"] == 2000)
    check("cxr last year == 2025", cxr[-1]["year"] == 2025)
    check("CBR > 0", all(row["CBR"] > 0 for row in cxr))
    check("CDR > 0", all(row["CDR"] > 0 for row in cxr))

    age_dist = body["age_dist"]
    check("age_dist non-empty", len(age_dist) > 0, f"got {len(age_dist)}")
    check("age_dist has age_start=0", any(r["age_start"] == 0 for r in age_dist))
    check("age_dist pop_total > 0", all(r["pop_total"] > 0 for r in age_dist))

    life_exp = body["life_exp"]
    check("life_exp non-empty", len(life_exp) > 0, f"got {len(life_exp)}")
    check("life_exp has age=0", any(r["age"] == 0 for r in life_exp))
    check("life_exp cumulative_deaths >= 0", all(r["cumulative_deaths"] >= 0 for r in life_exp))


def test_demographics_lowercase_iso():
    print("── GET /demographics/nga (lowercase ISO) ───────────────")
    r = get("/demographics/nga", start_year=2010, end_year=2010)
    check("HTTP 200 (normalised to uppercase)", r.status_code == 200)
    check("iso == NGA", r.json()["iso"] == "NGA")


def test_single_year():
    print("── GET /demographics/ETH (start_year == end_year) ──────")
    r = get("/demographics/ETH", start_year=2015, end_year=2015)
    check("HTTP 200", r.status_code == 200)
    cxr = r.json()["cxr"]
    check("cxr has exactly 1 row", len(cxr) == 1, f"got {len(cxr)}")


def test_future_years():
    print("── GET /demographics/IND (2030–2050) ───────────────────")
    r = get("/demographics/IND", start_year=2030, end_year=2050)
    check("HTTP 200", r.status_code == 200)
    cxr = r.json()["cxr"]
    check("cxr has 21 rows", len(cxr) == 21, f"got {len(cxr)}")
    life_exp = r.json()["life_exp"]
    check("life_exp uses 2024 file", len(life_exp) > 0)


def test_unknown_iso():
    print("── GET /demographics/ZZZ (unknown ISO) ─────────────────")
    r = get("/demographics/ZZZ", start_year=2000, end_year=2010)
    check("HTTP 404", r.status_code == 404, f"got {r.status_code}")


def test_inverted_years():
    print("── GET /demographics/NGA (start > end) ─────────────────")
    r = get("/demographics/NGA", start_year=2025, end_year=2000)
    check("HTTP 400", r.status_code == 400, f"got {r.status_code}")


def main():
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE)
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\nRunning unwpp-service tests against {BASE}\n")
    test_health()
    test_demographics_basic()
    test_demographics_lowercase_iso()
    test_single_year()
    test_future_years()
    test_unknown_iso()
    test_inverted_years()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
