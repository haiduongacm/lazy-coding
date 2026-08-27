# lazy-coding

Zero-install AI Coding Agentic Platform.

## Sử dụng (không cần cài đặt)

### Bước 1: Clone

```bash
git clone https://github.com/haiduongacm/lazy-coding.git
cd lazy-coding
```

### Bước 2: Set PYTHONPATH

```bash
# PowerShell
$env:PYTHONPATH = "lazy_core/src;lazy_pool/src;lazy_gate/src;lazy_master/src"

# Bash
export PYTHONPATH="lazy_core/src:lazy_pool/src:lazy_gate/src:lazy_master/src"
```

### Bước 3: Dùng trực tiếp

```bash
# Lazy-master
python -m lazy_master.cli dispatch "fix bug"
python -m lazy_master.cli status
python -m lazy_master.cli guard

# Lazy-gate
python -m lazy_gate.cli init .
python -m lazy_gate.cli push

# Lazy-pool
python -m lazy_pool.cli get
python -m lazy_pool.cli status
```

### Hoặc dùng trong Python

```python
import sys
sys.path.insert(0, "lazy_core/src")
sys.path.insert(0, "lazy_pool/src")
sys.path.insert(0, "lazy_gate/src")
sys.path.insert(0, "lazy_master/src")

from lazy_master import Master
from lazy_pool import Pool
from lazy_gate import Gate
```

## Trong Claude

Khi bạn yêu cầu Claude làm task:

```
Bạn: "Fix login bug"

Claude:
  1. cd D:\lazy-coding
  2. python -m lazy_pool.cli get
  3. Viết test, code trong worktree
  4. python -m lazy_gate.cli push
  5. python -m lazy_pool.cli return
```

Không cần cài đặt. Không cần pip. Chỉ cần clone và chạy.
