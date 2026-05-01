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

# ── all ────────────────────────────────────────────────────────────────────────

run-all:   run-unwpp
stop-all:  stop-unwpp

.PHONY: build-unwpp run-unwpp stop-unwpp restart-unwpp logs-unwpp test-unwpp \
        run-all stop-all
