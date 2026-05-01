"""
Test client for worldpop-service.

Usage:
    python test_client.py [--url http://localhost:8104] [--wait]

The service downloads WorldPop constrained rasters on demand. Use --wait to
poll /health before running tests. The first run for a new ISO downloads the
raster (seconds to minutes depending on country size).
"""

import argparse
import sys
import time

import httpx

BASE = "http://localhost:8104"
TEST_ISO = "LUX"  # Luxembourg — small country, small raster (~1 MB)

# Bounding box polygon covering Luxembourg (WGS84)
_LUX_RING = [[5.7, 49.4], [6.5, 49.4], [6.5, 50.2], [5.7, 50.2], [5.7, 49.4]]
TEST_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"nodeid": 0, "name": "Luxembourg"},
            "geometry": {"type": "Polygon", "coordinates": [_LUX_RING]},
        }
    ],
}


def get(path: str, timeout: float = 30) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", timeout=timeout)


def post(path: str, body: dict, timeout: float = 120) -> httpx.Response:
    return httpx.post(f"{BASE}{path}", json=body, timeout=timeout)


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def wait_for_ready(timeout_s: int = 120) -> None:
    print(f"Waiting for service to be ready (up to {timeout_s}s) ...")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{BASE}/health", timeout=5)
            if r.status_code == 200:
                print("  Service ready.\n")
                return
        except Exception:
            print("  Service not yet reachable — waiting ...")
        time.sleep(5)
    print("  TIMED OUT waiting for service")
    sys.exit(1)


def test_health():
    print("── /health ─────────────────────────────────────────────")
    r = get("/health")
    check("HTTP 200", r.status_code == 200)
    body = r.json()
    check("status == ok", body.get("status") == "ok", str(body))


def test_prewarm():
    print(f"── POST /prewarm/{TEST_ISO} (downloads raster) ─────────")
    r = post(f"/prewarm/{TEST_ISO}", {}, timeout=600)
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    body = r.json()
    check("status == ok", body.get("status") == "ok", str(body))
    check("iso present", "iso" in body)
    check("year present", "year" in body)


def test_aggregate():
    print(f"── POST /aggregate/{TEST_ISO} ─────────────────────────")
    r = post(f"/aggregate/{TEST_ISO}", TEST_GEOJSON, timeout=60)
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}")
    result = r.json()
    check("nodeid 0 in result", "0" in result, str(list(result.keys())[:5]))
    pop = result["0"]
    check("population > 100_000", pop > 100_000, f"got {pop:.0f}")
    check("population < 1_500_000", pop < 1_500_000, f"got {pop:.0f}")


def test_cache_speed():
    print(f"── Second /aggregate/{TEST_ISO} uses cached raster ─────")
    t0 = time.monotonic()
    r = post(f"/aggregate/{TEST_ISO}", TEST_GEOJSON, timeout=60)
    elapsed = time.monotonic() - t0
    check("HTTP 200", r.status_code == 200)
    check("responded in < 10s (cached raster)", elapsed < 10, f"{elapsed:.2f}s")


def test_unknown_iso():
    print("── POST /aggregate/ZZZ (unknown ISO) ────────────────────")
    r = post("/aggregate/ZZZ", TEST_GEOJSON, timeout=60)
    check("HTTP 404", r.status_code == 404, f"got {r.status_code}")


def test_bad_body():
    print("── POST /aggregate with non-FeatureCollection body ──────")
    r = post(f"/aggregate/{TEST_ISO}", {"type": "Point", "coordinates": [6.1, 49.8]}, timeout=30)
    check("HTTP 400", r.status_code == 400, f"got {r.status_code}")


def test_empty_features():
    print("── POST /aggregate with empty features array ─────────────")
    r = post(f"/aggregate/{TEST_ISO}", {"type": "FeatureCollection", "features": []}, timeout=30)
    check("HTTP 400", r.status_code == 400, f"got {r.status_code}")


def main():
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE)
    parser.add_argument("--wait", action="store_true",
                        help="Wait for service to be ready before running tests")
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\nRunning worldpop-service tests against {BASE}\n")
    if args.wait:
        wait_for_ready()

    test_health()
    test_prewarm()
    test_aggregate()
    test_cache_speed()
    test_unknown_iso()
    test_bad_body()
    test_empty_features()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
