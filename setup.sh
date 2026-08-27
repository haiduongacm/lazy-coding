#!/bin/bash
# Setup lazy-coding environment (zero-install)
export PYTHONPATH="$(dirname "$0")/lazy_core/src:$(dirname "$0")/lazy_pool/src:$(dirname "$0")/lazy_gate/src:$(dirname "$0")/lazy_master/src"
echo "lazy-coding environment ready."
echo "PYTHONPATH=$PYTHONPATH"
