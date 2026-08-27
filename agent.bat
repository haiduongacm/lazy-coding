@echo off
REM lazy-coding agent bootstrap
REM Call this file to set up the environment
REM
REM Usage in Claude/OpenCode:
REM   D:\lazy-coding\agent.bat
REM   python -m lazy_master.cli status

set PYTHONPATH=%~dp0lazy_core\src;%~dp0lazy_pool\src;%~dp0lazy_gate\src;%~dp0lazy_master\src
