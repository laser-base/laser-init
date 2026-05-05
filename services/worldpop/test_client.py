"""
Test client for worldpop-service.

Usage:
    python test_client.py [--url http://localhost:8104] [--wait]
    python test_client.py --url http://4.155.140.158 --large-country BRA

The service downloads WorldPop rasters on demand. Use --wait to poll /health
before running tests. The first run for a new ISO downloads the raster.

Default ISO is LUX (Luxembourg, ~1 MB raster — fast, always downloaded on demand).
Pass --large-country to also test a large pre-warmed country (e.g. BRA, NGA).
"""

import argparse
import sys
import time

import httpx

BASE = "http://localhost:8104"
TEST_ISO = "LUX"

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

# Simple 4-polygon GeoJSON for NGA that exercises the multi-polygon path
# (bounding boxes of 4 rough quadrants of Nigeria, WGS84)
_NGA_QUADS = [
    {"nodeid": 0, "name": "NW",  "ring": [[3.0,9.5],[9.5,9.5],[9.5,14.0],[3.0,14.0],[3.0,9.5]]},
    {"nodeid": 1, "name": "NE",  "ring": [[9.5,9.5],[15.0,9.5],[15.0,14.0],[9.5,14.0],[9.5,9.5]]},
    {"nodeid": 2, "name": "SW",  "ring": [[3.0,4.0],[9.5,4.0],[9.5,9.5],[3.0,9.5],[3.0,4.0]]},
    {"nodeid": 3, "name": "SE",  "ring": [[9.5,4.0],[15.0,4.0],[15.0,9.5],[9.5,9.5],[9.5,4.0]]},
]
NGA_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"nodeid": q["nodeid"], "name": q["name"]},
            "geometry": {"type": "Polygon", "coordinates": [q["ring"]]},
        }
        for q in _NGA_QUADS
    ],
}


def get(path: str, timeout: float = 30) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", timeout=timeout)


def post(path: str, body: dict, timeout: float = 300) -> httpx.Response:
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
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
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


def test_nga_multipolygon():
    print("── POST /aggregate/NGA (4 quads, multi-polygon) ─────────")
    t0 = time.monotonic()
    r = post("/aggregate/NGA", NGA_GEOJSON, timeout=120)
    elapsed = time.monotonic() - t0
    check("HTTP 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    result = r.json()
    check("4 nodeids returned", len(result) == 4, f"got {len(result)}: {list(result.keys())}")
    total = sum(result.values())
    check("total NGA pop plausible (150M–230M)", 150_000_000 < total < 230_000_000,
          f"got {total:.0f}")
    check("each quad > 0", all(v > 0 for v in result.values()),
          str({k: f"{v:.0f}" for k, v in result.items()}))
    print(f"  Quads: { {k: f'{v/1e6:.1f}M' for k, v in result.items()} }")
    print(f"  Total: {total/1e6:.1f}M  ({elapsed:.1f}s)")


def test_large_country(iso: str, shapes_url: str):
    """Fetch real admin-1 shapes from GADM and aggregate with worldpop.

    This is the critical test: large countries (BRA, IDN) have states whose
    raster windows exceed 8 M pixels and must be downsampled via Resampling.sum.
    """
    print(f"── POST /aggregate/{iso} (real admin-1 shapes from GADM) ──")

    # Fetch shapes
    print(f"  Fetching {iso}/1 from {shapes_url} ...")
    try:
        rs = httpx.get(f"{shapes_url}/boundaries/{iso}/1", timeout=120)
    except Exception as exc:
        print(f"  [SKIP] Could not reach GADM at {shapes_url}: {exc}")
        return
    check(f"GADM HTTP 200 for {iso}", rs.status_code == 200,
          f"got {rs.status_code}")
    fc = rs.json()
    n_features = len(fc["features"])
    print(f"  {n_features} features, raw body {len(rs.content)/1024:.0f} KB")

    # Truncate coordinates (same as client.html)
    def trunc(coords, dp=3):
        if isinstance(coords[0], (int, float)):
            return [round(v, dp) for v in coords]
        return [trunc(c, dp) for c in coords]

    fc_slim = {
        "type": "FeatureCollection",
        "features": [
            {**f, "geometry": {**f["geometry"],
             "coordinates": trunc(f["geometry"]["coordinates"])}}
            for f in fc["features"]
        ],
    }
    import json
    body_bytes = json.dumps(fc_slim).encode()
    print(f"  Slim body: {len(body_bytes)/1024:.0f} KB")

    # Aggregate
    print(f"  POSTing to {BASE}/aggregate/{iso}?year=2020 ...")
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{BASE}/aggregate/{iso}?year=2020",
            content=body_bytes,
            headers={"Content-Type": "application/json"},
            timeout=600,
        )
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"  [FAIL] Exception after {elapsed:.1f}s: {type(exc).__name__}: {exc}")
        sys.exit(1)

    elapsed = time.monotonic() - t0
    check("HTTP 200", r.status_code == 200,
          f"got {r.status_code}: {r.text[:300]}")
    result = r.json()
    check(f"{n_features} nodeids returned", len(result) == n_features,
          f"got {len(result)}")
    total = sum(result.values())
    print(f"  {len(result)} regions, total pop {total/1e6:.1f}M  ({elapsed:.1f}s)")
    check("all nodeids present", len(result) == n_features)
    check("total population > 0", total > 0, f"got {total:.0f}")


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
    parser.add_argument("--url", default=BASE, help="worldpop-service base URL")
    parser.add_argument("--wait", action="store_true",
                        help="Wait for service to be ready before running tests")
    parser.add_argument("--large-country", metavar="ISO",
                        help="Also test a large pre-warmed country (e.g. BRA). "
                             "Requires --gadm-url.")
    parser.add_argument("--gadm-url", default="http://48.200.52.126",
                        help="GADM service base URL (for --large-country shapes)")
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\nRunning worldpop-service tests against {BASE}\n")
    if args.wait:
        wait_for_ready()

    test_health()
    test_prewarm()
    test_aggregate()
    test_cache_speed()
    test_nga_multipolygon()
    if args.large_country:
        test_large_country(args.large_country.upper(), args.gadm_url)
    test_unknown_iso()
    test_bad_body()
    test_empty_features()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
