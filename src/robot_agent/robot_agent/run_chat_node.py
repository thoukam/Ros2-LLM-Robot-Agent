import os
import sys
import subprocess
from pathlib import Path


def main():
    ws = Path(__file__).resolve()

    for parent in ws.parents:
        candidate = parent / ".venv" / "bin" / "python"
        if candidate.exists():
            venv_python = str(candidate)
            break
    else:
        venv_python = os.environ.get("VIRTUAL_ENV")
        if venv_python:
            venv_python = str(Path(venv_python) / "bin" / "python")

    if not venv_python or not Path(venv_python).exists():
        print("Erreur: aucun .venv trouvé. Active ou crée .venv à la racine du workspace.")
        sys.exit(1)

    cmd = [venv_python, "-m", "robot_agent.chat_node", *sys.argv[1:]]
    os.execv(venv_python, cmd)