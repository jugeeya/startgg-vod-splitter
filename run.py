"""
Entry point for running the app (used by PyInstaller when building the exe).
From the project root you can still use:  python -m src.main
"""
from src.main import run_gui

if __name__ == "__main__":
    run_gui()
