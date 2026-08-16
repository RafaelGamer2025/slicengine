"""
SlicEngine — Linguagem de script em PORTUGUÊS (.sl).

Sintaxe inspirada em eventos "quando X acontecer → faça Y".
Cada arquivo é uma lista de REGRAS (event handlers):

    quando tecla "espaço" for pressionada:
        aumentar 1 no "JOGO"
        tocar som "pulo.wav"
        mover jogador 0 para cima

    quando colidir com "moeda":
        aumentar 1 no "PONTOS"
        destruir evento
        mostrar texto "Moeda coletada!" por 2 segundos

    sempre (a cada frame):
        se "vida" menor que 0:
            mostrar texto "Fim de jogo!" por 3 segundos
            parar jogo

Palavras-chave (eventos):
    quando, sempre, colidir, tecla, tocar, soltar_tecla
Palavras-chave (ações):
    aumentar N em/na/no "VAR" | "VAR"
    diminuir N ...
    definir "VAR" para VALOR
    tocar som "arquivo"
    parar música / tocar música "arquivo"
    mover jogador N para cima/baixo/esquerda/direita
    mostrar texto "..." por N segundos
    destruir evento
    parar jogo
    carregar mapa "arquivo"
    se ... então (blocos condicionais simples)
Condições: maior/menor/igual, verdadeiro/falso, tecla pressionada

O interpretador converte o script em Python e executa dentro de um
contexto fornecido pela engine (api = dict de funções).
"""
import re
import keyword

# ----------------------------------------------------------------------
# Dicionário de tradução PT -> operação interna
# ----------------------------------------------------------------------
KEY_MAP = {
    "espaço": "space", "espaco": "space",
    "cima": "up", "baixo": "down", "esquerda": "left", "direita": "right",
    "sim": "true", "verdadeiro": "true", "não": "false", "nao": "false",
}

DIRS = {"cima": (0, -1), "baixo": (0, 1), "esquerda": (-1, 0), "direita": (1, 0)}


def unquote(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def translate_cond(cond: str) -> str:
    """Traduz condição em PT para expressão Python."""
    cond = cond.strip().rstrip(":").strip()
    for pt, py in [("maior que", ">"), ("menor que", "<"), ("igual a", "=="),
                   ("igual", "=="), ("diferente de", "!=")]:
        if pt in cond:
            left, right = cond.split(pt, 1)
            l = _expr(left.strip())
            r = _expr(right.strip())
            return f"({l}) {py} ({r})"
    if "tecla" in cond and "pressionada" in cond:
        m = re.search(r'tecla\s+"([^"]+)"', cond)
        key = m.group(1) if m else "space"
        key = KEY_MAP.get(key.lower(), key)
        return f"api['tecla_pressionada']('{key}')"
    if "verdadeiro" in cond or "falso" in cond:
        var = unquote(cond.replace("verdadeiro", "").replace("falso", "").strip())
        return f"bool(api['get_var']('{var}'))"
    return _expr(cond)


def _expr(s: str) -> str:
    s = s.strip()
    if s.lower() == "verdadeiro":
        return "True"
    if s.lower() in ("falso", "não", "nao"):
        return "False"
    if s.startswith('"') or s.startswith("'"):
        return repr(unquote(s))
    try:
        return str(int(s))
    except ValueError:
        try:
            return str(float(s))
        except ValueError:
            return f"api['get_var']('{s}')"


def translate_action(line: str) -> str:
    """Traduz uma linha de ação PT para Python."""
    line = line.strip().rstrip(",;").strip()
    low = line.lower()

    # aumentar N em "VAR" / no VAR
    m = re.match(r'aumentar\s+(-?\d+(?:\.\d+)?)\s+(?:em|na|no)\s+"([^"]+)"', line)
    if not m:
        m = re.match(r'aumentar\s+(-?\d+(?:\.\d+)?)\s+(?:em|na|no)\s+(\w[\w ]*)', line)
    if m:
        n, var = m.group(1), m.group(2).strip()
        return f"api['add_var']('{var}', {n})"

    m = re.match(r'diminuir\s+(-?\d+(?:\.\d+)?)\s+(?:em|na|no)\s+"([^"]+)"', line)
    if not m:
        m = re.match(r'diminuir\s+(-?\d+(?:\.\d+)?)\s+(?:em|na|no)\s+(\w[\w ]*)', line)
    if m:
        n, var = m.group(1), m.group(2).strip()
        return f"api['add_var']('{var}', -({n}))"

    m = re.match(r'definir\s+"([^"]+)"\s+para\s+(.+)', line)
    if not m:
        m = re.match(r'definir\s+(\w[\w ]*)\s+para\s+(.+)', line)
    if not m:
        m = re.match(r'definir\s+"([^"]+)"\s+como\s+(.+)', line)
    if not m:
        m = re.match(r'definir\s+(\w[\w ]*)\s+como\s+(.+)', line)
    if m:
        var, val = m.group(1).strip(), m.group(2).strip()
        return f"api['set_var']('{var}', {_expr(val)})"

    if low.startswith("tocar som"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            return f"api['tocar_som']('{m.group(1)}')"

    if low.startswith("tocar música") or low.startswith("tocar musica"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            return f"api['tocar_musica']('{m.group(1)}')"

    if "parar música" in low or "parar musica" in low:
        return "api['parar_musica']()"

    m = re.match(r'mover\s+jogador\s+(?:o\s+)?(-?\d+(?:\.\d+)?)\s+(?:para|na\s+dire[çc][ãa]o\s+da\s+)?(\w+)', line)
    if not m:
        m = re.match(r'mover\s+jogador\s+(\w+)\s+(?:por\s+|para\s+)?(-?\d+(?:\.\d+)?)', line)
    if m:
        n = float(m.group(1))
        d = m.group(2)
        dkey = KEY_MAP.get(d.lower(), d.lower())
        dx, dy = DIRS.get(dkey, (0, 0))
        if dx == 0 and dy == 0 and d.lower() in ("cima", "baixo"):
            dy = -1 if d.lower() == "cima" else 1
        elif d.lower() in ("esquerda", "direita"):
            dx = -1 if d.lower() == "esquerda" else 1
        return f"api['mover_jogador']({dx * n}, {dy * n})"

    if low.startswith("mostrar texto"):
        m = re.search(r'"([^"]+)"', line)
        texto = m.group(1) if m else ""
        m2 = re.search(r'por\s+(-?\d+(?:\.\d+)?)', line)
        dur = float(m2.group(1)) if m2 else 2.0
        return f"api['mostrar_texto']('{texto}', {dur})"

    if "destruir" in low and "evento" in low:
        # mata a entidade informada no payload (ex.: colidir:moeda),
        # ou o primeiro alvo vivo encontrado
        return ("for _e in _engine.world.entities:\n"
                "            if _e.alive:\n"
                "                _e.alive = False\n"
                "                break")

    if "parar jogo" in low or "parar o jogo" in low:
        return "api['parar_jogo']()"

    if low.startswith("carregar mapa"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            return f"api['carregar_mapa']('{m.group(1)}')"

    if low.startswith("spawn") or (low.startswith("criar") and
                                   "entidade" in low):
        m = re.search(r'"([^"]+)"', line)
        if m:
            return f"api['criar_entidade']('{m.group(1)}')"

    # criar entidade "tipo" (sem a palavra entidade)
    m = re.match(r'criar\s+"([^"]+)"', line)
    if m:
        return f"api['criar_entidade']('{m.group(1)}')"

    # comando genérico: tentar como nome de função API
    m = re.match(r'(\w[\w ]*?)\s*\((.*)\)', line)
    if m:
        fn, args = m.group(1).strip(), m.group(2)
        return f"api['{fn}']({args})" if args else f"api['{fn}']()"

    return f"# ação não reconhecida: {line}"


def compile_ptscript(source: str) -> str:
    """Compila script .sl (português) para código Python."""
    lines = source.splitlines()
    out = ["# código gerado pelo compilador SlicEngine (.sl -> python)",
           "import sys", "_stop = [False]", ""]
    i = 0
    rules = []
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip().lower()

        # regra: quando <evento>:
        m = re.match(r'quando\s+(.+?):\s*$', stripped)
        m_sempre = re.match(r'sempre\s*:\s*$', stripped)
        if m or m_sempre:
            evt = m.group(1).strip() if m else "sempre"
            # descobrir indentação do bloco
            indent_re = None
            block = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == "":
                    j += 1
                    continue
                if indent_re is None:
                    indent_re = re.match(r'^( +)', nxt)
                    if not indent_re:
                        break
                    base = len(indent_re.group(1))
                # linha pertence ao bloco se estiver indentada >= base
                m2 = re.match(r'^ {' + str(base) + r',}(.+)$', nxt)
                if not m2:
                    break
                inner = nxt[base:]
                block.append(inner)
                j += 1
            py = _compile_block(block, base_indent=2)
            rules.append((evt, "\n".join(py)))
            i = j
            continue
        i += 1

    # gerar uma função por regra e registrá-la (corpo já vem indentado)
    out.append("def registrar(engine):")
    out.append("    _engine = engine")
    idx = 0
    for evt, body in rules:
        evt_py = translate_event(evt)
        fname = f"_handler_{idx}"
        idx += 1
        out.append(f"    def {fname}(api, payload=None):")
        for line in body.splitlines():
            out.append(line)
        out.append(f"    engine.adicionar_evento('{evt_py}', {fname})")
    out.append("")
    return "\n".join(out)


def _compile_block(block: list, base_indent=0) -> list:
    """Compila bloco com suporte a 'se ... então' aninhado.
    base_indent: níveis de indentação adicionais (para handlers)."""
    pad = "    " * base_indent
    out = []
    j = 0
    while j < len(block):
        line = block[j]
        s = line.strip().lower()
        if s.startswith("se ") and s.endswith(":"):
            cond = line.strip()[3:-1].strip()
            sub = []
            j += 1
            while j < len(block):
                inner = block[j]
                if inner.strip() == "":
                    j += 1
                    continue
                if re.match(r'^ {4,}(.+)$', inner):
                    sub.append(inner[4:].strip())
                    j += 1
                elif inner.strip().startswith("senão") or inner.strip().startswith("senao"):
                    j += 1
                    while j < len(block) and re.match(r'^ {4,}(.+)$', block[j]):
                        j += 1
                    break
                else:
                    break
            py_cond = translate_cond(cond)
            out.append(f"{pad}if {py_cond}:")
            for a in sub:
                out.append(pad + "    " + translate_action(a))
            continue
        out.append(pad + translate_action(line))
        j += 1
    return out


def translate_event(evt: str) -> str:
    """Traduz descrição de evento PT para id interno."""
    e = evt.strip().lower()
    m = re.match(r'tecla\s+"([^"]+)"\s+(?:for\s+)?pressionada', e)
    if m:
        key = KEY_MAP.get(m.group(1), m.group(1))
        return f"tecla:{key}"
    m = re.match(r'tecla\s+"([^"]+)"\s+soltar?', e)
    if m:
        key = KEY_MAP.get(m.group(1), m.group(1))
        return f"tecla_up:{key}"
    if "colidir" in e:
        m = re.search(r'"([^"]+)"', evt)
        alvo = m.group(1) if m else "*"
        return f"colidir:{alvo}"
    if e == "sempre" or e.startswith("a cada frame"):
        return "update"
    if "iniciar" in e or "começar" in e or "comecar" in e:
        return "iniciar"
    if "jogador entrar" in e or "inimigo entrar" in e:
        return "colidir:*"
    return "update"


class PTScript:
    """Carrega e executa um script .sl dentro da engine."""

    def __init__(self, source: str):
        self.source = source
        self.code = compile_ptscript(source)
        self.namespace = {}

    def register(self, engine):
        """Registra os eventos do script na engine."""
        ns = {}
        try:
            exec(compile(self.code, "<ptscript>", "exec"), ns)
        except Exception as err:
            raise RuntimeError(f"Erro ao compilar script em português:\n{err}\n{self.code}")
        reg = ns.get("registrar")
        if reg:
            reg(engine)
        self.namespace = ns

    @property
    def generated_code(self):
        """Código Python gerado (útil para debug)."""
        return self.code
