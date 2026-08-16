"""
SlicEngine — Gerenciador de assets.

Importa e armazena em cache:
- Sprites (PNG, JPG, GIF, BMP)
- Sons (WAV, OGG)
- Músicas (MP3, OGG — streaming)
- GIFs animados (sequência de frames para menus)
"""
import os
import pygame
from PIL import Image


SUPPORTED_IMG = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
SUPPORTED_SFX = (".wav", ".ogg")
SUPPORTED_MUSIC = (".mp3", ".ogg", ".wav")


def _is_music(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in SUPPORTED_MUSIC and \
        os.path.splitext(path)[1].lower() != ".wav"


class AssetManager:
    def __init__(self, base_dir="."):
        self.base_dir = os.path.abspath(base_dir)
        self.sprites = {}
        self.sounds = {}
        self.musics = {}
        self.gifs = {}

    def _abs(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(self.base_dir, path)

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------
    def sprite(self, path: str, colorkey=None) -> pygame.Surface:
        if path in self.sprites:
            return self.sprites[path]
        surf = pygame.image.load(self._abs(path)).convert_alpha()
        if colorkey is not None:
            surf.set_colorkey(colorkey)
        self.sprites[path] = surf
        return surf

    def sprite_raw(self, path: str) -> pygame.Surface:
        """Carrega sem converter alpha (para tiles opacos)."""
        if path in self.sprites:
            return self.sprites[path]
        surf = pygame.image.load(self._abs(path)).convert()
        self.sprites[path] = surf
        return surf

    # ------------------------------------------------------------------
    # Som (efeitos)
    # ------------------------------------------------------------------
    def sound(self, path: str) -> "Sound":
        if path in self.sounds:
            return self.sounds[path]
        s = Sound(self._abs(path))
        self.sounds[path] = s
        return s

    # ------------------------------------------------------------------
    # Música (streaming)
    # ------------------------------------------------------------------
    def music(self, path: str, volume=0.7):
        pygame.mixer.music.load(self._abs(path))
        pygame.mixer.music.set_volume(volume)
        self.musics[path] = path

    def music_play(self, path: str, volume=0.7, loops=-1):
        self.music(path, volume)
        pygame.mixer.music.play(loops)

    def music_stop(self):
        pygame.mixer.music.stop()

    # ------------------------------------------------------------------
    # GIF animado
    # ------------------------------------------------------------------
    def gif(self, path: str, scale=1.0, fps=10) -> "GifPlayer":
        if path in self.gifs:
            return self.gifs[path]
        g = GifPlayer(self._abs(path), scale, fps)
        self.gifs[path] = g
        return g


class Sound:
    def __init__(self, path: str):
        self.path = path
        self._channel = None
        try:
            self._snd = pygame.mixer.Sound(path)
        except pygame.error:
            self._snd = None

    def play(self, volume=0.6, loops=0):
        if self._snd is not None:
            self._snd.set_volume(volume)
            self._channel = self._snd.play(loops)
            return self._channel is not None
        return False

    def stop(self):
        if self._channel is not None:
            self._channel.stop()


class GifPlayer:
    """Toca GIF animado (menu, fundo, cutscenes)."""

    def __init__(self, path: str, scale=1.0, fps=10):
        self.path = path
        self.frames: list[pygame.Surface] = []
        self.durations: list[float] = []
        self.fps = fps
        self._load(path, scale)

    def _load(self, path: str, scale: float):
        img = Image.open(path)
        if getattr(img, "n_frames", 1) <= 1:
            surf = pygame.image.load(path).convert_alpha()
            self.frames = [surf]
            self.durations = [1.0 / self.fps]
            return
        info = getattr(img, "info", {})
        dur = info.get("duration", 100) / 1000.0
        frame = 0
        while True:
            try:
                img.seek(frame)
                f = img.convert("RGBA")
                surf = pygame.image.fromstring(
                    f.tobytes(), f.size, "RGBA").convert_alpha()
                if scale != 1.0:
                    w, h = surf.get_size()
                    surf = pygame.transform.scale(
                        surf, (max(1, int(w * scale)), max(1, int(h * scale))))
                self.frames.append(surf)
                fdur = getattr(img, "info", {}).get("duration", int(dur * 1000))
                self.durations.append(fdur / 1000.0)
                frame += 1
            except EOFError:
                break
        if not self.frames:
            self.frames = [pygame.Surface((64, 64))]
            self.durations = [0.1]

    @property
    def size(self):
        if self.frames:
            return self.frames[0].get_size()
        return (0, 0)

    def frame_at(self, elapsed: float) -> pygame.Surface:
        total = sum(self.durations)
        if total <= 0:
            return self.frames[0]
        t = elapsed % total
        acc = 0.0
        for s, d in zip(self.frames, self.durations):
            acc += d
            if t <= acc:
                return s
        return self.frames[-1]
