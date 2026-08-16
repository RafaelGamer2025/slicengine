"""
SlicEngine — SaveSystem.

Separa claramente os tipos de dados que a engine salva::

    Engine configuration   -> configuração do runtime (tela, fps...)
    Project configuration  -> nome, versão, caminho, assets, cenas
    Scene data             -> conteúdo de uma cena (via Scene.save)
    Game save data         -> progresso de jogo (slots)
    User/editor settings   -> preferências do editor (janelas, tema...)

Formato: JSON com ``save_version`` e ``engine_version`` para permitir
migração e validação. Autosave periódico opcional e backup automático.
"""
import json
import os
import shutil
import time

from . import utils
from .gameobjects import Logger

SAVE_VERSION = 1


class SaveError(Exception):
    """Erro específico do sistema de salvamento."""


class SaveSystem:
    """Salvamento validado, versionado e com backup/autosave."""

    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.saves_dir = os.path.join(self.project_dir, "saves")
        self.settings_path = os.path.join(self.project_dir,
                                          "settings.json")
        self.autosave_timer = 0.0
        self.autosave_interval = 30.0      # segundos
        self._autosave_fn = None

    # ------------------------------------------------------------------
    # validação de caminho (segurança)
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_path(base, name):
        full = os.path.realpath(os.path.join(base, name))
        if not full.startswith(os.path.realpath(base)):
            raise SaveError(f"caminho inválido: {name}")
        return full

    # ------------------------------------------------------------------
    def _write(self, path, data):
        data["engine_version"] = utils.VERSION
        data["save_version"] = SAVE_VERSION
        data["saved_at"] = time.time()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    @staticmethod
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise SaveError(f"arquivo corrompido: {e}") from e
        if not isinstance(data, dict):
            raise SaveError("formato inválido")
        return data

    # ------------------------------------------------------------------
    # Project configuration
    # ------------------------------------------------------------------
    def save_project(self, name, version="0.1.0", path=None,
                     extra=None):
        data = {
            "kind": "project",
            "name": name,
            "version": version,
            "path": path or self.project_dir,
            "metadata": extra or {},
        }
        return self._write(
            self._safe_path(self.project_dir, "project.json"), data)

    def load_project(self):
        return self._read(self._safe_path(self.project_dir,
                                          "project.json"))

    # ------------------------------------------------------------------
    # Game save data (slots)
    # ------------------------------------------------------------------
    def save_game(self, slot=1, data=None):
        if not isinstance(slot, int) or not (1 <= slot <= 9):
            raise SaveError("slot inválido (1-9)")
        path = self._safe_path(self.saves_dir, f"slot{slot}.json")
        backup = path + ".bak"
        if os.path.exists(path):
            try:
                shutil.copy(path, backup)
            except OSError:
                pass
        return self._write(path, {"kind": "game", "slot": slot,
                                  "data": data or {}})

    def load_game(self, slot=1):
        return self._read(self._safe_path(self.saves_dir,
                                          f"slot{slot}.json"))

    def has_save(self, slot=1):
        return os.path.exists(self._safe_path(self.saves_dir,
                                              f"slot{slot}.json"))

    def list_saves(self):
        out = []
        try:
            for f in sorted(os.listdir(self.saves_dir)):
                if f.startswith("slot") and f.endswith(".json"):
                    out.append(f)
        except OSError:
            pass
        return out

    def recover(self, slot=1):
        """Restaura o backup (.bak) de um slot."""
        path = self._safe_path(self.saves_dir, f"slot{slot}.json")
        backup = path + ".bak"
        if not os.path.exists(backup):
            return False
        shutil.copy(backup, path)
        return True

    # ------------------------------------------------------------------
    # User/editor settings
    # ------------------------------------------------------------------
    def save_settings(self, settings):
        return self._write(self.settings_path,
                           {"kind": "settings", "data": settings})

    def load_settings(self):
        try:
            data = self._read(self.settings_path)
            return data.get("data", {})
        except SaveError:
            return {}

    # ------------------------------------------------------------------
    # Autosave
    # ------------------------------------------------------------------
    def set_autosave(self, interval, fn):
        """``fn`` é chamada periodicamente para gerar o snapshot."""
        self.autosave_interval = interval
        self._autosave_fn = fn

    def update(self, dt):
        if self._autosave_fn is None:
            return
        self.autosave_timer += dt
        if self.autosave_timer >= self.autosave_interval:
            self.autosave_timer = 0.0
            try:
                snapshot = self._autosave_fn()
                self._write(self._safe_path(
                    self.project_dir, "autosave.json"),
                    {"kind": "autosave", "data": snapshot})
                Logger.shared().debug("autosave gravado")
            except Exception as e:
                Logger.shared().warning(f"autosave falhou: {e}")

    def recover_autosave(self):
        try:
            data = self._read(self._safe_path(self.project_dir,
                                              "autosave.json"))
            return data.get("data")
        except SaveError:
            return None
