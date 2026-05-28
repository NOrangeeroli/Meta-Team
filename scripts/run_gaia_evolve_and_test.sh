#!/bin/bash
# GAIA Evolution Pipeline — 20-train evolve + 100-test evaluation.
#
# Usage:
#   scripts/run_gaia_evolve_and_test.sh [evolve|test|smoke]
#   - smoke:  run 3 cases of train_20 (first 3 tasks) to validate the pipeline
#   - evolve: run full 20-case evolve (~4-6 hours)
#   - test:   run 100-case hold-out test on the evolved pool (~2 hours w/ -j4)
#
# Workflow:
#   1. smoke (3 cases)   → validates evolve pipeline end-to-end
#   2. evolve (20 cases) → produces runs/<ts>_evolve_gaia_train_20_evolve/
#   3. promote            → copy latest team/vNN to agents/pool_GAIA_MT_evolved_v0NN
#   4. test (100 cases)  → evaluates the promoted pool on hold-out

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs

MODE="${1:-smoke}"
TS=$(date +%Y%m%d_%H%M%S)

case "$MODE" in
  smoke)
    # Default: 2 cases (web + file typical paths). Override with 2nd arg.
    CASES="${2:-0,1}"
    echo "=== SMOKE TEST (cases=${CASES} from train_20) ==="
    RUN_ID="${TS}_smoke_gaia_train_20"
    python3 benchmarks/adapter_gaia.py \
        --split train_20 \
        --cases "${CASES}" \
        --evolve \
        --team pool_GAIA_MT \
        --run-id "${RUN_ID}" \
        2>&1 | tee "logs/${RUN_ID}.log"
    echo ""
    echo "Smoke run complete. Inspect:"
    echo "  runs/${RUN_ID}_evolve/summary.json"
    echo "  runs/${RUN_ID}_evolve/changelog.jsonl"
    echo "  runs/${RUN_ID}_evolve/team/v*/"
    ;;

  evolve)
    echo "=== FULL EVOLVE (20 cases) ==="
    RUN_ID="${TS}_evolve_gaia_train_20"
    python3 benchmarks/adapter_gaia.py \
        --split train_20 \
        --evolve \
        --team pool_GAIA_MT \
        --run-id "${RUN_ID}" \
        2>&1 | tee "logs/${RUN_ID}.log"
    echo ""
    echo "Evolve run complete:"
    echo "  runs/${RUN_ID}_evolve/"
    echo ""
    echo "To promote the evolved team:"
    echo "  LATEST_V=\$(ls runs/${RUN_ID}_evolve/team/ | grep -E '^v[0-9]+$' | tail -1)"
    echo "  cp -r runs/${RUN_ID}_evolve/team/\$LATEST_V agents/pool_GAIA_MT_evolved_\$LATEST_V"
    ;;

  test)
    # Usage: scripts/run_gaia_evolve_and_test.sh test <evolved_pool_name> [--rollout N]
    POOL="${2:-}"
    if [[ -z "$POOL" ]]; then
        echo "Usage: $0 test <evolved_pool_name> [--rollout N]"
        echo "Example: $0 test pool_GAIA_MT_evolved --rollout 3"
        exit 1
    fi
    if [[ ! -d "agents/${POOL}" ]]; then
        echo "Pool not found: agents/${POOL}"
        exit 1
    fi
    shift 2
    ROLLOUTS=1
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --rollout) ROLLOUTS="$2"; shift 2 ;;
            *) echo "Unknown arg: $1"; exit 1 ;;
        esac
    done
    echo "=== HOLD-OUT TEST (100 cases on ${POOL}, rollouts=${ROLLOUTS}) ==="
    for r in $(seq 1 "$ROLLOUTS"); do
        RUN_ID="${TS}_test_gaia_${POOL}_r${r}"
        echo "--- Rollout ${r}/${ROLLOUTS} (run_id: ${RUN_ID}) ---"
        python3 benchmarks/adapter_gaia.py \
            --split test_100 \
            --team "${POOL}" \
            --workers 6 \
            --run-id "${RUN_ID}" \
            2>&1 | tee "logs/${RUN_ID}.log"
    done
    echo ""
    echo "Test complete. Results in benchmarks/gaia-results/"
    ;;

  *)
    echo "Unknown mode: $MODE"
    echo "Usage: $0 [smoke|evolve|test]"
    exit 1
    ;;
esac
