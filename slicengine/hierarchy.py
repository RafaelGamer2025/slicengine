"""
SlicEngine — Sistema de HIERARQUIA (árvore de nós).

Organiza TUDO da cena em uma árvore pai->filhos com prioridade:
- Nós de ASSETS   (quem usa qual sprite/som/gif)
- Nós de SCRIPTS  (ordem de execução por prioridade)
- Nós de COMANDOS (eventos: quem responde primeiro)
- Nós de CÂMERA   (qual câmera manda na cena, viewports)

Uso:
    hier = Hierarchy()
    raiz = hier.root
    jogador = raiz.add_child("Jogador", kind="script", priority=10)
    inimigo = raiz.add_child("Inimigo", kind="script", priority=5)
    cam = raiz.add_child("Câmera", kind="camera", priority=100)
    jogador.add_child("SpriteHerói", kind="asset")

    hier.run_scripts(dt)           # executa na ordem de prioridade
    hier.dispatch("colidir:moeda") # comandos na ordem de prioridade
    cam_ativa = hier.active_camera # câmera de maior prioridade
"""


class HierarchyNode:
    """Nó da árvore de hierarquia."""

    def __init__(self, name: str, kind="node", priority=50, parent=None):
        self.name = name
        self.kind = kind          # "asset", "script", "command", "camera",
                                  # "entity", "node"
        self.priority = priority  # maior = mais importante
        self.parent = parent
        self.children: list[HierarchyNode] = []
        self.enabled = True
        self.data = {}            # payload genérico (sprite, func, cmd...)

    # ------------------------------------------------------------------
    def add_child(self, name, kind="node", priority=50, data=None):
        node = HierarchyNode(name, kind, priority, parent=self)
        if data is not None:
            node.data = data
        self.children.append(node)
        self.children.sort(key=lambda n: -n.priority)
        return node

    def remove_child(self, name_or_node):
        if isinstance(name_or_node, str):
            self.children = [c for c in self.children
                             if c.name != name_or_node]
        else:
            self.children.remove(name_or_node)

    def find(self, name: str):
        """Busca recursiva por nome."""
        if self.name == name:
            return self
        for c in self.children:
            found = c.find(name)
            if found:
                return found
        return None

    def find_all(self, kind: str) -> list:
        out = []
        if self.kind == kind and self.enabled:
            out.append(self)
        for c in self.children:
            out.extend(c.find_all(kind))
        return out

    @property
    def path(self) -> str:
        """Caminho completo: Raiz/Jogador/SpriteHerói."""
        parts = []
        node = self
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return "/".join(reversed(parts))

    def describe(self, indent=0) -> str:
        lines = [" " * indent + f"- {self.name} [{self.kind}] "
                                f"(p={self.priority})"]
        for c in self.children:
            lines.append(c.describe(indent + 2))
        return "\n".join(lines)


class Hierarchy:
    """Árvore de hierarquia completa da cena."""

    def __init__(self):
        self.root = HierarchyNode("Cena", kind="node", priority=0)

    # ------------------------------------------------------------------
    # Atalhos por tipo
    # ------------------------------------------------------------------
    def add_asset(self, name, parent=None, data=None, priority=50):
        p = parent or self.root
        return p.add_child(name, "asset", priority, data)

    def add_script(self, name, func, parent=None, priority=50):
        p = parent or self.root
        return p.add_child(name, "script", priority, {"func": func})

    def add_command(self, name, event_id, func, parent=None, priority=50):
        p = parent or self.root
        return p.add_child(name, "command", priority,
                           {"event": event_id, "func": func})

    def add_camera(self, name, camera_obj, parent=None, priority=50):
        p = parent or self.root
        return p.add_child(name, "camera", priority, {"cam": camera_obj})

    # ------------------------------------------------------------------
    # Execução ordenada
    # ------------------------------------------------------------------
    def scripts(self) -> list:
        """Scripts em ordem de prioridade (maior primeiro)."""
        return self.root.find_all("script")

    def run_scripts(self, dt: float, engine=None):
        for node in self.scripts():
            if node.enabled:
                try:
                    fn = node.data.get("func")
                    if fn is not None:
                        fn(dt, engine)
                except Exception as e:
                    print(f"[Hierarquia] erro em {node.path}: {e}")

    def commands_for(self, event_id: str) -> list:
        """Comandos que respondem a um evento, em ordem de prioridade."""
        return [n for n in self.root.find_all("command")
                if n.data.get("event") in (event_id, "*")]

    def dispatch(self, event_id: str, payload=None) -> bool:
        """Dispara um evento nos comandos registrados.
        Retorna True se alguém respondeu (consumiu o evento)."""
        handled = False
        for node in self.commands_for(event_id):
            if node.enabled:
                try:
                    node.data["func"](payload)
                    handled = True
                except Exception as e:
                    print(f"[Hierarquia] erro no comando {node.path}: {e}")
        return handled

    @property
    def active_camera(self):
        """Câmera ativa = câmera habilitada de maior prioridade."""
        cams = self.root.find_all("camera")
        return cams[0] if cams else None

    def __repr__(self):
        return self.root.describe()
