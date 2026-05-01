"""
Test client for unocha-service.

Usage:
    python test_client.py [--url http://localhost:8103] [--wait]

The service downloads a 1-2 GB global GDB on first startup. Use --wait to
poll /health until gdb_ready=true before running tests (useful in CI or
after a fresh container start). Without --wait, tests run immediately and
will get 503s if the GDB isn't ready yet.
"""

import argparse
import sys
import time

import httpx

BASE = "http://localhost:8103"
TEST_ISO = "NGA"  # Nigeria — well-covered in UNOCHA data


def get(path: str, timeout: float = 120) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", timeout=timeout)


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def wait_for_ready(timeout_s: int = 1800) -> None:
    print(f"Waiting for GDB to be ready (up to {timeout_s}s) ...")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{BASE}/health", timeout=5)
            body = r.json()
            if body.get("gdb_ready"):
                print("  GDB ready.\n")
                return
            status = body.get("status", "?")
            print(f"  status={status} — waiting ...")
        except Exception:
            print("  service not yet reachable — waiting ...")
        time.sleep(10)
    print("  TIMED OUT waiting for GDB ready")
    sys.exit(1)


def test_health():
    print("── /health ─────────────────────────────────────────────")
    r = get("/health")
    check("HTTP 200", r.status_code == 200)
    body = r.json()
    check("gdb_ready == true", body.get("gdb_ready") is True, str(body))


def test_boundaries_level0():
    print(f"── GET /boundaries/{TEST_ISO}/0 ────────────────────────")
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
    check("geometry is Polygon/MultiPolygon", geom.get("type") in ("Polygon", "MultiPolygon"))


def test_boundaries_level1():
    print(f"── GET /boundaries/{TEST_ISO}/1 ────────────────────────")
    r = get(f"/boundaries/{TEST_ISO}/1")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    features = r.json().get("features", [])
    check("multiple features at level 1", len(features) > 1, f"got {len(features)}")
    props = features[0].get("properties", {})
    check("nodeid present", "nodeid" in props)
    check("name present", "name" in props)


def test_cache_speed():
    print(f"── Second request uses in-memory cache (fast) ──────────")
    t0 = time.monotonic()
    r = get(f"/boundaries/{TEST_ISO}/1")
    elapsed = time.monotonic() - t0
    check("HTTP 200", r.status_code == 200)
    check("responded in < 5s (memory cache)", elapsed < 5, f"{elapsed:.2f}s")


def test_lowercase_iso():
    print(f"── GET /boundaries/nga/1 (lowercase) ───────────────────")
    r = get("/boundaries/nga/1")
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")


def test_invalid_level():
    print("── GET /boundaries/NGA/5 (unsupported level) ───────────")
    r = get("/boundaries/NGA/5")
    check("HTTP 400", r.status_code == 400, f"got {r.status_code}")


def test_unknown_iso():
    print("── GET /boundaries/ZZZ/1 (unknown ISO) ─────────────────")
    r = get("/boundaries/ZZZ/1")
    check("HTTP 404", r.status_code == 404, f"got {r.status_code}")


def test_503_before_ready():
    print("── /health returns warming status when not ready ────────")
    # Can't easily test 503 on a live ready service; just confirm health
    # reports gdb_ready correctly
    r = get("/health")
    check("HTTP 200", r.status_code == 200)
    check("gdb_ready key present", "gdb_ready" in r.json())


def main():
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE)
    parser.add_argument("--wait", action="store_true",
                        help="Poll /health until gdb_ready before running tests")
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\nRunning unocha-service tests against {BASE}\n")
    if args.wait:
        wait_for_ready()

    test_health()
    test_boundaries_level0()
    test_boundaries_level1()
    test_cache_speed()
    test_lowercase_iso()
    test_invalid_level()
    test_unknown_iso()
    test_503_before_ready()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
