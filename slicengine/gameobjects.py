"""
SlicEngine — GameObject / Component / Transform / Scene / SceneManager.

Nova camada arquitetural incremental (MANTER → CORRIGIR → ORGANIZAR →
EXPANDIR). Nenhum módulo existente é alterado: esta camada convive com
a Entity/World atual e pode ser usada sozinha ou junto.

Responsabilidades:

- Transform: sistema espacial oficial (posição local/global, rotação,
  escala, pai/filhos). Uma única implementação — a hierarquia de
  Transform é a fonte da verdade, e o GameObject apenas a referencia.
- Component: unidade reutilizável de comportamento (independente do
  toolkit gráfico). Métodos de ciclo de vida: start, update, on_destroy.
- GameObject: nó da hierarquia com nome, tag, layer, ativos/inativos,
  pai/filhos, componentes e Transform.
- Scene: coleção oficial de GameObjects com metadata, tags e layers.
- SceneManager: gerencia objetos Scene com eventos (criada, carregada,
  trocada, salvada) e histórico simples.
"""
import copy
import json
import uuid as _uuid


# =====================================================================
# EventBus global leve
# =====================================================================

class EventBus:
    """Barramento de eventos global, simples e sem dependências.

    Uso::

        bus = EventBus.shared
        bus.on("SceneLoaded", callback)
        bus.emit("SceneLoaded", scene)
    """

    _shared = None

    def __init__(self):
        self._handlers = {}

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def on(self, event_name, callback):
        self._handlers.setdefault(event_name, []).append(callback)
        return callback

    def off(self, event_name, callback=None):
        if callback is None:
            self._handlers.pop(event_name, None)
        elif event_name in self._handlers:
            self._handlers[event_name] = [
                cb for cb in self._handlers[event_name] if cb != callback]

    def emit(self, event_name, payload=None):
        for cb in list(self._handlers.get(event_name, [])):
            try:
                cb(payload)
            except Exception as e:
                # Logger pode ainda não existir na primeira carga;
                # usamos print seguro.
                try:
                    print(f"[EventBus ERROR] {event_name}: {e}")
                except Exception:
                    pass


# =====================================================================
# Logger central
# =====================================================================

class Logger:
    """Logger central com níveis DEBUG/INFO/WARNING/ERROR/CRITICAL.

    Substitui os ``print()`` espalhados. Mensagens vão para uma lista
    de registro (que pode ser impressa/gravada) e, no nível WARNING+,
    também ao ``print`` padrão."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    _shared = None

    def __init__(self, level=None):
        self.level = level or self.INFO
        self.records = []          # (level, message)
        self._order = [self.DEBUG, self.INFO, self.WARNING,
                       self.ERROR, self.CRITICAL]

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def log(self, level, message):
        self.records.append((level, str(message)))
        if self._order.index(level) >= self._order.index(self.level):
            print(f"[{level}] {message}")

    def debug(self, message):
        self.log(self.DEBUG, message)

    def info(self, message):
        self.log(self.INFO, message)

    def warning(self, message):
        self.log(self.WARNING, message)

    def error(self, message):
        self.log(self.ERROR, message)

    def critical(self, message):
        self.log(self.CRITICAL, message)

    def clear(self):
        self.records = []


# =====================================================================
# Vector2 (leve, usado por Transform)
# =====================================================================

class Vector2:
    """Vetor 2D simples (preparação para Vector3/Matrix no futuro)."""

    def __init__(self, x=0.0, y=0.0):
        self.x, self.y = float(x), float(y)

    def __repr__(self):
        return f"Vector2({self.x:.2f}, {self.y:.2f})"

    def __eq__(self, other):
        return isinstance(other, Vector2) and \
            abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __add__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        return Vector2(self.x + other, self.y + other)

    def __sub__(self, other):
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        return Vector2(self.x - other, self.y - other)

    def __mul__(self, s):
        return Vector2(self.x * s, self.y * s)

    def length(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def normalized(self):
        ln = self.length()
        if ln < 1e-9:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / ln, self.y / ln)

    def to_tuple(self):
        return (self.x, self.y)


# =====================================================================
# Transform
# =====================================================================

class Transform:
    """Sistema espacial oficial: posição local, global, rotação, escala,
    pai e filhos. A hierarquia Transform é a fonte da verdade."""

    def __init__(self):
        self._position = Vector2()
        self._rotation = 0.0      # graus
        self._scale = Vector2(1.0, 1.0)
        self._parent = None
        self._children = []
        self.game_object = None   # vinculado pelo GameObject dono

    # --- propriedades base -------------------------------------------
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if isinstance(value, tuple):
            value = Vector2(*value)
        self._position = value

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        self._rotation = float(value)

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if isinstance(value, tuple):
            value = Vector2(*value)
        self._scale = value

    # --- hierarquia --------------------------------------------------
    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, new_parent):
        if self._parent is new_parent:
            return
        if self._parent is not None:
            self._parent._children.remove(self)
        self._parent = new_parent
        if new_parent is not None and self not in new_parent._children:
            new_parent._children.append(self)

    @property
    def children(self):
        return list(self._children)

    def add_child(self, child):
        child.parent = self

    # --- espaço global -----------------------------------------------
    @property
    def global_position(self):
        pos = self._position
        p = self._parent
        while p is not None:
            angle = p._rotation * 3.141592653589793 / 180.0
            cos_a, sin_a = __import__("math").cos(angle), \
                __import__("math").sin(angle)
            rx = pos.x * cos_a - pos.y * sin_a
            ry = pos.x * sin_a + pos.y * cos_a
            pos = Vector2(p._position.x + rx * p._scale.x,
                          p._position.y + ry * p._scale.y)
            p = p._parent
        return pos

    @global_position.setter
    def global_position(self, value):
        """Converte posição global em local ao definir."""
        import math
        if isinstance(value, tuple):
            value = Vector2(*value)
        p = self._parent
        if p is None:
            self._position = value
            return
        parent_pos = p.global_position
        angle = -p._rotation * math.pi / 180.0
        dx, dy = value.x - parent_pos.x, value.y - parent_pos.y
        rx = dx * math.cos(angle) - dy * math.sin(angle)
        ry = dx * math.sin(angle) + dy * math.cos(angle)
        self._position = Vector2(rx / p._scale.x, ry / p._scale.y)

    @property
    def global_rotation(self):
        total = self._rotation
        p = self._parent
        while p is not None:
            total += p._rotation
            p = p._parent
        return total

    @property
    def global_scale(self):
        sx, sy = self._scale.x, self._scale.y
        p = self._parent
        while p is not None:
            sx *= p._scale.x
            sy *= p._scale.y
            p = p._parent
        return Vector2(sx, sy)


# =====================================================================
# Component
# =====================================================================

class Component:
    """Unidade reutilizável de comportamento. Herde e sobrescreva
    ``update(dt)`` e/ou ``on_destroy()``."""

    def __init__(self):
        self.game_object = None      # dono (definido pelo GameObject)
        self.enabled = True

    def start(self):
        """Chamado uma vez após adicionar ao GameObject."""

    def update(self, dt):
        """Chamado a cada quadro."""

    def on_destroy(self):
        """Chamado quando o dono é destruído."""

    def __repr__(self):
        return f"<{type(self).__name__} enabled={self.enabled}>"


# =====================================================================
# GameObject
# =====================================================================

class GameObject:
    """Nó da hierarquia de jogo: nome, tag, layer, Transform,
    componentes e filhos. Criação, destruição, clonagem e ativação
    suportadas."""

    _next_id = 0

    def __init__(self, name="GameObject"):
        GameObject._next_id += 1
        self.id = GameObject._next_id
        self.name = name
        self.tag = "Untagged"
        self.layer = "Default"
        self.metadata = {}
        self.active = True
        self.transform = Transform()
        self.transform.game_object = self
        self._components = []
        self._destroyed = False

    # --- componentes --------------------------------------------------
    def add_component(self, component):
        if component in self._components:
            return component
        component.game_object = self
        self._components.append(component)
        try:
            component.start()
        except Exception as e:
            Logger.shared().warning(f"Component.start falhou: {e}")
        EventBus.shared().emit("ComponentAdded",
                             {"object": self, "component": component})
        return component

    def get_component(self, component_type):
        for c in self._components:
            if isinstance(c, component_type):
                return c
        return None

    @property
    def components(self):
        return list(self._components)

    def destroy_component(self, component):
        if component in self._components:
            self._components.remove(component)
            try:
                component.on_destroy()
            except Exception as e:
                Logger.shared().warning(f"Component.on_destroy: {e}")

    # --- filhos -------------------------------------------------------
    @property
    def children(self):
        return [t.game_object for t in self.transform.children
                if t.game_object is not None]

    def add_child(self, child):
        child.transform.parent = self.transform

    @property
    def parent(self):
        t = self.transform.parent
        return t.game_object if (t is not None and
                                 t.game_object is not None) else None

    # --- estado -------------------------------------------------------
    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        for c in list(self._components):
            try:
                c.on_destroy()
            except Exception as e:
                Logger.shared().warning(f"Component.on_destroy: {e}")
        self._components.clear()
        for t in list(self.transform.children):
            if t.game_object is not None:
                t.game_object.destroy()
        if self.transform.parent is not None:
            self.transform.parent._children.remove(self.transform)
        self.transform._parent = None
        EventBus.shared().emit("GameObjectDestroyed", self)

    def clone(self, name=None):
        obj = GameObject(name or (self.name + "_clone"))
        obj.tag = self.tag
        obj.layer = self.layer
        obj.metadata = copy.deepcopy(self.metadata)
        obj.transform.position = Vector2(
            self.transform.position.x, self.transform.position.y)
        obj.transform.rotation = self.transform.rotation
        obj.transform.scale = Vector2(self.transform.scale.x,
                                      self.transform.scale.y)
        for c in self._components:
            try:
                nc = copy.deepcopy(c)
            except Exception:
                nc = type(c)()
            obj.add_component(nc)
        return obj

    def set_active(self, value):
        self.active = bool(value)

    def find_children_by_tag(self, tag):
        return [c for c in self.children if c.tag == tag]

    def __repr__(self):
        return (f"<GameObject '{self.name}' tag={self.tag} "
                f"components={len(self._components)}>")


# =====================================================================
# Scene + SceneManager
# =====================================================================

class Scene:
    """Representação oficial de uma cena: GameObjects, metadata, tags e
    layers. Independente da interface gráfica."""

    def __init__(self, name="Scene"):
        self.name = name
        self.metadata = {}
        self.tags = set()
        self.layers = {}           # layer -> {"objects": [...]}
        self._objects = []
        self._destroyed = False

    # --- objetos ------------------------------------------------------
    def add(self, game_object):
        self._objects.append(game_object)
        if game_object.layer not in self.layers:
            self.layers[game_object.layer] = {"objects": []}
        if game_object not in self.layers[game_object.layer]["objects"]:
            self.layers[game_object.layer]["objects"].append(
                game_object)
        EventBus.shared().emit("GameObjectCreated", game_object)
        return game_object

    def remove(self, game_object):
        if game_object in self._objects:
            self._objects.remove(game_object)
            self.layers.get(game_object.layer,
                            {}).get("objects", []).remove(game_object)
            game_object.destroy()
            return True
        return False

    @property
    def objects(self):
        return list(self._objects)

    def find(self, name):
        for o in self._objects:
            if o.name == name:
                return o
        return None

    def find_by_tag(self, tag):
        return [o for o in self._objects if o.tag == tag]

    def find_all(self, component_type):
        return [o for o in self._objects
                if o.get_component(component_type) is not None]

    # --- ciclo de vida ------------------------------------------------
    def update(self, dt):
        for o in list(self._objects):
            if o.active and not o._destroyed:
                for c in o.components:
                    if c.enabled:
                        try:
                            c.update(dt)
                        except Exception as e:
                            Logger.shared().error(
                                f"update de {c} em {o.name}: {e}")

    def save(self, path):
        data = {
            "name": self.name,
            "metadata": self.metadata,
            "tags": sorted(self.tags),
            "layers": {k: [o.name for o in v["objects"]]
                       for k, v in self.layers.items()},
            "objects": [],
        }
        data["objects"] = [
            {"id": o.id, "name": o.name, "tag": o.tag, "layer": o.layer,
             "active": o.active, "metadata": o.metadata,
             "position": o.transform.position.to_tuple(),
             "rotation": o.transform.rotation,
             "scale": o.transform.scale.to_tuple(),
             "components": [
                 {"type": type(c).__name__, "enabled": c.enabled}
                 for c in o.components]}
            for o in self._objects]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        EventBus.shared().emit("SceneSaved", self)
        return path

    @classmethod
    def load(cls, path):
        """Carrega os dados básicos de uma cena salva (sem componentes
        customizados — apenas dados)."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scene = cls(data.get("name", "Scene"))
        scene.metadata = data.get("metadata", {})
        scene.tags = set(data.get("tags", []))
        for odata in data.get("objects", []):
            obj = GameObject(odata.get("name", "GameObject"))
            obj.tag = odata.get("tag", "Untagged")
            obj.layer = odata.get("layer", "Default")
            obj.active = odata.get("active", True)
            obj.metadata = odata.get("metadata", {})
            pos = odata.get("position", (0, 0))
            obj.transform.position = Vector2(pos[0], pos[1])
            obj.transform.rotation = odata.get("rotation", 0)
            sc = odata.get("scale", (1, 1))
            obj.transform.scale = Vector2(sc[0], sc[1])
            scene.add(obj)
        return scene


class SceneManager:
    """Gerencia objetos Scene com eventos, histórico e cena atual.

    Integrado à Engine pelo EventBus: eventos emitidos são
    SceneCreated, SceneLoaded, SceneChanged, SceneUnloaded,
    SceneSaved. Uso::

        sm = SceneManager()
        sm.new_scene("Fase1")          # cria e troca
        sm.change("Menu")              # troca de cena existente
        sm.current                     # cena ativa
    """

    def __init__(self):
        self._scenes = {}
        self._current = None
        self.history = []              # nomes de cenas trocadas
        self._uuid = str(_uuid.uuid4())[:8]

    @property
    def current(self):
        return self._current

    @property
    def scenes(self):
        return dict(self._scenes)

    def new_scene(self, name):
        """Cria uma cena nova e a torna a atual."""
        if name in self._scenes:
            Logger.shared().warning(
                f"Scene '{name}' já existe; usando change().")
            return self.change(name)
        scene = Scene(name)
        self._scenes[name] = scene
        old = self._current
        self._current = scene
        self.history.append(name)
        EventBus.shared().emit("SceneCreated", scene)
        EventBus.shared().emit("SceneLoaded", scene)
        if old is not None:
            EventBus.shared().emit("SceneChanged",
                                 {"from": old, "to": scene})
        return scene

    def change(self, name):
        """Troca para uma cena já criada."""
        if name not in self._scenes:
            Logger.shared().error(f"Scene '{name}' não encontrada.")
            return None
        old = self._current
        if old is not None:
            EventBus.shared().emit("SceneUnloaded", old)
        scene = self._scenes[name]
        self._current = scene
        self.history.append(name)
        EventBus.shared().emit("SceneLoaded", scene)
        EventBus.shared().emit("SceneChanged",
                             {"from": old, "to": scene})
        return scene

    def add_scene(self, scene):
        self._scenes[scene.name] = scene
        EventBus.shared().emit("SceneCreated", scene)
        return scene

    def remove_scene(self, name):
        scene = self._scenes.pop(name, None)
        if scene is not None:
            if self._current is scene:
                self._current = None
            EventBus.shared().emit("SceneUnloaded", scene)
        return scene is not None

    def reload(self, name):
        scene = self._scenes.get(name)
        if scene is None:
            return None
        new_scene = Scene(name)
        new_scene.metadata = scene.metadata
        new_scene.tags = set(scene.tags)
        self._scenes[name] = new_scene
        if self._current is scene:
            old = self._current
            self._current = new_scene
            EventBus.shared().emit("SceneChanged",
                                 {"from": old, "to": new_scene})
        return new_scene

    def duplicate(self, name, new_name):
        scene = self._scenes.get(name)
        if scene is None:
            return None
        import copy
        dup = copy.deepcopy(scene)
        dup.name = new_name
        dup._objects = []            # reconstruir objetos clonados
        for o in scene.objects:
            dup.add(o.clone(o.name))
        self._scenes[new_name] = dup
        EventBus.shared().emit("SceneCreated", dup)
        return dup

    def rename(self, old_name, new_name):
        if old_name not in self._scenes or new_name in self._scenes:
            return False
        scene = self._scenes.pop(old_name)
        scene.name = new_name
        self._scenes[new_name] = scene
        if self._current is scene:
            EventBus.shared().emit("SceneChanged",
                                 {"from": None, "to": scene})
        return True

    def save(self, name, path):
        scene = self._scenes.get(name)
        if scene is None:
            return False
        scene.save(path)
        return True

    def load_file(self, path, name=None):
        scene = Scene.load(path)
        if name:
            scene.name = name
        self._scenes[scene.name] = scene
        EventBus.shared().emit("SceneLoaded", scene)
        return scene

    def update(self, dt):
        if self._current is not None:
            self._current.update(dt)
