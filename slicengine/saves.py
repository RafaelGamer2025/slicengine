"""
SlicEngine — Sistema de saves.

Integra o estado de jogo (variáveis, posição do jogador, mundo) com o
banco SQLite da engine (profile_db), permitindo:
    - salvar/carregar slots nomeados
    - listar slots do perfil atual
    - deletar saves

Uso:
    from slicengine.saves import SaveManager

    mgr = SaveManager(engine)
    mgr.save("slot1", titulo="Fase 1")
    if mgr.exists("slot1"):
        mgr.load("slot1")
"""
import json
import time

from .world import World, Entity


class SaveManager:
    def __init__(self, engine):
        self.engine = engine
        self.db = engine.db

    # ------------------------------------------------------------------
    def _state(self) -> dict:
        """Serializa o estado jogável do mundo."""
        p = next((e for e in self.engine.world.entities
                  if e.kind == "player"), None)
        return {
            "player": {"x": p.x, "y": p.y} if p else None,
            "entities": [e.to_dict() for e in self.engine.world.entities],
            "vars": dict(self.engine.lua_state["vars"]),
            "world": self.engine.world.to_dict(),
            "mode": self.engine.mode,
            "timestamp": time.time(),
        }

    def _restore(self, state: dict):
        """Restaura estado jogável."""
        w = state.get("world")
        if w:
            self.engine.world = World.from_dict(w)
        else:
            ents = state.get("entities", [])
            self.engine.world.entities = [Entity.from_dict(e)
                                          for e in ents]
        vars_ = state.get("vars", {})
        self.engine.lua_state["vars"].update(vars_)
        # reposicionar o jogador, se informado
        pl = state.get("player")
        if pl:
            p = next((e for e in self.engine.world.entities
                      if e.kind == "player"), None)
            if p:
                p.x, p.y = pl["x"], pl["y"]
                self.engine.lua_state["vars"]["player_x"] = p.x
                self.engine.lua_state["vars"]["player_y"] = p.y
                if self.engine.raycaster:
                    self.engine.raycaster.x = p.x
                    self.engine.raycaster.y = p.y
        mode = state.get("mode")
        if mode:
            self.engine.mode = mode

    @staticmethod
    def _slot_key(slot) -> int:
        if isinstance(slot, int):
            return slot
        return abs(hash(str(slot))) % 10**9 + 1

    # ------------------------------------------------------------------
    def save(self, slot, titulo=None, extra=None):
        """Salva o estado atual no slot (int ou string)."""
        data = self._state()
        data["titulo"] = titulo or str(slot)
        if extra:
            data["extra"] = extra
        self.db.save_game(self.engine.profile_id,
                          self._slot_key(slot),
                          data["titulo"],
                          json.dumps(data, ensure_ascii=False))
        return True

    def load(self, slot) -> bool:
        """Carrega o slot. Retorna False se não existir."""
        rec = self.db.load_game(self.engine.profile_id,
                                self._slot_key(slot))
        if not rec:
            return False
        try:
            state = json.loads(rec["world_json"])
        except (TypeError, ValueError, KeyError):
            return False
        self._restore(state)
        return True

    def exists(self, slot) -> bool:
        return bool(self.db.load_game(self.engine.profile_id,
                                      self._slot_key(slot)))

    def list_saves(self) -> list:
        out = []
        cur = self.db.conn.execute(
            "SELECT slot, game_title, saved_at FROM save_games "
            "WHERE profile_id = ? ORDER BY saved_at DESC",
            (self.engine.profile_id,))
        for slot, title, saved in cur.fetchall():
            out.append({"slot": slot, "title": title, "saved_at": saved})
        return out

    def delete(self, slot):
        self.db.conn.execute(
            "DELETE FROM save_games WHERE profile_id = ? AND slot = ?",
            (self.engine.profile_id, self._slot_key(slot)))
        self.db.conn.commit()
