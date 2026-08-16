"""
SlicEngine — Banco de dados de PERFIS (SQLite).

Guarda:
- Perfis de desenvolvedor (nome, avatar, preferências)
- Jogos/projetos criados por perfil
- Histórico de comandos do terminal local
- Configurações por perfil (tema, controles, atalhos)

Banco fica em ~/.slicengine/profiles.db (ou no projeto, se definido).
"""
import os
import json
import sqlite3
import datetime

DEFAULT_DB = os.path.expanduser("~/.slicengine/profiles.db")


class ProfileDB:
    def __init__(self, db_path=None):
        self.path = db_path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # timeout generoso evita "database is locked" em testes rápidos
        self.conn = sqlite3.connect(self.path, timeout=5.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            avatar TEXT,
            created_at TEXT,
            settings_json TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            path TEXT,
            mode TEXT DEFAULT '2d',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );
        CREATE TABLE IF NOT EXISTS terminal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            command TEXT NOT NULL,
            output TEXT,
            executed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS save_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            slot INTEGER NOT NULL,
            game_title TEXT,
            world_json TEXT,
            saved_at TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Perfis
    # ------------------------------------------------------------------
    def create_profile(self, name: str, settings=None) -> int:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO profiles (name, created_at, settings_json) "
                "VALUES (?, ?, ?)",
                (name, datetime.datetime.now().isoformat(),
                 json.dumps(settings or {})))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return self.get_profile_id(name)

    def get_profile_id(self, name: str) -> int:
        cur = self.conn.execute(
            "SELECT id FROM profiles WHERE name = ?", (name,))
        row = cur.fetchone()
        return row[0] if row else 0

    def list_profiles(self) -> list:
        cur = self.conn.execute(
            "SELECT id, name, avatar, created_at, settings_json "
            "FROM profiles ORDER BY id")
        out = []
        for rid, name, avatar, created, sjson in cur.fetchall():
            out.append({
                "id": rid, "name": name, "avatar": avatar,
                "created_at": created,
                "settings": json.loads(sjson or "{}"),
            })
        return out

    def get_settings(self, profile_id: int) -> dict:
        cur = self.conn.execute(
            "SELECT settings_json FROM profiles WHERE id = ?", (profile_id,))
        row = cur.fetchone()
        if row:
            return json.loads(row[0] or "{}")
        return {}

    def save_settings(self, profile_id: int, settings: dict):
        self.conn.execute(
            "UPDATE profiles SET settings_json = ? WHERE id = ?",
            (json.dumps(settings), profile_id))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Projetos
    # ------------------------------------------------------------------
    def add_project(self, profile_id: int, title: str, path=None,
                    mode="2d") -> int:
        now = datetime.datetime.now().isoformat()
        cur = self.conn.execute(
            "INSERT INTO projects (profile_id, title, path, mode, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (profile_id, title, path, mode, now, now))
        self.conn.commit()
        return cur.lastrowid

    def list_projects(self, profile_id: int) -> list:
        cur = self.conn.execute(
            "SELECT id, title, path, mode, created_at, updated_at "
            "FROM projects WHERE profile_id = ? ORDER BY updated_at DESC",
            (profile_id,))
        cols = ["id", "title", "path", "mode", "created_at", "updated_at"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Terminal
    # ------------------------------------------------------------------
    def record_command(self, profile_id: int, command: str, output: str):
        self.conn.execute(
            "INSERT INTO terminal_history (profile_id, command, output, "
            "executed_at) VALUES (?,?,?,?)",
            (profile_id, command, output[:4000],
             datetime.datetime.now().isoformat()))
        self.conn.commit()

    def history(self, profile_id: int, limit=30) -> list:
        cur = self.conn.execute(
            "SELECT command, output, executed_at FROM terminal_history "
            "WHERE profile_id = ? ORDER BY id DESC LIMIT ?",
            (profile_id, limit))
        return list(cur.fetchall())[::-1]

    # ------------------------------------------------------------------
    # Saves
    # ------------------------------------------------------------------
    def save_game(self, profile_id: int, slot: int, title: str,
                  world_json: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO save_games "
            "(profile_id, slot, game_title, world_json, saved_at) "
            "VALUES (?,?,?,?,?)",
            (profile_id, slot, title, world_json,
             datetime.datetime.now().isoformat()))
        self.conn.commit()

    def load_game(self, profile_id: int, slot: int) -> dict:
        cur = self.conn.execute(
            "SELECT game_title, world_json, saved_at FROM save_games "
            "WHERE profile_id = ? AND slot = ?", (profile_id, slot))
        row = cur.fetchone()
        if row:
            return {"title": row[0], "world_json": row[1],
                    "saved_at": row[2]}
        return {}

    def close(self):
        self.conn.close()
