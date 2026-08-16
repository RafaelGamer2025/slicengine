/*
 * SlicEngine — Exemplo de plugin nativo em C.
 *
 * Compilação:
 *   Linux:   gcc -shared -fPIC -O2 noise.c -o noise.so
 *   Windows: gcc -shared -O2 noise.c -o noise.dll
 *   macOS:   gcc -shared -fPIC -O2 noise.c -o noise.dylib
 *
 * A engine chama `se_plugin_register()` ao carregar e, se existir,
 * `se_plugin_name()` para mostrar o nome. Qualquer função exposta aqui
 * pode ser chamada pelos scripts via ctypes ou pelo mod Python wrapper.
 */

#include <stdlib.h>
#include <string.h>

/* Gera ruído pseudoaleatório simples (inteiros 0..255) com semente.
 * Útil para mods que querem efeitos de ruído sem depender de Python. */
static unsigned long _seed = 123456789UL;

void noise_seed(unsigned long s) {
    _seed = s ? s : 123456789UL;
}

int noise_next(void) {
    /* xorshift32 — rápido e sem dependências */
    _seed ^= _seed << 13;
    _seed ^= _seed >> 17;
    _seed ^= _seed << 5;
    return (int)(_seed & 0xFF);
}

/* Preenche um buffer com ruído (0..255). Retorna a quantidade escrita. */
int noise_fill(unsigned char *buf, int n) {
    int i;
    if (!buf || n <= 0) return 0;
    for (i = 0; i < n; i++)
        buf[i] = (unsigned char)noise_next();
    return n;
}

/* ---- Interface padrão da SlicEngine ---- */

void se_plugin_register(void) {
    noise_seed(0);
}

const char *se_plugin_name(void) {
    return "slicengine-noise-c";
}

int se_plugin_version(void) {
    return 1;
}
