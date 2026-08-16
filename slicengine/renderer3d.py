"""
SlicEngine — Renderizador 3D real (não raycasting).

Módulo de projeção 3D por software baseado em triângulos:
- Câmera com posição, rotação (yaw/pitch) e FOV
- Projeção perspectiva de vértices
- Rasterização de triângulos preenchidos (scanline) com z-buffer
- Luz direcional simples (produto escalar com a normal)
- Malhas, cubos e primitivas pré-montadas

É o modo "3D real" da engine — diferente do modo raycasting
(slicengine.raycaster), que é o estilo Doom.

Uso rápido::

    scene = Scene3D()
    scene.add_cube(0, 0, 4, color=(0, 150, 255))
    renderer = Renderer3D(screen, scene, camera_pos=(0, 1.6, 0))
    renderer.draw()
"""
import math
import pygame


# ---------- matemática 3D básica ----------

def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vec_len(a):
    return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)


def vec_norm(a):
    l = vec_len(a)
    if l < 1e-9:
        return a
    return (a[0] / l, a[1] / l, a[2] / l)


def rotate_y(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (c * v[0] + s * v[2], v[1], -s * v[0] + c * v[2])


def rotate_x(v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (v[0], c * v[1] - s * v[2], s * v[1] + c * v[2])


class Mesh:
    """Malha 3D: lista de triângulos (3 vértices em espaço de objeto)
    com cores ou uma cor por face."""

    def __init__(self, triangles, colors=None):
        """
        ``triangles``: lista de tuplas de 3 vértices ((x,y,z),...).
        ``colors``: lista de cores RGB, uma por triângulo; se ``None``,
        a cor padrão é cinza.
        """
        self.triangles = triangles
        self.colors = colors or [(150, 150, 150)] * len(triangles)

    @staticmethod
    def cube(size=1.0, position=(0.0, 0.0, 0.0), color=None):
        """Cria um cubo com 12 triângulos (6 faces), cada face com
        um tom levemente diferente para dar profundidade."""
        s = size / 2
        x, y, z = position
        verts = [
            (x - s, y - s, z - s), (x + s, y - s, z - s),
            (x + s, y + s, z - s), (x - s, y + s, z - s),
            (x - s, y - s, z + s), (x + s, y - s, z + s),
            (x + s, y + s, z + s), (x - s, y + s, z + s),
        ]
        base = color or (180, 60, 60)
        # faces: 4 vértices cada, divididas em 2 triângulos
        faces = [
            ([verts[0], verts[1], verts[2], verts[3]], 0.85),  # frente
            ([verts[5], verts[4], verts[7], verts[6]], 0.85),  # trás
            ([verts[4], verts[0], verts[3], verts[7]], 0.70),  # esq
            ([verts[1], verts[5], verts[6], verts[2]], 0.70),  # dir
            ([verts[3], verts[2], verts[6], verts[7]], 1.00),  # topo
            ([verts[4], verts[5], verts[1], verts[0]], 0.55),  # baixo
        ]
        tris, cols = [], []
        for quad, shade in faces:
            c = tuple(int(v * shade) for v in base)
            tris.append((quad[0], quad[1], quad[2]))
            tris.append((quad[0], quad[2], quad[3]))
            cols.extend([c, c])
        return Mesh(tris, cols)

    @staticmethod
    def pyramid(base=1.0, height=1.5, position=(0.0, 0.0, 0.0),
                color=None):
        """Pirâmide de 4 faces triangulares."""
        x, y, z = position
        s = base / 2
        apex = (x, y + height / 2, z)
        base_verts = [
            (x - s, y - height / 2, z - s),
            (x + s, y - height / 2, z - s),
            (x + s, y - height / 2, z + s),
            (x - s, y - height / 2, z + s),
        ]
        c = color or (60, 180, 60)
        shades = [0.9, 0.8, 0.7, 1.0]
        tris, cols = [], []
        for i in range(4):
            tris.append((base_verts[i], base_verts[(i + 1) % 4], apex))
            cols.append(tuple(int(v * shades[i]) for v in c))
        # base
        tris.append((base_verts[0], base_verts[2], base_verts[1]))
        tris.append((base_verts[0], base_verts[3], base_verts[2]))
        cols.extend([tuple(int(v * 0.5) for v in c)] * 2)
        return Mesh(tris, cols)

    @staticmethod
    def ground(size=40.0, position=(0.0, 0.0, 1.0),
               color=(60, 110, 60), tiles=8):
        """Chão quadriculado: um grid plano de triângulos.

        Por padrão o chão começa logo à frente da câmera (z=1) e se
        estende por ``size`` tiles, evitando vértices atrás da câmera."""
        x0, _, z0 = position
        step = size / tiles
        tris, cols = [], []
        for i in range(tiles):
            for j in range(tiles):
                a = (x0 + i * step, 0, z0 + j * step)
                b = (x0 + (i + 1) * step, 0, z0 + j * step)
                c_ = (x0 + (i + 1) * step, 0, z0 + (j + 1) * step)
                d = (x0 + i * step, 0, z0 + (j + 1) * step)
                check = (i + j) % 2 == 0
                c1 = color if check else tuple(int(v * 1.25) for v in color)
                c2 = color if not check else tuple(int(v * 0.85)
                                                   for v in color)
                tris.append((a, b, c_))
                tris.append((a, c_, d))
                cols.extend([c1, c2])
        return Mesh(tris, cols)


class Scene3D:
    """Coleção de malhas posicionadas no mundo 3D."""

    def __init__(self):
        self.meshes = []          # (mesh, posição, rotação yaw)
        self.ambient = 0.35       # luz ambiente
        self.light_dir = vec_norm((0.4, -0.8, -0.3))   # direção da luz

    def add(self, mesh, position=(0, 0, 0), yaw=0.0):
        self.meshes.append((mesh, position, yaw))

    def add_cube(self, x=0, y=0, z=0, size=1.0, color=None):
        self.add(Mesh.cube(size, position=(x, y, z), color=color))

    def add_pyramid(self, x=0, y=0, z=0, color=None):
        self.add(Mesh.pyramid(position=(x, y, z), color=color))

    def clear(self):
        self.meshes = []


class Renderer3D:
    """Renderizador 3D por software com projeção perspectiva e
    rasterização de triângulos.

    Não é raycasting: projeta vértices reais em espaço 3D para a tela,
    como os renderizadores 3D clássicos (Gouraud simples)."""

    def __init__(self, screen, scene, camera_pos=(0, 1.6, 0),
                 yaw=0.0, pitch=0.0, fov=70.0, near=0.05, far=200.0):
        self.screen = screen
        self.scene = scene
        self.cam_pos = list(camera_pos)
        self.yaw = yaw
        self.pitch = pitch
        self.fov = fov
        self.near = near
        self.far = far
        self.w, self.h = screen.get_size()
        self.zbuf = None

    # ------------------------------------------------------------------
    def _project(self, v):
        """Transforma um vértice do mundo para coordenadas de tela.
        Retorna (sx, sy, z_camera) ou None se atrás da câmera/longe."""
        p = vec_sub(v, tuple(self.cam_pos))
        p = rotate_y(p, -self.yaw)
        p = rotate_x(p, -self.pitch)
        z = p[2]
        if z <= self.near or z >= self.far:
            return None
        f = (self.w / 2) / math.tan(math.radians(self.fov) / 2)
        return (self.w / 2 + p[0] * f / z,
                self.h / 2 - p[1] * f / z,
                z)

    def _shade(self, tri, idx):
        """Intensidade de luz da face (normal . direção da luz)."""
        a, b, c = tri
        n = vec_cross(vec_sub(b, a), vec_sub(c, a))
        if vec_len(n) < 1e-9:
            return self.scene.ambient
        n = vec_norm(n)
        lambert = max(0.0, vec_dot(n, self.scene.light_dir))
        return min(1.0, self.scene.ambient + lambert * 0.7)

    # ------------------------------------------------------------------
    def _rasterize(self, sx, sy, sz, c1, c2, c3):
        """Rasterização de triângulo com interpolação de cor e z-buffer.
        (sx, sy, sz) = 3 listas de coordenadas de tela já projetadas."""
        # ordenar vértices por y
        order = sorted(range(3), key=lambda i: sy[i])
        y0, y1, y2 = sy[order[0]], sy[order[1]], sy[order[2]]
        x0, x1, x2 = sx[order[0]], sx[order[1]], sx[order[2]]
        z0, z1, z2 = sz[order[0]], sz[order[1]], sz[order[2]]
        cr0, cg0, cb0 = c1
        cr1, cg1, cb1 = c2
        cr2, cg2, cb2 = c3
        ymin, ymax = int(max(0, y0)), int(min(self.h - 1, y2))
        pixels = pygame.PixelArray(self.screen)
        try:
            for y in range(ymin, ymax + 1):
                if y2 == y0:
                    continue
                if y <= y1:
                    t = (y - y0) / (y1 - y0) if y1 != y0 else 0
                    t2 = (y - y0) / (y2 - y0)
                else:
                    t = (y - y1) / (y2 - y1) if y2 != y1 else 1
                    t2 = (y - y0) / (y2 - y0)
                xa = x0 + (x1 - x0) * t
                za = z0 + (z1 - z0) * t
                ra = cr0 + (cr1 - cr0) * t
                ga = cg0 + (cg1 - cg0) * t
                ba = cb0 + (cb1 - cb0) * t
                xb = x0 + (x2 - x0) * t2
                zb = z0 + (z2 - z0) * t2
                rb = cr0 + (cr2 - cr0) * t2
                gb = cg0 + (cg2 - cg0) * t2
                bb = cb0 + (cb2 - cb0) * t2
                if xa > xb:
                    xa, xb, za, zb, ra, rb, ga, gb, ba, bb = \
                        xb, xa, zb, za, rb, ra, gb, ga, bb, ba
                x_start = int(max(0, xa))
                x_end = int(min(self.w - 1, xb))
                width = xb - xa
                if width < 1e-6:
                    continue
                for x in range(x_start, x_end + 1):
                    u = (x - xa) / width
                    zc = za + (zb - za) * u
                    if self.zbuf is None or zc <= self.zbuf[y][x]:
                        self.zbuf[y][x] = zc
                        r = int(ra + (rb - ra) * u)
                        g = int(ga + (gb - ga) * u)
                        b = int(ba + (bb - ba) * u)
                        try:
                            pixels[x][y] = ((b & 0xff) << 24 |
                                            (r << 16) | (g << 8) | 0)
                        except (IndexError, ValueError):
                            pass
        finally:
            del pixels

    # ------------------------------------------------------------------
    def draw(self):
        """Renderiza toda a cena no screen (limpa com céu e chão)."""
        self.w, self.h = self.screen.get_size()
        # céu azul e chão com horizonte (fundo inicial)
        for y in range(self.h):
            if y < self.h // 2:
                t = y / (self.h // 2)
                r, g, b = int(40 + 60 * t), int(60 + 90 * t), int(120 + 80 * t)
            else:
                t = (y - self.h // 2) / (self.h // 2)
                r, g, b = int(90 + 40 * t), int(130 + 30 * t), int(90 + 30 * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y),
                             (self.w, y))
        self.zbuf = [[float("inf")] * self.w for _ in range(self.h)]

        # coletar todos os triângulos da cena (com transformação)
        all_tris = []   # (dist_ordenada, projected_pts, cores)
        for mesh, pos, yaw in self.scene.meshes:
            for tri, color in zip(mesh.triangles, mesh.colors):
                world = [rotate_y(vec_add(v, pos), yaw) for v in tri]
                proj = [self._project(v) for v in world]
                if any(p is None for p in proj):
                    continue
                sx = [p[0] for p in proj]
                sy = [p[1] for p in proj]
                sz = [p[2] for p in proj]
                shade = self._shade(world, 0)
                r = int(color[0] * shade)
                g = int(color[1] * shade)
                b = int(color[2] * shade)
                mid_z = (sz[0] + sz[1] + sz[2]) / 3
                all_tris.append(((sx, sy, sz), r, g, b, mid_z))

        # painter's algorithm + z-buffer: desenhar do mais longe ao
        # mais perto e o z-buffer garante ordem correta por pixel
        all_tris.sort(key=lambda t: -t[4])
        for (sx, sy, sz), r, g, b, _ in all_tris:
            self._rasterize(sx, sy, sz, (r, g, b), (r, g, b), (r, g, b))

        # refazer só o chão: os triângulos do chão são grandes demais
        # e o ordenamento por z médio falha quando cobrem a câmera.
        # Desenhamos o chão DEPOIS dos objetos usando o z-buffer por
        # pixel, mas apenas se o chão estiver MESMO atrás dos pixels
        # já preenchidos — então na verdade o chão foi desenhado
        # primeiro como malha (longe -> perto), e o z-buffer impediu
        # que cubos atrás fossem desenhados? Não: o chão está em y=0,
        # z grande; cubos perto têm z menor e passam no z-test.
        # O problema do screenshot era que o chão estava na lista E
        # os cubos eram rasterizados antes do chão (z médio maior).
        # Com o z-buffer pixel a pixel o resultado já sai correto.
