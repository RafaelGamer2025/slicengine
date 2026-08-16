"""
SlicEngine — Sprites animados.

Carrega strips/sheets de sprites (PNG) e devolve o frame correto
conforme o tempo, com suporte a loop, ping-pong e uma única vez.

Uso:
    from slicengine.spritesheet import AnimatedSprite, Animation

    # strip horizontal: 4 frames lado a lado
    anim = Animation.strip("assets/run.png", frames=4, fps=10)

    # ou frames individuais
    anim = Animation.frames(["f1.png", "f2.png", "f3.png"], fps=12)

    runner = AnimatedSprite(anim, mode="loop")   # loop | once | pingpong
    surface = runner.frame(elapsed=1.3)
    screen.blit(surface, (x, y))

Também dá para fazer animações programáticas (sem arquivos):
    anim = Animation.frames(pygame_surfaces_list, fps=8)
"""
import os
import pygame


class Animation:
    """Sequência de frames com duração por frame."""

    def __init__(self, frames: list, fps=8):
        """frames: lista de pygame.Surface (ou caminhos de imagem)."""
        self.fps = max(1, fps)
        self.frames = []
        for f in frames:
            if isinstance(f, str):
                try:
                    self.frames.append(pygame.image.load(f).convert_alpha())
                except pygame.error:
                    self.frames.append(f)
            else:
                self.frames.append(f)
        self.n = len(self.frames)

    @classmethod
    def strip(cls, path: str, frames: int = 4, fps=8, direction="h"):
        """Divide um sprite sheet em `frames` quadros horizontais (ou 'v'
        para verticais)."""
        sheet = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        if direction == "v":
            cell = sh // frames
            return cls([sheet.subsurface(0, i * cell, sw, cell)
                        for i in range(frames)], fps=fps)
        cell = sw // frames
        return cls([sheet.subsurface(i * cell, 0, cell, sh)
                    for i in range(frames)], fps=fps)

    @classmethod
    def frames(cls, items, fps=8):
        return cls(list(items), fps=fps)


class AnimatedSprite:
    """Reprodutor de uma Animation.

    modos:
        "loop"     — repete indefinidamente
        "once"     — para no último frame e define .finished=True
        "pingpong" — vai e volta
    """

    def __init__(self, anim: Animation, mode="loop", start=0.0):
        self.anim = anim
        self.mode = mode
        self.elapsed = start
        self.finished = False
        self._dir = 1

    def update(self, dt):
        self.elapsed += dt
        total = self.anim.n / max(1, self.anim.fps)
        if self.mode == "loop":
            self.elapsed %= total if total > 0 else 1.0
        elif self.mode == "once":
            if self.elapsed >= total:
                self.elapsed = total - 1e-6
                self.finished = True
        elif self.mode == "pingpong":
            self.elapsed = self.elapsed  # tratado em frame_index()
        # (dir atualizado em frame_index)

    @property
    def frame_index(self):
        """Índice do frame atual (pingpong reflete)."""
        n = self.anim.n
        if n == 0:
            return 0
        per = 1.0 / max(1, self.anim.fps)
        if self.mode == "pingpong":
            cycle = 2 * (n - 1)
            t = self.elapsed / per
            i = int(t) % cycle if cycle else 0
            if i >= n:
                i = cycle - i
            return min(max(i, 0), n - 1)
        return min(int(self.elapsed / per), n - 1)

    def frame(self, elapsed=None):
        if elapsed is not None:
            self.elapsed = elapsed
        idx = self.frame_index
        if idx >= self.anim.n:
            idx = self.anim.n - 1
        return self.anim.frames[idx] if self.anim.frames \
            else pygame.Surface((1, 1))


class SpriteAtlas:
    """Atalho: carrega vários AnimatedSprite por nome (para o editor e
    o jogo 2D)."""

    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self._cache = {}

    def get(self, name: str, path: str, frames=1, fps=8) -> AnimatedSprite:
        if name in self._cache:
            return self._cache[name]
        full = os.path.join(self.base_dir, path)
        if frames > 1:
            anim = Animation.strip(full, frames=frames, fps=fps)
        else:
            try:
                surf = pygame.image.load(full).convert_alpha()
            except pygame.error:
                surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                surf.fill((150, 150, 150))
            anim = Animation([surf], fps=fps)
        runner = AnimatedSprite(anim, mode="loop")
        self._cache[name] = runner
        return runner
