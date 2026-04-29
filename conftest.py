"""
Root conftest — chargé automatiquement par pytest avant tous les tests.

Problème Windows Store Python : uvicorn.exe est installé dans le dossier
"Scripts" des paquets utilisateur, qui n'est PAS dans le PATH système par
défaut. Résultat : subprocess.Popen(["uvicorn", ...]) échoue avec WinError 2.

Ce fichier ajoute le bon dossier Scripts au PATH avant que la fixture
api_process de test_auto_eval.py ne soit exécutée.
"""

import os
import shutil
import site
import sys
from pathlib import Path


def pytest_configure(config):
    if shutil.which("uvicorn"):
        return  # uvicorn déjà accessible, rien à faire

    candidates = []

    # 1. Scripts à côté du site-packages utilisateur (Windows Store Python)
    try:
        user_sp = Path(site.getusersitepackages())
        candidates.append(user_sp.parent / "Scripts")
    except Exception:
        pass

    # 2. Scripts à côté de l'exécutable Python courant
    candidates.append(Path(sys.executable).parent)
    candidates.append(Path(sys.executable).parent / "Scripts")

    # 3. Scripts dans le venv courant (si applicable)
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        candidates.append(Path(sys.prefix) / "Scripts")
        candidates.append(Path(sys.prefix) / "bin")

    for candidate in candidates:
        uv = candidate / "uvicorn.exe"
        if not uv.exists():
            uv = candidate / "uvicorn"   # Linux/macOS dans un venv
        if uv.exists():
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            return
