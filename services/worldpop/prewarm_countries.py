"""
Prewarm worldpop-service raster cache for a list of countries.

Usage:
    python prewarm_countries.py [--url http://localhost:8104] [--year 2020]
                                [--workers 4] [--countries FILE]

Designed to run as a Kubernetes init Job that pre-populates the PVC before
worldpop-service pods start serving traffic. Each ISO triggers a
POST /prewarm/{iso} call; the service downloads and caches the raster.

Default country list covers common LASER / humanitarian contexts (~50 ISOs).
Pass --countries to override with a newline-delimited file of ISO3 codes.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

# fmt: off
DEFAULT_COUNTRIES = [
    # Sub-Saharan Africa
    "NGA", "ETH", "COD", "TZA", "KEN", "UGA", "MOZ", "GHA", "MDG", "CMR",
    "CIV", "NER", "BFA", "MLI", "SEN", "ZMB", "ZWE", "SOM", "SSD", "SDN",
    "AGO", "RWA", "BDI", "TCD", "GIN", "SLE", "LBR", "MWI", "NAM", "BWA",
    # North Africa / Middle East
    "EGY", "DZA", "MAR", "TUN", "LBY", "SYR", "IRQ", "YEM", "AFG", "PAK",
    # South / Southeast Asia
    "IND", "BGD", "NPL", "MMR", "KHM", "LAO", "PHL", "IDN",
    # Latin America
    "BRA", "COL", "PER", "BOL", "HTI",
    # Western Europe — small rasters, useful for evaluator ground-truthing
    "GBR", "DEU", "FRA",
]
# fmt: on

_MAX_RETRIES = 15       # up to 15 min of retries per country
_RETRY_WAIT  = 60       # seconds between retries


def prewarm_one(url: str, iso: str, year: int) -> tuple[str, bool, str]:
    # Retry on connection reset — Azure LB 4-min idle timeout fires while a
    # large raster is downloading server-side; the download continues and the
    # next attempt hits the cache.
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            r = httpx.post(f"{url}/prewarm/{iso}?year={year}", timeout=1800)
            if r.status_code == 200:
                return iso, True, ""
            return iso, False, f"HTTP {r.status_code}: {r.text[:120]}"
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError) as exc:
            if attempt == _MAX_RETRIES:
                return iso, False, f"gave up after {attempt} retries: {exc}"
            print(f"  [WAIT] {iso} — connection reset, retry {attempt}/{_MAX_RETRIES} in {_RETRY_WAIT}s",
                  flush=True)
            time.sleep(_RETRY_WAIT)
        except Exception as exc:
            return iso, False, str(exc)
    return iso, False, "unreachable"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-warm WorldPop raster cache.")
    parser.add_argument("--url", default="http://localhost:8104",
                        help="worldpop-service base URL")
    parser.add_argument("--year", type=int, default=2020,
                        help="WorldPop year (2000–2020, default 2020)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel download workers (default 4)")
    parser.add_argument("--countries", metavar="FILE",
                        help="Newline-delimited file of ISO3 codes (overrides default list)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    if args.countries:
        with open(args.countries) as f:
            isos = [ln.strip().upper() for ln in f if ln.strip() and not ln.startswith("#")]
    else:
        isos = DEFAULT_COUNTRIES

    print(f"Pre-warming {len(isos)} countries at {base_url} (year={args.year}, workers={args.workers})\n",
          flush=True)

    t0 = time.monotonic()
    ok, failed = [], []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(prewarm_one, base_url, iso, args.year): iso for iso in isos}
        for fut in as_completed(futures):
            iso, success, msg = fut.result()
            if success:
                ok.append(iso)
                print(f"  [OK]   {iso}", flush=True)
            else:
                failed.append(iso)
                print(f"  [FAIL] {iso} — {msg}", flush=True)

    elapsed = time.monotonic() - t0
    print(f"\n{len(ok)}/{len(isos)} countries cached in {elapsed:.0f}s", flush=True)
    if failed:
        print(f"Failed: {', '.join(failed)}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
