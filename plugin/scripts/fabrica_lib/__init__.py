"""The factory's installer, updater and tutor helpers (standard library only: they run before anything is installed).

Called through plugin/scripts/fabrica.sh (Mac, Linux) or fabrica.ps1 (Windows), which first make sure `uv` exists and
then run fabrica.py with a Python 3.12 that uv provides. Nothing here needs administrator rights.
"""
