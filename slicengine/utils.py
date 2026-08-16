"""
SlicEngine — utilitários gerais.
"""
import os
import math
import time

VERSION = "0.2.0"
ENGINE_NAME = "SlicEngine"
SE_EXTENSION = ".se"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t, 0.0, 1.0)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


class FPSCounter:
    def __init__(self):
        self.frames = 0
        self.last_time = time.perf_counter()
        self.fps = 0.0

    def update(self):
        self.frames += 1
        now = time.perf_counter()
        if now - self.last_time >= 1.0:
            self.fps = self.frames / (now - self.last_time)
            self.frames = 0
            self.last_time = now
        return self.fps


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
