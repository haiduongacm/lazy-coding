#!/bin/bash
# lazy-coding agent bootstrap
# Source this file to set up the environment
#
# Usage in Claude/OpenCode:
#   source D:\lazy-coding\agent.sh
#   python -m lazy_master.cli status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/lazy_core/src:$SCRIPT_DIR/lazy_pool/src:$SCRIPT_DIR/lazy_gate/src:$SCRIPT_DIR/lazy_master/src"
