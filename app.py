"""Entrada Streamlit: reexecuta a interface em cada rerun (sem cache de import)."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("smartlaunch_ui.py")), run_name="__main__")
