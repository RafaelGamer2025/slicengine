"""
SlicEngine — Núcleo da engine.

A classe Engine une tudo:
- Loop principal com delta time
- Gerenciador de assets, mods, hierarquia, perfis, shell local
- Eventos (update, tecla, colidir...)
- Modos: editor (pincel), jogo 2D, jogo 3D raycasting, menu com GIF
- API de script (usada por Lua/Python/.sl)
"""
import os
import sys
import time
import pygame

from . import utils
from .assets import AssetManager
from .world import World, Entity
from .raycaster import Raycaster
from .editor import MapEditor
from .modsystem import ModSystem
from .seformat import SEFormat
from .hierarchy import Hierarchy
from .local import ScriptRunner, Shell
from .profile_db import ProfileDB
from .aiscript import AIAssistant

pygame.mixer.pre_init(44100, -16, 2, 1024)


class Engine:
    """Engine principal da SlicEngine."""

    def __init__(self, title="SlicEngine", width=800, height=600,
                 mode="2d", profile="default", base_dir="."):
        pygame.init()
        self.title = title
        self.width, self.height = width, height
        self.mode = mode                  # "2d", "3d", "editor"
        self.base_dir = os.path.abspath(base_dir)
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title + " — " + utils.VERSION)
        self.clock = pygame.time.Clock()

        # componentes
        self.assets = AssetManager(self.base_dir)
        self.hierarchy = Hierarchy()
        self.mods = ModSystem(self)
        db_path = os.path.join(self.base_dir, ".slicengine.db")
        self.db = ProfileDB(db_path=db_path)
        self.ai = AIAssistant()
        self.runner = ScriptRunner(self)
        self.shell = Shell(workdir=self.base_dir, record_db=self.db)
        self.format = SEFormat()

        # estado
        self.world = World()
        self.raycaster = None
        self.editor = None
        self.running = True
        self.paused = False
        self.state = "menu"           # menu | editor | game
        self.elapsed = 0.0
        self._last = time.perf_counter()
        self.fps_counter = utils.FPSCounter()

        # variáveis de jogo (acessíveis por scripts)
        self.lua_state = {
            "vars": {}, "snd_queue": [], "mus_queue": [], "texts": [],
            "spawns": [], "player_move": [], "stop": False,
            "window": None, "lua_start": False, "load_map": None,
        }

        # eventos: id -> lista de callbacks
        self._handlers = {}
        # texto flutuante: (texto, fim_tempo)
        self._toast = None

        # menu
        self._menu_gif = None
        self._menu_title = "SlicEngine"
        self._menu_action = None

        # perfil
        self.profile_name = profile
        self.profile_id = self.db.create_profile(profile)

        # carregar mods da pasta plugins/ e do base_dir
        self.mods.scan_folder(os.path.join(self.base_dir, "plugins"))
        self.mods.scan_folder(os.path.join(self.base_dir, "mods"))

    # ------------------------------------------------------------------
    # API pública de eventos (usada por Lua/Python/.sl)
    # ------------------------------------------------------------------
    def adicionar_evento(self, event_id: str, callback):
        self._handlers.setdefault(event_id, []).append(callback)

    def adicionar_evento_lua(self, event_id: str, fn):
        self.adicionar_evento(event_id, fn)

    def disparar(self, event_id: str, payload=None):
        """Dispara evento na hierarquia e nos handlers."""
        self.hierarchy.dispatch(event_id, payload)
        for cb in self._handlers.get(event_id, []):
            try:
                cb(self._build_api(), payload)
            except Exception as e:
                print(f"[Engine] erro no handler {event_id}: {e}")

    # ------------------------------------------------------------------
    # API de script (o "api" passado aos callbacks)
    # ------------------------------------------------------------------
    def _build_api(self):
        return {
            "get_var": lambda name: self.lua_state["vars"].get(name, 0),
            "set_var": lambda name, v: self.lua_state["vars"].__setitem__(
                name, v),
            "add_var": lambda name, n: self.lua_state["vars"].__setitem__(
                name, self.lua_state["vars"].get(name, 0) + n),
            "tecla_pressionada": lambda key: pygame.key.get_pressed()[
                getattr(pygame, "K_" + key.upper(), 0)],
            "tocar_som": self._api_tocar_som,
            "tocar_musica": self._api_tocar_musica,
            "parar_musica": self._api_parar_musica,
            "mover_jogador": self._api_mover_jogador,
            "mostrar_texto": self._api_mostrar_texto,
            "destruir_evento": lambda: None,
            "parar_jogo": lambda: self.lua_state.__setitem__("stop", True),
            "carregar_mapa": self._api_carregar_mapa,
            "criar_entidade": self._api_criar_entidade,
        }

    def _api_tocar_som(self, path):
        try:
            self.assets.sound(path).play()
        except Exception:
            print(f"[Engine] som não encontrado: {path}")

    def _api_tocar_musica(self, path):
        try:
            self.assets.music_play(path)
        except Exception:
            print(f"[Engine] música não encontrada: {path}")

    def _api_parar_musica(self):
        pygame.mixer.music.stop()

    def _api_mover_jogador(self, dx, dy):
        self.lua_state["player_move"].append([dx, dy])

    def _api_mostrar_texto(self, text, dur=2.0):
        self._toast = (text, self.elapsed + dur)

    def _api_carregar_mapa(self, path):
        self.lua_state["load_map"] = path

    def _api_criar_entidade(self, kind):
        self.lua_state["spawns"].append([kind, 0.0, 0.0])

    # ------------------------------------------------------------------
    # Construção de mundo
    # ------------------------------------------------------------------
    def build_from_ascii(self, ascii_map: str, title="Jogo"):
        """Cria mundo a partir de mapa ASCII (# parede, P player, E inimigo)."""
        self.world = World.from_ascii(ascii_map)
        self.world.flags["title"] = title
        self.mode = "3d" if any("#" in ln for ln in ascii_map.splitlines()) \
            else "2d"
        self._setup_scene()

    def load_package(self, path: str):
        """Carrega um pacote .se."""
        self.world = self.format.load(path)
        self.mode = self.world.flags.get("mode", "2d")
        self._setup_scene()
        # carregar scripts embarcados
        for sname in self.world.flags.get("scripts", []):
            try:
                content = self.format.read_file(path, sname)
                base = os.path.dirname(path)
                if sname.endswith(".lua"):
                    self.runner.run_string(content, "lua")
                elif sname.endswith(".sl"):
                    self.runner.run_string(content, "sl")
                elif sname.endswith(".py"):
                    self.runner.run_string(content, "python")
            except Exception as e:
                print(f"[Engine] erro no script {sname}: {e}")

    def _build_fallback_atlas(self):
        """Gera texturas procedurais quando não há arquivos em assets/."""
        import random
        atlas = {}
        bases = [(150, 110, 70), (100, 100, 110), (70, 120, 70),
                 (90, 85, 100), (150, 110, 70), (60, 130, 60),
                 (70, 120, 180), (150, 150, 150)]
        for tid in range(1, 9):
            tex = pygame.Surface((64, 64))
            r2 = random.Random(tid * 77)
            base = bases[tid - 1]
            for y in range(64):
                for x in range(64):
                    v = r2.uniform(-20, 20)
                    bh = 16
                    if y % bh < 2 or ((y // bh) % 2 == 0 and
                                      (x + bh // 2) % 32 < 2):
                        c = (base[0] * 0.4, base[1] * 0.4, base[2] * 0.4)
                    else:
                        c = (base[0] + v, base[1] + v, base[2] + v * 0.7)
                    tex.set_at((x, y), tuple(int(min(255, max(0, ch)))
                                             for ch in c))
            atlas[tid] = tex
        return atlas

    def _setup_scene(self):
        self.world.flags.setdefault("mode", self.mode)
        # player
        player = next((e for e in self.world.entities
                       if e.kind == "player"), None)
        if player:
            self.lua_state["vars"]["player_x"] = player.x
            self.lua_state["vars"]["player_y"] = player.y

        if self.mode == "3d":
            if self.world.raycast_map:
                atlas = {}
                if not pygame.display.get_init():
                    pygame.display.init()
                for tid in range(1, 9):
                    for name in (f"assets/wall{tid}.png",
                                 f"assets/wall_{tid}.png",
                                 f"assets/wall{tid}.jpg",
                                 f"assets/sprites/wall{tid}.png",
                                 f"sprites/wall{tid}.png"):
                        try:
                            atlas[tid] = self.assets.sprite_raw(name)
                            break
                        except (pygame.error, FileNotFoundError):
                            continue
                if not atlas:
                    # texturas procedurais de reserva (tijolo/metal)
                    atlas = self._build_fallback_atlas()
                print(f"[Engine] atlas 3D: {list(atlas.keys())}")
                self.raycaster = Raycaster(
                    self.world.raycast_map, atlas,
                    self.width, self.height)
                if player:
                    self.raycaster.x, self.raycaster.y = player.x, player.y
            self.state = "game"
        else:
            self.state = "game"

        self.mods.load_all()
        self.disparar("iniciar")

    # ------------------------------------------------------------------
    # Menu com GIF
    # ------------------------------------------------------------------
    def set_menu(self, gif=None, title="SlicEngine",
                 start_action=None, subtitle=None):
        self._menu_gif = gif
        self._menu_title = title
        self._menu_subtitle = subtitle or \
            "Pressione ENTER para jogar"
        self._menu_action = start_action
        self.state = "menu"

    def _draw_menu(self):
        if self._menu_gif is not None:
            frame = self._menu_gif.frame_at(self.elapsed)
            fw, fh = frame.get_size()
            sw, sh = self.screen.get_size()
            # cobrir a tela repetindo o frame
            y = 0
            while y < sh:
                x = 0
                while x < sw:
                    self.screen.blit(frame, (x, y))
                    x += fw
                y += fh
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill((10, 10, 18))

        sw, sh = self.screen.get_size()
        big = pygame.font.SysFont("dejavusans", 56, bold=True)
        small = pygame.font.SysFont("dejavusans", 22)
        title_surf = big.render(self._menu_title, True, (255, 220, 60))
        sub_surf = small.render(self._menu_subtitle, True, (230, 230, 230))
        ver_surf = small.render(f"SlicEngine {utils.VERSION}  |  "
                                f"{self.profile_name}  |  "
                                f"ESC = sair", True, (160, 160, 180))
        self.screen.blit(title_surf,
                         (sw // 2 - title_surf.get_width() // 2,
                          sh // 2 - 80))
        self.screen.blit(sub_surf,
                         (sw // 2 - sub_surf.get_width() // 2,
                          sh // 2 + 20))
        self.screen.blit(ver_surf, (12, sh - 30))

    # ------------------------------------------------------------------
    # Loop de jogo 2D
    # ------------------------------------------------------------------
    def _draw_2d(self):
        ts = self.world.tilemap.tile_size
        tm = self.world.tilemap
        # câmera segue o jogador
        px, py = self._player_xy()
        cam_x = max(0, min(px * ts - self.width // 2,
                           tm.pixels_w - self.width))
        cam_y = max(0, min(py * ts - self.height // 2,
                           tm.pixels_h - self.height))
        self.screen.fill((15, 15, 20))
        x0 = max(0, int(cam_x) // ts)
        y0 = max(0, int(cam_y) // ts)
        x1 = min(tm.width, int(cam_x + self.width) // ts + 1)
        y1 = min(tm.height, int(cam_y + self.height) // ts + 1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                tid = tm.get(x, y)
                if tid == 0:
                    continue
                px0 = x * ts - int(cam_x)
                py0 = y * ts - int(cam_y)
                try:
                    spr = self.assets.sprite_raw(
                        f"tile{tid}.png" if tid else "tile.png")
                    self.screen.blit(spr, (px0, py0))
                except (pygame.error, FileNotFoundError):
                    from .editor import TILE_COLORS
                    pygame.draw.rect(self.screen,
                                     TILE_COLORS.get(tid, (100, 100, 100)),
                                     (px0, py0, ts, ts))
                    pygame.draw.rect(self.screen, (0, 0, 0),
                                     (px0, py0, ts, ts), 1)
        # entidades
        for e in self.world.entities:
            if not e.alive:
                continue
            ex = int(e.x * ts - cam_x)
            ey = int(e.y * ts - cam_y)
            try:
                spr = self.assets.sprite(
                    {"player": "player.png", "enemy": "enemy.png",
                     "coin": "coin.png"}.get(e.kind, "player.png"))
                self.screen.blit(spr, (ex - spr.get_width() // 2,
                                       ey - spr.get_height() // 2))
            except (pygame.error, FileNotFoundError):
                color = {"player": (60, 150, 255), "enemy": (220, 60, 60),
                         "coin": (255, 215, 0)}.get(e.kind, (200, 200, 200))
                pygame.draw.circle(self.screen, color, (ex, ey), ts // 3)

    def _player_xy(self):
        p = next((e for e in self.world.entities if e.kind == "player"),
                 None)
        if p:
            return p.x, p.y
        return 1.5, 1.5

    def _update_2d_entities(self, keys, dt):
        p = next((e for e in self.world.entities if e.kind == "player"),
                 None)
        if p is None:
            return
        dx = dy = 0.0
        spd = 150 * dt / self.world.tilemap.tile_size
        try:
            kw = keys[pygame.K_w] or keys[pygame.K_UP]
            ks = keys[pygame.K_s] or keys[pygame.K_DOWN]
            ka = keys[pygame.K_a] or keys[pygame.K_LEFT]
            kd = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        except KeyError:
            kw = ks = ka = kd = False
        if kw:
            dy -= spd
        if ks:
            dy += spd
        if ka:
            dx -= spd
        if kd:
            dx += spd
        # movimentos pedidos por script
        for mv in self.lua_state["player_move"]:
            dx += mv[0] * dt * 2
            dy += mv[1] * dt * 2
        self.lua_state["player_move"].clear()
        # colisão com paredes (tile 1 na camada terreno)
        tm = self.world.tilemap
        nx, ny = p.x + dx, p.y + dy
        if not tm.get(int(nx + (0.2 if dx > 0 else -0.2)), int(p.y)):
            p.x = nx
        if not tm.get(int(p.x), int(ny + (0.2 if dy > 0 else -0.2))):
            p.y = ny
        self.lua_state["vars"]["player_x"] = p.x
        self.lua_state["vars"]["player_y"] = p.y
        # colisões com outras entidades
        for e in self.world.entities:
            if e is p or not e.alive:
                continue
            if utils.distance(p.x, p.y, e.x, e.y) < 0.6:
                self.disparar(f"colidir:{e.kind}", e.data)

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def run(self, start_state=None):
        """Roda a engine até fechar."""
        if start_state:
            self.state = start_state
        while self.running:
            dt = min(0.05, time.perf_counter() - self._last)
            self._last = time.perf_counter()
            self.elapsed += dt
            self.fps_counter.update()

            # eventos do pygame
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN:
                    self.disparar(f"tecla:{pygame.key.name(ev.key)}")
                    if ev.key == pygame.K_ESCAPE:
                        if self.state == "game":
                            self.state = "menu"
                        elif self.state == "menu":
                            self.running = False
                        elif self.state == "editor":
                            self.state = "menu"
                    elif ev.key == pygame.K_RETURN and \
                            self.state == "menu" and self._menu_action:
                        self._menu_action()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    self.disparar("mouse:click", ev.pos)

            keys = pygame.key.get_pressed()

            # ------- estados -------
            if self.state == "menu":
                self._draw_menu()
            elif self.state == "editor":
                if self.editor is None:
                    self.editor = MapEditor(self)
                res = self.editor.handle_event(
                    pygame.event.Event(pygame.USEREVENT))
                if res == "test":
                    self.mode = "2d"
                    self._setup_scene()
                self.editor.update(dt)
                self.editor.draw(self.screen)
            elif self.state == "game":
                if self.mode == "3d" and self.raycaster:
                    self.raycaster.move(keys, dt)
                    sprites = [
                        {"x": e.x, "y": e.y,
                         "surface": self.assets.sprite(
                             {"enemy": "enemy.png", "coin": "coin.png"}
                             .get(e.kind, "enemy.png"))}
                        for e in self.world.entities if e.alive]
                    self.raycaster.render(self.screen, sprites)
                    self._update_2d_entities(keys, dt)
                else:
                    self._update_2d_entities(keys, dt)
                    self._draw_2d()
                # handlers de update (hierarquia + handlers)
                self.hierarchy.run_scripts(dt, self)
                self.disparar("update", dt)
                # spawns pedidos por scripts
                for sp in self.lua_state["spawns"]:
                    kind, x, y = sp
                    self.world.entities.append(Entity(kind, x, y))
                self.lua_state["spawns"].clear()
                # música pedida por scripts
                for m in self.lua_state["mus_queue"]:
                    if m is None:
                        pygame.mixer.music.stop()
                    else:
                        try:
                            self.assets.music_play(m)
                        except Exception:
                            pass
                self.lua_state["mus_queue"].clear()
                for s in self.lua_state["snd_queue"]:
                    try:
                        self.assets.sound(s).play()
                    except Exception:
                        pass
                self.lua_state["snd_queue"].clear()
                # toast
                if self._toast and self.elapsed > self._toast[1]:
                    self._toast = None
                if self._toast:
                    font = pygame.font.SysFont("dejavusans", 28, bold=True)
                    t = font.render(self._toast[0], True,
                                    (255, 255, 255))
                    self.screen.blit(
                        t, (self.width // 2 - t.get_width() // 2, 40))
                # FPS
                fps = pygame.font.SysFont("dejavusans", 13)
                f = fps.render(f"FPS {self.fps_counter.fps:.0f} | "
                               f"modo {self.mode}", True, (255, 255, 0))
                self.screen.blit(f, (self.width - 170, 8))
                if self.lua_state.get("stop"):
                    self.state = "menu"
                    self.lua_state["stop"] = False

            pygame.display.flip()
            self.clock.tick(60)

        pygame.mixer.quit()
        pygame.quit()
        try:
            self.db.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Variáveis de jogo (conveniência para scripts Python)
    # ------------------------------------------------------------------
    def get_var(self, name, default=0):
        return self.lua_state["vars"].get(name, default)

    def set_var(self, name, value):
        self.lua_state["vars"][name] = value

    def add_var(self, name, n):
        self.lua_state["vars"][name] = \
            self.lua_state["vars"].get(name, 0) + n

    # ------------------------------------------------------------------
    # Utilitários públicos
    # ------------------------------------------------------------------
    def save(self, path="jogo.se", title=None):
        mode = "3d" if self.mode == "3d" else "2d"
        return self.format.save(self.world, path,
                                title=title or self.title, mode=mode)

    def ai_ask(self, prompt: str) -> str:
        return self.ai.ask_online(prompt)

    def run_script(self, source: str, lang="auto") -> str:
        return self.runner.run_string(source, lang)

    def shell_run(self, command: str) -> str:
        return self.shell.run(command)

    def print_hierarchy(self) -> str:
        return repr(self.hierarchy)
