# ADR-006 — El `AGENTS.md` del proyecto es un artefacto generado

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A3** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: `AGENTS.md` (partición ley/parámetros), `instanciar-harness` (nuevo), `AGENTS.md` §4

## Contexto

`AGENTS.md` es la **ley** y todo agente debe leerlo como precondición (§0 y §6). Al instanciar el
harness en un proyecto nuevo, hay que decidir si la ley se copia, se referencia o se genera.

El análisis reveló que el archivo **ya es hoy una mezcla de dos naturalezas**:

| Sección | Naturaleza | ¿Cambia por proyecto? |
| :--- | :--- | :--- |
| §1 R1–R10 · §2 estándares · §3 convenciones · §5 DoD · §6 protocolo · §7 gates · §8 verifier · §9 ADRs | **Ley** | **No** |
| §4 Estructura del repositorio | **Mixta** | Referencia `.agents/`, `.harness/` (harness) **y** `src/`, `tests/` (proyecto) |

**§4 es el síntoma**: un archivo de ley describiendo `src/`. Es ley conteniendo datos de proyecto. Y
en un proyecto multi-componente las rutas dependen del stack, así que no pueden ser ley.

## Decisión

**El `AGENTS.md` de un proyecto se GENERA desde (ley base versionada + parámetros del proyecto), y se
marca como no editable.**

| Contenido | Dónde vive | Naturaleza |
| :--- | :--- | :--- |
| **Reglas** (R1–R10, gates, protocolo en frío, DoD) | Harness base, versionado | Ley — no se edita por proyecto |
| **Parámetros** (nombre, ramas protegidas, rutas, stack, comandos) | `harness.config.json` del proyecto | Datos — sí cambian |
| **`AGENTS.md` del proyecto** | Generado de ambos | Artefacto, cabecera «NO EDITAR A MANO» |

Consecuencias directas:

1. **§4 deja de ser ley y pasa a ser parámetro.** La estructura del repositorio se resuelve desde la
   configuración, no desde el texto de la ley.
2. **El drift se controla con un check, no con disciplina**: `instanciar-harness --check` falla si el
   `AGENTS.md` del proyecto no corresponde a la versión declarada del harness. Misma forma que
   `sync-adapters.sh --check`, que ya existe.
3. **La ley no se puede editar en el proyecto** (R4 se preserva): el proyecto puede cambiar sus
   parámetros, nunca sus reglas.

### El precedente ya existe en este repositorio

El argumento decisivo no es teórico. `scripts/sync-adapters.sh` **ya implementa exactamente este
patrón** para los agentes:

```bash
echo "<!-- GENERADO por scripts/sync-adapters.sh — NO EDITAR A MANO."
echo "## Ley del repositorio (AGENTS.md) — normativa, prevalece sobre todo lo demás"
sed -n '/^## 0\./,$p' "$LAW"
```

Incrusta la ley en cada `.agent.md` y lo marca como generado. El mecanismo, la convención de cabecera
y el check de sincronización ya están probados en producción.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Copia completa por proyecto** | Autónomo; un solo archivo que leer | **Drift garantizado** (mejorar R5 obliga a actualizar N archivos). Y peor: el proyecto puede editar su propia ley, que es justo lo que **R4** impide | Rompe R4 y no escala |
| **B. Referencia fina** (el proyecto cita la ley base) | Sin duplicación; un solo texto de ley | El agente debe leer dos archivos. Y los subagentes de Copilot **no leen `AGENTS.md` automáticamente** — ya hubo que incrustar la ley en los `.agent.md` por esto | Choca con un límite real de la plataforma |
| **C. Partido** (ley + `project.yaml` separados) | Separación limpia de conceptos | Dos sitios que el agente debe leer; hay que decidir cuál prevalece y documentarlo | Añade complejidad sin beneficio sobre (D) |
| **D. Generado desde ley + parámetros** | Un solo archivo que el agente lee; ley inmutable; drift detectable por check; **precedente ya existente** | Requiere un generador y marcar el archivo como no editable | — (la elegida) |

## Consecuencias

**Positivas**
- La ley viaja **íntegra y única**: mejorar R5 se propaga a todos los proyectos al re-instanciar.
- El drift deja de ser silencioso: es un error de check, no un descuido.
- Corrige el defecto de §4, que hoy mezcla ley y datos de proyecto.
- Reutiliza un mecanismo ya probado (`sync-adapters.sh`) en lugar de inventar uno.

**Negativas / deuda asumida**
- El `AGENTS.md` del proyecto **no se puede editar a mano**. Si un proyecto necesita una regla
  distinta, el camino es promover el cambio al base o registrar un ADR en el proyecto — no editar.
  Es una restricción deliberada.
- `instanciar-harness` necesita un generador y su modo `--check`. Es trabajo real, no un envoltorio.
- Cambiar la ley base exige **re-instanciar** los proyectos para que reciban el cambio. Esto hace
  visible el coste de actualización, que es precisamente el objetivo.

**Neutrales**
- El `AGENTS.md` de *este* repositorio (el harness) no se genera: es la fuente, no una instancia.
- Los adaptadores de CLI no cambian.

## Cómo revertir esta decisión

Dejar de generar el `AGENTS.md` del proyecto y volver a copiarlo íntegro (alternativa A). Se recupera
la autonomía total del proyecto y se pierde la propagación de la ley. Barato de ejecutar, costoso de
mantener.

## Cómo se verificará

1. `instanciar-harness --check` sobre un proyecto instanciado → código 0 si está sincronizado.
2. **Prueba negativa**: editar a mano una regla en el `AGENTS.md` del proyecto y confirmar que
   `--check` **falla** señalando la divergencia.
3. El `AGENTS.md` generado contiene §1–§3 y §5–§9 idénticas al base, y §4 resuelta con las rutas del
   proyecto.
4. `bash init.sh` del proyecto → PASS con el check de sincronización incluido.

## Referencias

- `docs/propuesta-harness-instanciable.md` §11 A3, §12 Anexo A
- `scripts/sync-adapters.sh` — precedente del patrón «generado + check»
- `AGENTS.md` §4 (el defecto que esta decisión corrige), §9 (cambios a la ley)
- ADR-004 de este directorio (versión del harness, que el check necesita fijar)
