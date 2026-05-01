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

# ── all ────────────────────────────────────────────────────────────────────────

run-all:   run-unwpp run-gadm
stop-all:  stop-unwpp stop-gadm

.PHONY: build-unwpp run-unwpp stop-unwpp restart-unwpp logs-unwpp test-unwpp \
        build-gadm run-gadm stop-gadm restart-gadm logs-gadm test-gadm \
        run-all stop-all
