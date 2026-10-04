# ADR-015 — Los adaptadores llevan el procedimiento del rol, y se verifica por contenido

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (pendiente de revisión humana)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Tareas afectadas**: `scripts/sync-adapters.sh`, `.github/agents/*.agent.md`, `.claude/agents/`, `.gemini/agents/`

## Contexto

El diseño de `sync-adapters.sh` tiene un motivo explícito, documentado en `README.md`:

> `sync-adapters.sh` genera `.github/agents/*.agent.md`, incrustando la ley y el prompt del rol,
> **porque los subagentes de Copilot no leen `AGENTS.md` automáticamente.**

Y en el propio script:

> El cuerpo INCLUYE la ley del repo y el prompt del rol.

Al inspeccionar los adaptadores generados se descubrió que **5 de los 6 contenían la ley pero no el
procedimiento de su rol**. Un adaptador de 256 líneas con esta forma:

```
## Ley del repositorio (AGENTS.md)   ← 255 líneas, correcto
---
## Definición del rol
                                     ← VACÍO: el procedimiento nunca se copió
```

Cada agente recibía el contrato completo pero **ninguna instrucción de cómo actuar**. Lo que hacían
bien era por interpretación de su `description`, no por seguir el procedimiento escrito.

### Causa raíz: CRLF

El script extraía el cuerpo con:

```bash
sed '1{/^---$/!q}; 1,/^---$/d' "$AGENTS_DIR/${role}.md"
```

Con finales de línea **CRLF** —los de todo el repo, porque es Windows— la línea delimitadora es
`---\r`, y `^---$` **no casa**. El `sed` no reconoce el cierre del frontmatter, ejecuta la rama `q`
del primer bloque y devuelve **una sola línea**.

Medición del alcance (verificada, no inferida):

| Rol | Finales de línea | Cuerpo extraído por el `sed` |
| :--- | :--- | :--- |
| `harness-maintainer` | LF (creado el 2026-10-04) | 64 líneas — correcto |
| `sdd-init`, `sdd-tech-lead`, `sdd-developer`, `sdd-verifier`, `sdd-security-reviewer` | **CRLF** | **1 línea** — roto |

El único rol que funcionaba era el creado más recientemente, **por accidente**: su archivo salió con LF.

### Agravante: el check decía que todo estaba bien

`sync-adapters.sh --check` compara cada archivo generado **contra la salida del propio script**. Si el
script genera mal, el check compara mal contra mal y responde **«SINCRONIZADOS»**. Un verde que no
verifica nada — la misma clase de defecto que un check en `SKIP` contado como `PASS` (ADR-011).

## Decisión

**El cuerpo del rol se extrae con un helper tolerante a CRLF, y la presencia del procedimiento en el
adaptador se verifica por CONTENIDO, no solo por comparación de archivos.**

1. **`extract_body()`** normaliza `\r` antes de buscar los delimitadores, con la misma técnica que ya
   usaba `parse_models()` y `extract_description()` en el mismo script. Sustituye al `sed`.

2. **`check_adapters_have_role_body()`**, que comprueba dos cosas:
   - El rol fuente tiene cuerpo más allá del frontmatter (si no, **es un error**, no un resultado
     vacío aceptable).
   - El adaptador generado contiene las secciones clave del rol (`## Procedimiento`, `## Límites`).

   Este check mira el **contenido**, así que no puede ser víctima del mismo círculo vicioso: si el
   script genera mal, lo detecta.

3. El check se ejecuta **tanto** en modo `--check` como en cada sincronización, de modo que un
   adaptador vacío no puede llegar a `main` sin que alguien lo vea.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Normalizar todos los archivos del repo a LF** (`.gitattributes`) | Elimina la causa de raíz | No arregla el `sed` frágil; cualquier archivo nuevo con CRLF vuelve a romperlo. Y el check seguiría sin detectar el vacío | Trata el síntoma; el defecto puede reaparecer |
| **B. Dejar que el agente lea su prompt del rol desde `.agents/`** | Sin duplicación | Los subagentes de Copilot **no leen archivos arbitrarios** de forma fiable: es el motivo por el que el script incrusta el contenido | Contradice el diseño existente |
| **C. Helper tolerante a CRLF + check de contenido** | Arregla la causa y **detecta la recaída**; coherente con `extract_description`, que ya lo hacía bien | Un check más en el script | — (la elegida) |
| **D. Solo arreglar el `sed`, sin check** | Cambio mínimo | Nada impediría que un cambio futuro volviera a vaciar los adaptadores, y el `--check` seguiría dando verde | Es exactamente el fallo que se acaba de descubrir |

## Consecuencias

**Positivas**
- Los 6 adaptadores pasan de 256 a **303–320 líneas** y contienen el procedimiento completo de su rol
  (`Quién eres`, `Precondición`, `Procedimiento`, `Límites`, `Salida`).
- El check **mira el contenido**, así que rompe el círculo vicioso de comparar el generado contra sí
  mismo.
- El helper es coherente con el resto del script, que ya normalizaba CRLF en otros dos sitios.
- Corrige el defecto **antes** de que el instanciador (ADR-006) lo propague a cada componente nuevo.

**Negativas / deuda asumida**
- El check depende de que el rol tenga las secciones `## Procedimiento` y `## Límites`. Un rol con otra
  estructura daría un falso positivo. Se acepta: la estructura está fijada por el protocolo del harness
  y todos los roles la siguen.
- El script sigue siendo bash y depende de `awk`/`grep`, que en Windows solo existen dentro de bash.

**Neutrales**
- `.claude/agents/` y `.gemini/agents/` son copias directas del prompt y **no tenían** el defecto; se
  verificó que contienen el procedimiento.

## Cómo revertir esta decisión

Volver al `sed` anterior y retirar el check. Se recupera el comportamiento defectuoso: 5 de 6
adaptadores sin procedimiento y un `--check` que dice que todo está bien.

## Cómo se verificó

1. **Reproducción del fallo** antes de tocar nada: con el `sed` original, `sdd-init.md` (CRLF) extrae
   **1 línea** y `harness-maintainer.md` (LF) extrae 64.
2. **El check detecta el defecto existente**: con los adaptadores aún rotos,
   `sync-adapters.sh --check` falla con **código 1** señalando los 6.
3. **Regeneración**: los 6 adaptadores pasan a contener el procedimiento (303–320 líneas).
4. **Pruebas negativas** (cada una con código 1, revirtiendo el fixture):
   - Adaptador truncado a 256 líneas → `falta el procedimiento del rol`
   - Rol con el frontmatter descerrado → `no se pudo extraer el cuerpo del rol`
5. `python scripts/validate_harness.py` → **123 comprobaciones, COHERENTE**; `bash init.sh` → **PASS**.

## Lección transversal

**Sexta ocurrencia del patrón del repositorio** (dato crítico en copias que divergen en silencio), y
aquí con un matiz nuevo: **el check que debía protegerlo estaba diseñado de forma que no podía
fallar** — comparaba la salida del generador contra la salida del generador.

Refuerza las dos lecciones ya registradas:
- *Un validador que nunca ha fallado no ha demostrado nada.*
- *Un límite es real cuando es capacidad ausente*: aquí, un check solo es real cuando **mira algo
  distinto de sí mismo**.

## Referencias

- ADR-011 (garantía aparente: un `SKIP` no es un `PASS`), ADR-003 (vínculo verificable por comando)
- `AGENTS.md` §6 (arranque en frío), §4 (regla de capas)
- `scripts/sync-adapters.sh`, `README.md` (arquitectura de capas)
