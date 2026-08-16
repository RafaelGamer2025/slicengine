"""
SlicEngine — API da engine exposta para scripts Lua (via lupa).

Permite escrever mods e jogos inteiros em Lua:

    engine.set_var("pontos", 0)

    function pegar_moeda(api, dados)
        engine.add_var("pontos", 10)
        api.tocar_som("moeda.wav")
        api.mostrar_texto("Moeda!", 1.5)
    end

    engine.on_event("colidir:moeda", pegar_moeda)

    function atualizar(api, dt)
        -- lógica por frame; dt chega como `dt` (payload do update)
    end
    engine.on_event("update", atualizar)

Assinatura padrão dos callbacks: (api, payload)
- update: payload = dt (float)
- tecla:X / tecla_up:X: payload = nome da tecla
- colidir:tipo: payload = dados da entidade tocada (dict)
- mouse:click: payload = (x, y) do clique

Aliases em português também funcionam:
    engine.mostrar_texto / engine.tocar_som / engine.tocar_musica /
    engine.mover_jogador / engine.criar_entidade / engine.carregar_mapa /
    engine.parar_jogo / engine.parar_musica / engine.pegar /
    engine.adicionar / engine.definir
"""
import lupa


def _wrap_callable(fn, mode="default"):
    """Converte um callback Lua em callable Python compatível com a
    engine (que chama handlers como `fn(api, payload)`).

    mode="default": aceita qualquer assinatura e repassa (api, payload);
    funções que declaram 1 argumento recebem só o payload.
    """
    def wrapper(api_or_none, payload=None):
        try:
            if lupa.lua_type(fn) != "function":
                return fn(api_or_none, payload)
            # lupa não expõe nparams em funções globais; chamar com a
            # assinatura completa (api, payload) — argumentos extras em
            # Lua são simplesmente descartados
            return fn(api_or_none, payload)
        except lupa.LuaError as e:
            print(f"[Lua] erro no callback: {e}")
        except Exception as e:
            print(f"[Lua] erro no callback: {e}")
    return wrapper


def build_lua_api(engine) -> "lupa.LuaRuntime":
    """Cria um runtime Lua com a tabela `engine` cheia de funções
    vinculadas ao estado interno da engine."""
    rt = lupa.LuaRuntime(unpack_returned_tuples=True)

    state = engine.lua_state

    def _push_text(text, dur=2.0):
        # integra com o toast da engine (o core desenha _toast)
        engine._api_mostrar_texto(text, dur)

    api = {
        "window": lambda title, w, h: state.setdefault("window",
                                                       [title, w, h]),
        "get_var": lambda name: state["vars"].get(name, 0),
        "set_var": lambda name, val: state["vars"].__setitem__(name, val),
        "add_var": lambda name, n: state["vars"].__setitem__(
            name, state["vars"].get(name, 0) + n),
        "play_sound": lambda path: state["snd_queue"].append(path),
        "play_music": lambda path: state["mus_queue"].append(path),
        "stop_music": lambda: state["mus_queue"].append(None),
        "show_text": _push_text,
        "stop_game": lambda: state.setdefault("stop", True),
        "move_player": lambda dx, dy: state["player_move"].append([dx, dy]),
        "spawn_entity": lambda kind, x=0.0, y=0.0: state["spawns"].append(
            [kind, x, y]),
        "load_map": lambda path: state.setdefault("load_map", path),
        "log": print,
        # aliases em português (mesma API usada pelos callbacks .sl)
        "mostrar_texto": _push_text,
        "tocar_som": lambda path: state["snd_queue"].append(path),
        "tocar_musica": lambda path: state["mus_queue"].append(path),
        "parar_musica": lambda: state["mus_queue"].append(None),
        "mover_jogador": lambda dx, dy: state["player_move"].append(
            [dx, dy]),
        "criar_entidade": lambda kind: state["spawns"].append(
            [kind, 0.0, 0.0]),
        "carregar_mapa": lambda path: state.setdefault("load_map", path),
        "parar_jogo": lambda: state.setdefault("stop", True),
        "pegar": lambda name: state["vars"].get(name, 0),
        "adicionar": lambda name, n: state["vars"].__setitem__(
            name, state["vars"].get(name, 0) + n),
        "definir": lambda name, val: state["vars"].__setitem__(name, val),
        "tecla_pressionada": lambda key: bool(
            __import__("pygame").key.get_pressed()[
                getattr(__import__("pygame"),
                        "K_" + key.upper(), 0)]),
    }

    # tabela engine
    lua_api = rt.eval("{}") if False else rt.table_from(api)

    # registrar handler via on_event
    def on_event_py(event_id, fn):
        engine.adicionar_evento_lua(event_id, _wrap_callable(fn))
    lua_api["on_event"] = on_event_py

    # start: marca que o script Lua quer iniciar o jogo
    lua_api["start"] = lambda: state.setdefault("lua_start", True)

    rt.globals().engine = lua_api
    return rt
