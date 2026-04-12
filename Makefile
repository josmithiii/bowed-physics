# bowed-physics — top-level convenience Makefile
#
# Thin wrapper over CMake for C++ targets plus direct `python3` calls
# for the Python-side experiments and viewers.  Preferred build dir is
# ./build/ at the project root.

BUILD       := build
CMAKE       := cmake
CMAKE_FLAGS := -DCMAKE_BUILD_TYPE=Release

.PHONY: help configure build test clean rebuild \
        seestr run-seestr view-seestr \
        run-bow3 view-bow3 \
        bowed-string bowed-string-b3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' Makefile | awk -F ':.*## ' '{printf "  %-22s %s\n", $$1, $$2}'

# ------------------------------------------------------------------
# C++ build (via CMake)
# ------------------------------------------------------------------

configure: ## Run CMake configure step into ./build/
	$(CMAKE) -S . -B $(BUILD) $(CMAKE_FLAGS)

build: ## Build all C++ targets
	$(CMAKE) --build $(BUILD) --parallel

seestr: configure ## Build just the `seestr` experiment binary
	$(CMAKE) --build $(BUILD) --target seestr --parallel

rebuild: clean build ## Full clean + rebuild

clean: ## Remove ./build/
	rm -rf $(BUILD)

# ------------------------------------------------------------------
# C++ experiments: STK-based bowed-string probe (ex-ncbs)
# Args to seestr: duration stride beta prefix
# ------------------------------------------------------------------

run-seestr: seestr ## Run the STK bowed string probe (default β≈0.127 near bridge)
	cd $(BUILD) && ./seestr 0.5 20 0.127236 ""

view-seestr: ## Animate build/string_out.wav with the viewer
	python3 viewers/seestr.py --build-dir $(BUILD)

run-bow3: seestr ## Run the STK bowed string probe at β=1/3 (segment ratio 1:2)
	cd $(BUILD) && ./seestr 1.0 40 0.3333333 "bow3_"

view-bow3: ## Animate the bow3_ experiment's output
	python3 viewers/seestr.py --prefix bow3_ --build-dir $(BUILD)

# ------------------------------------------------------------------
# Python experiments: digital-waveguide bowed-string toy
# ------------------------------------------------------------------

bowed-string: ## Python DW bowed-string toy, default β=1/8 (near bridge); writes PNG/EPS/GIF
	python3 python/bowed_physics/bowed_string_toy.py --gif

bowed-string-b3: ## Python DW bowed-string toy at β=1/3 (segment ratio 1:2)
	python3 python/bowed_physics/bowed_string_toy.py --gif --beta 0.3333333 --suffix _b3

# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

test: ## Run Python tests (pytest)
	python3 -m pytest tests/
