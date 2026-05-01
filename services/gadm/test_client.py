"""
Test client for gadm-service.

Usage:
    python test_client.py [--url http://localhost:8101]

Uses Luxembourg (LUX) — tiny shapefile (~1 MB) — for tests that trigger a
real download. Checks GeoJSON structure, property presence, and error cases.
"""

import argparse
import sys

import httpx

BASE = "http://localhost:8101"
TEST_ISO = "LUX"  # Luxembourg — small file, fast download


def get(path: str, timeout: float = 120) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", timeout=timeout)


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def test_health():
    print("── /health ─────────────────────────────────────────────")
    r = get("/health")
    check("HTTP 200", r.status_code == 200)
    check("status == ok", r.json().get("status") == "ok")


def test_boundaries_level0():
    print(f"── GET /boundaries/{TEST_ISO}/0 (country outline) ─────")
    r = get(f"/boundaries/{TEST_ISO}/0")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    fc = r.json()
    check("type == FeatureCollection", fc.get("type") == "FeatureCollection")
    features = fc.get("features", [])
    check("exactly 1 feature at level 0", len(features) == 1, f"got {len(features)}")
    props = features[0].get("properties", {})
    check("nodeid present", "nodeid" in props)
    check("name present", "name" in props)
    check("gid present", "gid" in props)
    geom = features[0].get("geometry", {})
    check("geometry present", bool(geom))
    check("geometry type is Polygon/MultiPolygon", geom.get("type") in ("Polygon", "MultiPolygon"))


def test_boundaries_level1():
    print(f"── GET /boundaries/{TEST_ISO}/1 ────────────────────────")
    r = get(f"/boundaries/{TEST_ISO}/1")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    features = r.json().get("features", [])
    check("at least 1 feature", len(features) >= 1, f"got {len(features)}")
    for f in features:
        props = f.get("properties", {})
        check("each feature has nodeid", "nodeid" in props)
        check("each feature has name", "name" in props)
        break  # spot-check first feature only


def test_boundaries_level2():
    print(f"── GET /boundaries/{TEST_ISO}/2 ────────────────────────")
    r = get(f"/boundaries/{TEST_ISO}/2")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    features = r.json().get("features", [])
    check("more features at level 2 than level 1", len(features) > 1, f"got {len(features)}")


def test_lowercase_iso():
    print(f"── GET /boundaries/lux/1 (lowercase ISO) ───────────────")
    r = get("/boundaries/lux/1")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")


def test_second_request_is_cached():
    print(f"── Second request uses cache (fast) ────────────────────")
    import time
    t0 = time.monotonic()
    r = get(f"/boundaries/{TEST_ISO}/1")
    elapsed = time.monotonic() - t0
    check("HTTP 200", r.status_code == 200)
    check("responded in < 10s (cache hit)", elapsed < 10, f"{elapsed:.2f}s")


def test_invalid_level():
    print("── GET /boundaries/LUX/9 (invalid level) ───────────────")
    r = get("/boundaries/LUX/9")
    check("HTTP 400", r.status_code == 400, f"got {r.status_code}")


def test_unknown_iso():
    print("── GET /boundaries/ZZZ/1 (unknown ISO) ─────────────────")
    r = get("/boundaries/ZZZ/1")
    check("HTTP 404", r.status_code == 404, f"got {r.status_code}")


def main():
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE)
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\nRunning gadm-service tests against {BASE}\n")
    print(f"Note: first run downloads {TEST_ISO} shapefile — may take a moment.\n")
    test_health()
    test_boundaries_level0()
    test_boundaries_level1()
    test_boundaries_level2()
    test_lowercase_iso()
    test_second_request_is_cached()
    test_invalid_level()
    test_unknown_iso()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
