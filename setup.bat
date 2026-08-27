@echo off
REM Setup lazy-coding environment (zero-install)
set PYTHONPATH=%~dp0lazy_core\src;%~dp0lazy_pool\src;%~dp0lazy_gate\src;%~dp0lazy_master\src
echo lazy-coding environment ready.
echo PYTHONPATH=%PYTHONPATH%
