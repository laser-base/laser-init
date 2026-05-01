CACHE_ROOT ?= $(HOME)/.laser/cache
PYTHON     ?= python3.11

# ── unwpp-service (port 8100) ──────────────────────────────────────────────────

build-unwpp:
	docker build -t laser-unwpp-service unwpp/

run-unwpp: build-unwpp
	@mkdir -p $(CACHE_ROOT)/unwpp
	docker run -d \
		--name laser-unwpp-service \
		-p 8100:8000 \
		-v $(CACHE_ROOT)/unwpp:/cache \
		laser-unwpp-service
	@echo "unwpp-service running on http://localhost:8100"

stop-unwpp:
	docker stop laser-unwpp-service 2>/dev/null || true
	docker rm   laser-unwpp-service 2>/dev/null || true

restart-unwpp: stop-unwpp run-unwpp

logs-unwpp:
	docker logs -f laser-unwpp-service

test-unwpp:
	$(PYTHON) unwpp/test_client.py --url http://localhost:8100

# ── gadm-service (port 8101) ───────────────────────────────────────────────────

build-gadm:
	docker build -t laser-gadm-service gadm/

run-gadm: build-gadm
	@mkdir -p $(CACHE_ROOT)/gadm
	docker run -d \
		--name laser-gadm-service \
		-p 8101:8000 \
		-v $(CACHE_ROOT)/gadm:/cache \
		laser-gadm-service
	@echo "gadm-service running on http://localhost:8101"

stop-gadm:
	docker stop laser-gadm-service 2>/dev/null || true
	docker rm   laser-gadm-service 2>/dev/null || true

restart-gadm: stop-gadm run-gadm

logs-gadm:
	docker logs -f laser-gadm-service

test-gadm:
	$(PYTHON) gadm/test_client.py --url http://localhost:8101

# ── geoboundaries-service (port 8102) ─────────────────────────────────────────

build-geoboundaries:
	docker build -t laser-geoboundaries-service geoboundaries/

run-geoboundaries: build-geoboundaries
	@mkdir -p $(CACHE_ROOT)/geoboundaries
	docker run -d \
		--name laser-geoboundaries-service \
		-p 8102:8000 \
		-v $(CACHE_ROOT)/geoboundaries:/cache \
		laser-geoboundaries-service
	@echo "geoboundaries-service running on http://localhost:8102"

stop-geoboundaries:
	docker stop laser-geoboundaries-service 2>/dev/null || true
	docker rm   laser-geoboundaries-service 2>/dev/null || true

restart-geoboundaries: stop-geoboundaries run-geoboundaries

logs-geoboundaries:
	docker logs -f laser-geoboundaries-service

test-geoboundaries:
	$(PYTHON) geoboundaries/test_client.py --url http://localhost:8102

# ── unocha-service (port 8103) ────────────────────────────────────────────────

build-unocha:
	docker build -t laser-unocha-service unocha/

run-unocha: build-unocha
	@mkdir -p $(CACHE_ROOT)/unocha
	docker run -d \
		--name laser-unocha-service \
		-p 8103:8000 \
		-v $(CACHE_ROOT)/unocha:/cache \
		laser-unocha-service
	@echo "unocha-service running on http://localhost:8103"
	@echo "Note: first run downloads ~1-2 GB global GDB — use 'make logs-unocha' to monitor."

stop-unocha:
	docker stop laser-unocha-service 2>/dev/null || true
	docker rm   laser-unocha-service 2>/dev/null || true

restart-unocha: stop-unocha run-unocha

logs-unocha:
	docker logs -f laser-unocha-service

test-unocha:
	$(PYTHON) unocha/test_client.py --url http://localhost:8103 --wait

# ── worldpop-service (port 8104) ──────────────────────────────────────────────

build-worldpop:
	docker build -t laser-worldpop-service worldpop/

run-worldpop: build-worldpop
	@mkdir -p $(CACHE_ROOT)/worldpop
	docker run -d \
		--name laser-worldpop-service \
		-p 8104:8000 \
		-v $(CACHE_ROOT)/worldpop:/cache \
		laser-worldpop-service
	@echo "worldpop-service running on http://localhost:8104"
	@echo "Note: rasters are downloaded on demand via POST /prewarm/{iso} or POST /aggregate/{iso}."

stop-worldpop:
	docker stop laser-worldpop-service 2>/dev/null || true
	docker rm   laser-worldpop-service 2>/dev/null || true

restart-worldpop: stop-worldpop run-worldpop

logs-worldpop:
	docker logs -f laser-worldpop-service

test-worldpop:
	$(PYTHON) worldpop/test_client.py --url http://localhost:8104

# ── all ────────────────────────────────────────────────────────────────────────

run-all:   run-unwpp run-gadm run-geoboundaries run-unocha run-worldpop
stop-all:  stop-unwpp stop-gadm stop-geoboundaries stop-unocha stop-worldpop

.PHONY: build-unwpp run-unwpp stop-unwpp restart-unwpp logs-unwpp test-unwpp \
        build-gadm run-gadm stop-gadm restart-gadm logs-gadm test-gadm \
        build-geoboundaries run-geoboundaries stop-geoboundaries \
        restart-geoboundaries logs-geoboundaries test-geoboundaries \
        build-unocha run-unocha stop-unocha restart-unocha logs-unocha test-unocha \
        build-worldpop run-worldpop stop-worldpop restart-worldpop logs-worldpop test-worldpop \
        run-all stop-all
