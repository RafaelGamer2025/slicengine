"""
SlicEngine — Telas de entrada da engine.

Entrada completa em camadas:

    Menu Principal
        [Jogar] ........... lista de projetos do perfil -> abrir/tentar
        [Novo Jogo] ....... cria projeto novo (nome + modo 2D/3D, gravado
                            no banco do perfil) -> abre editor
        [Perfis] .......... lista perfis do SQLite, criar perfil,
                            selecionar, ver stats (projetos/saves)
        [Demos] ........... atalhos para as demos
        [Sair]

Nada do núcleo (core.py) é alterado: esta camada usa apenas a API
pública da Engine. As telas são desenhadas por cima do loop com
``state = "menuscreen"`` e retornam a ação escolhida por callback.
"""
import os
import pygame
from . import utils


FONT_PATHS = ("dejavusans", "freesansbold", None)


def _sysfont(size, bold=False):
    for name in FONT_PATHS:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size * 2)


BG = (12, 12, 20)
ACCENT = (255, 220, 60)
TEXT = (235, 235, 240)
DIM = (150, 150, 170)
BTN_BG = (45, 45, 60)
BTN_HOVER = (70, 70, 100)
ITEM_BG = (32, 32, 48)


class MenuScreen:
    """Gerencia as telas de entrada. Uso:

        ms = MenuScreen(engine)
        engine.state = "menuscreen"
    """

    MAIN = "main"
    NEW = "new"
    PROJECTS = "projects"
    PROFILES = "profiles"
    DEMOS = "demos"
    PROFILE_NEW = "profile_new"

    def __init__(self, engine):
        self.engine = engine
        self.screen = "main"
        self.hover = -1
        self.sel = 0
        self.input_text = ""
        self.input_focus = False
        self.new_mode = "2d"
        self.message = ""
        self.message_time = 0.0
        self._profiles_cache = None
        self._avatar_cache = {}

    # ------------------------------------------------------------------
    def _font(self, size, bold=False):
        return _sysfont(size, bold)

    def _toast(self, text, t=2.0):
        self.message = text
        self.message_time = self.engine.elapsed + t

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def _profiles(self):
        return self.engine.db.list_profiles()

    def _projects(self):
        return self.engine.db.list_projects(self.engine.profile_id)

    def _avatar(self, name):
        """Desenha um avatar colorido a partir do nome (hash simples)."""
        h = sum(ord(c) for c in name) or 1
        color = (70 + (h * 17) % 140, 90 + (h * 31) % 120,
                 120 + (h * 43) % 90)
        key = name[:2].upper()
        if key in self._avatar_cache:
            return self._avatar_cache[key]
        s = pygame.Surface((40, 40))
        s.fill(color)
        f = self._font(20, True)
        t = f.render(key, True, (255, 255, 255))
        s.blit(t, (20 - t.get_width() // 2, 20 - t.get_height() // 2))
        self._avatar_cache[key] = s
        return s

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def go(self, screen):
        self.screen = screen
        self.hover = -1
        self.sel = 0
        self.input_text = ""
        self.input_focus = screen == self.PROFILE_NEW

    # ------------------------------------------------------------------
    def open_new_game(self):
        """Cria um projeto novo e abre o editor."""
        name = self.input_text.strip()
        if not name:
            self._toast("Digite o nome do jogo!")
            return
        pid = self.engine.profile_id
        self.engine.db.add_project(pid, name, mode=self.new_mode)
        self.engine.db.record_command(pid, f"projeto criado: {name}",
                                      "via menu")
        # limpa mundo atual e abre o editor
        from .world import World
        self.engine.world = World()
        self.engine.mode = self.new_mode
        self.engine.editor = None
        self.engine.state = "editor"
        self.engine.title = name
        pygame.display.set_caption(f"{name} — SlicEngine "
                                   f"{self.engine.title}")

    def open_project(self, project):
        path = project.get("path")
        if path and os.path.exists(path):
            try:
                self.engine.load_package(path)
                self.engine.state = "game"
                return
            except Exception as e:
                self._toast(f"Erro ao abrir: {e}")
        # sem arquivo: cria um mundo vazio com o modo do projeto
        from .world import World
        self.engine.world = World()
        self.engine.mode = project.get("mode", "2d")
        self.engine.editor = None
        self.engine.state = "editor"
        self._toast("Projeto sem arquivo — editor aberto")

    def select_profile(self, profile):
        self.engine.profile_name = profile["name"]
        self.engine.profile_id = profile["id"]
        # preferências do perfil
        st = profile.get("settings", {})
        self.engine.title = st.get("editor_title", "SlicEngine")
        self._toast(f"Perfil: {profile['name']}")

    def create_profile(self):
        name = self.input_text.strip()
        if not name:
            self._toast("Digite o nome do perfil!")
            return
        pid = self.engine.db.create_profile(name)
        self.select_profile(
            {"name": name, "id": pid, "settings": {}})
        self.go(self.MAIN)

    # ------------------------------------------------------------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.screen == self.MAIN:
                    self.engine.running = False
                else:
                    self.go(self.MAIN)
                return
            if self.screen == self.PROFILE_NEW and self.input_focus:
                if ev.key == pygame.K_RETURN:
                    self.create_profile()
                elif ev.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif ev.unicode and ev.unicode.isprintable() and \
                        len(self.input_text) < 24:
                    self.input_text += ev.unicode
                return
            if self.screen == self.NEW:
                if ev.key == pygame.K_1:
                    self.new_mode = "2d"
                elif ev.key == pygame.K_2:
                    self.new_mode = "3d"
                elif ev.key == pygame.K_RETURN:
                    self.open_new_game()
                elif ev.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif ev.unicode and ev.unicode.isprintable() and \
                        len(self.input_text) < 30:
                    self.input_text += ev.unicode
                return
            if self.screen == self.MAIN:
                main = self._main_items()
                if ev.key == pygame.K_1:
                    self._choose_main(0)
                elif ev.key == pygame.K_2 and len(main) > 1:
                    self._choose_main(1)
                elif ev.key == pygame.K_3 and len(main) > 2:
                    self._choose_main(2)
                elif ev.key == pygame.K_4 and len(main) > 3:
                    self._choose_main(3)
                return
            if self.screen == self.PROFILES:
                profs = self._profiles()
                for i in range(min(9, len(profs))):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        self.select_profile(profs[i])
                        return
                if ev.key == pygame.K_n:
                    self.go(self.PROFILE_NEW)
                return
            if self.screen == self.PROJECTS:
                projs = self._projects()
                for i in range(min(9, len(projs))):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        self.open_project(projs[i])
                        return
                return
            if self.screen == self.DEMOS:
                demos = self._demo_items()
                for i in range(len(demos)):
                    if ev.key == getattr(pygame, f"K_{i + 1}"):
                        demos[i][1]()
                        return
                return
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._handle_click(ev.pos)

    def _choose_main(self, index):
        if index == 0:
            self.go(self.PROJECTS)
        elif index == 1:
            self.go(self.NEW)
        elif index == 2:
            self.go(self.PROFILES)
        elif index == 3:
            self.go(self.DEMOS)

    def _handle_click(self, pos):
        mx, my = pos
        items = self._visible_items()
        for i, rect in enumerate(items):
            if rect.collidepoint(mx, my):
                if self.screen == self.MAIN:
                    self._choose_main(i)
                elif self.screen == self.NEW:
                    self.open_new_game()
                elif self.screen == self.PROFILE_NEW:
                    self.create_profile()
                elif self.screen == self.PROJECTS:
                    self.open_project(self._projects()[i])
                elif self.screen == self.PROFILES:
                    self.select_profile(self._profiles()[i])
                elif self.screen == self.DEMOS:
                    self._demo_items()[i][1]()
                return
        # campo de texto
        if self.screen in (self.NEW, self.PROFILE_NEW):
            if self._input_rect().collidepoint(mx, my):
                self.input_focus = True
            else:
                self.input_focus = False

    # ------------------------------------------------------------------
    # Itens de cada tela
    # ------------------------------------------------------------------
    def _main_items(self):
        return ["Jogos / Projetos", "Novo Jogo", "Perfis", "Demos"]

    def _demo_items(self):
        import sys
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        examples = os.path.join(base, "examples")
        def _run(name):
            def _do():
                import subprocess
                pygame.quit()
                subprocess.Popen([sys.executable,
                                  os.path.join(examples, name)])
                self.engine.running = False
            return _do
        return [
            ("Demo FPS 3D (estilo Doom)", _run("demo_fps.py")),
            ("Demo 3D raycasting", _run("demo_3d.py")),
            ("Demo 3D real (polígonos)", _run("demo_3d_real.py")),
            ("Demo 2D plataforma", _run("demo_platform.py")),
            ("Demo 2D tile map", _run("demo_2d.py")),
        ]

    def _visible_items(self):
        sw, sh = self.screen_size()
        # rects verticais dos botões principais
        items = self._main_items() if self.screen == self.MAIN \
            else self._projects() if self.screen == self.PROJECTS \
            else self._profiles() if self.screen == self.PROFILES \
            else self._demo_items() if self.screen == self.DEMOS \
            else []
        y0 = sh // 2 - 20
        rects = []
        for i in range(len(items)):
            rects.append(pygame.Rect(sw // 2 - 160, y0 + i * 48, 320, 40))
        return rects

    def _input_rect(self):
        sw, sh = self.screen_size()
        return pygame.Rect(sw // 2 - 160, sh // 2 + 120, 320, 36)

    def screen_size(self):
        return self.engine.screen.get_size()

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def screen_size(self):
        return self.engine.screen.get_size()

    def draw(self):
        sw, sh = self.screen_size()
        s = self.engine.screen
        s.fill(BG)
        big = self._font(46, True)
        small = self._font(22)
        tiny = self._font(16)

        if self.screen == self.MAIN:
            t = big.render("SlicEngine", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 100))
            sub = small.render(f"Perfil ativo: {self.engine.profile_name}",
                               True, TEXT)
            s.blit(sub, (sw // 2 - sub.get_width() // 2, 170))
            for i, it in enumerate(self._main_items()):
                r = self._visible_items()[i]
                col = BTN_HOVER if r.collidepoint(
                    pygame.mouse.get_pos()) else BTN_BG
                pygame.draw.rect(s, col, r, border_radius=6)
                t = small.render(f"[{i + 1}] {it}", True, TEXT)
                s.blit(t, (r.x + 14, r.y + 8))
            ver = tiny.render(f"SlicEngine {utils.VERSION}  |  "
                              f"ESC = sair", True, DIM)
            s.blit(ver, (12, sh - 30))
        elif self.screen == self.NEW:
            t = big.render("Novo Jogo", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 70))
            lbl = small.render("Nome do jogo:", True, TEXT)
            s.blit(lbl, (sw // 2 - lbl.get_width() // 2, 160))
            ir = self._input_rect()
            pygame.draw.rect(s, BTN_HOVER if self.input_focus else BTN_BG,
                             ir, border_radius=4)
            f = small.render(self.input_text + ("_" if self.input_focus
                                                else ""), True, TEXT)
            s.blit(f, (ir.x + 12, ir.y + 6))
            mode_lbl = small.render(
                f"Modo: {'[1] 2D' if self.new_mode == '2d' else '[2] 3D'}"
                f" raycasting{' (selecione 2 para 3D)' if self.new_mode == '2d' else ''}",
                True, TEXT)
            s.blit(mode_lbl, (sw // 2 - mode_lbl.get_width() // 2, 220))
            btn = pygame.Rect(sw // 2 - 160, sh // 2 + 20, 320, 44)
            pygame.draw.rect(s, BTN_HOVER if btn.collidepoint(
                pygame.mouse.get_pos()) else BTN_BG, btn, border_radius=6)
            t = small.render("Criar e abrir no editor (Enter)", True,
                             TEXT)
            s.blit(t, (btn.x + 16, btn.y + 10))
            hint = tiny.render("ESC = voltar ao menu", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen == self.PROFILE_NEW:
            t = big.render("Novo Perfil", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 70))
            lbl = small.render("Nome do perfil:", True, TEXT)
            s.blit(lbl, (sw // 2 - lbl.get_width() // 2, 160))
            ir = self._input_rect()
            pygame.draw.rect(s, BTN_HOVER if self.input_focus else BTN_BG,
                             ir, border_radius=4)
            f = small.render(self.input_text + ("_" if self.input_focus
                                                else ""), True, TEXT)
            s.blit(f, (ir.x + 12, ir.y + 6))
            btn = pygame.Rect(sw // 2 - 160, sh // 2 + 20, 320, 44)
            pygame.draw.rect(s, BTN_HOVER if btn.collidepoint(
                pygame.mouse.get_pos()) else BTN_BG, btn, border_radius=6)
            t = small.render("Criar perfil (Enter)", True, TEXT)
            s.blit(t, (btn.x + 16, btn.y + 10))
            hint = small.render("Ou pressione N de volta na tela Perfis "
                                "para cancelar", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen in (self.PROJECTS, self.PROFILES):
            title = "Meus Jogos" if self.screen == self.PROJECTS \
                else "Perfis"
            t = big.render(title, True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 60))
            items = (self._projects() if self.screen == self.PROJECTS
                     else self._profiles())
            if not items:
                none_ = small.render("Nada por aqui ainda — crie um "
                                     "novo jogo ou perfil!", True, DIM)
                s.blit(none_, (sw // 2 - none_.get_width() // 2,
                               sh // 2))
            y = 150
            for i, it in enumerate(items):
                r = pygame.Rect(sw // 2 - 220, y, 440, 44)
                if r.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(s, BTN_HOVER, r, border_radius=6)
                if self.screen == self.PROFILES:
                    s.blit(self._avatar(it["name"]), (r.x + 6, r.y + 2))
                    nm = small.render(
                        f"[{i + 1}] {it['name']}", True, TEXT)
                    s.blit(nm, (r.x + 54, r.y + 8))
                    stats = tiny.render(
                        f"{len(self.engine.db.list_projects(it['id']))} "
                        f"jogo(s)", True, DIM)
                    s.blit(stats, (r.x + 360, r.y + 14))
                else:
                    nm = small.render(
                        f"[{i + 1}] {it['title']}", True, TEXT)
                    s.blit(nm, (r.x + 14, r.y + 8))
                    mode = tiny.render(it.get("mode", "2d"), True,
                                       ACCENT)
                    s.blit(mode, (r.x + 380, r.y + 14))
                y += 50
            hint = small.render("ESC = voltar", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))
        elif self.screen == self.DEMOS:
            t = big.render("Demos", True, ACCENT)
            s.blit(t, (sw // 2 - t.get_width() // 2, 60))
            y = 140
            for i, (nome, _) in enumerate(self._demo_items()):
                r = pygame.Rect(sw // 2 - 220, y, 440, 44)
                if r.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(s, BTN_HOVER, r, border_radius=6)
                nm = small.render(f"[{i + 1}] {nome}", True, TEXT)
                s.blit(nm, (r.x + 14, r.y + 8))
                y += 50
            hint = small.render("ESC = voltar", True, DIM)
            s.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 40))

        # toast
        if self.message and self.engine.elapsed > self.message_time:
            self.message = ""
        if self.message:
            f = self._font(24, True)
            t = f.render(self.message, True, (255, 120, 120))
            s.blit(t, (sw // 2 - t.get_width() // 2, 20))

    # ------------------------------------------------------------------
    def update(self, dt):
        # refresh do cursor piscando
        pass
