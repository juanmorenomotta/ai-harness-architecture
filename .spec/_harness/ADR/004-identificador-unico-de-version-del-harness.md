# ADR-004 — Identificador único de versión del harness

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A1** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: `.harness/harness.version` (nuevo), `scripts/validate_harness.py`

## Contexto

El harness se va a **instanciar** para iniciar cada proyecto nuevo, y debe conservar un enlace de
versión con los proyectos y componentes que origina (decisión **D1**). Eso exige un identificador
de versión que un proyecto pueda fijar.

Al medir el estado real, el repositorio tenía **cinco versiones independientes**, ninguna de las
cuales representa al conjunto:

| Artefacto | Versión |
| :--- | :--- |
| `AGENTS.md` → «Versión del contrato» | `1.0.0` |
| `harness.config.json` → `version` | `1.0.0` |
| `.harness/models.yaml` → `version` | `1.2.0` |
| `.harness/providers.yaml` → `version` | `1.1.0` |
| `.harness/routing.yaml` → `version` | `1.0.0` |

`scripts/validate_harness.py` **no comprobaba** la coherencia entre ellas. El riesgo es el mismo
que ya se corrigió dos veces en este repositorio: **un dato crítico repartido en copias que pueden
divergir en silencio**. Ocurrió con el catálogo de modelos (ADR-001) y con los vínculos agente↔skill
(ADR-003). Esta es la tercera ocurrencia del mismo patrón.

Sin identificador único, «enlace de versión con los proyectos» es inejecutable: no hay nada que fijar.

## Decisión

**El harness tiene un único punto de verdad de versión en `.harness/harness.version`, que agrega las
cinco versiones de los artefactos. `scripts/validate_harness.py` falla si alguna diverge de la
declarada.**

```yaml
# .harness/harness.version — ÚNICO punto de verdad de versión del harness.
# Un proyecto instanciado fija este valor para saber de qué versión viene.
harness: "1.0.0"              # versión del conjunto (semver)
declared:
  agents_contract: "1.0.0"    # AGENTS.md      → "Versión del contrato"
  config: "1.0.0"             # harness.config.json → version
  models: "1.2.0"             # .harness/models.yaml → version
  providers: "1.1.0"          # .harness/providers.yaml → version
  routing: "1.0.0"            # .harness/routing.yaml → version
```

**Semántica del check** (tres invariantes, todas verificables por comando):

| Invariante | Tipo | Qué evita |
| :--- | :--- | :--- |
| `.harness/harness.version` existe y `harness` es semver válido | error | Que no haya versión que fijar |
| Cada artefacto declara una versión presente en `declared` | error | Artefacto sin versión registrada |
| La versión **real** de cada artefacto coincide con la declarada | error | Cambiar una configuración **sin registrarlo** — la divergencia real |

El tercer invariante es el que aporta el valor: detecta el caso «se editó `models.yaml` y se subió su
versión, pero nadie actualizó el agregado». Sin él, el archivo sería documentación, no un control.

**Política de incremento** (semver sobre el campo `harness`):

| Cambio | Incremento |
| :--- | :--- |
| Se modifica una regla de `AGENTS.md` (R1–R10) o un gate | **major** |
| Se añade o elimina un rol, una skill o una política | **minor** |
| Ajuste de configuración sin cambio de contrato (modelo, umbral, timeout) | **patch** |

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Campo `harnessVersion` en `harness.config.json`** | Un solo sitio, ya versionado, sin archivo nuevo | **No agrega** las cinco versiones existentes: seguirían divergiendo en silencio. El check solo podría validarse a sí mismo | No resuelve el problema que motiva la decisión |
| **B. Tag semver del repositorio del harness** | Mecanismo estándar de git; inmutable | No captura cambios de configuración sin tag; no dice nada de las cinco versiones internas; requiere que el proyecto consulte git del harness | Necesario pero **insuficiente**: los tags y el manifiesto se complementan, no se sustituyen |
| **C. Ninguna versión: el proyecto copia y ya** | Cero mantenimiento | Hace imposible el upgrade del harness y contradice D1 | Contradice la decisión D1 |
| **D. `.harness/harness.version` con manifiesto de las cinco versiones** | Un solo sitio; **detecta la divergencia real**; sin dependencias externas | Un archivo más y una edición adicional al cambiar cualquier configuración | — (la elegida) |

## Consecuencias

**Positivas**
- Existe **una** versión que un proyecto puede fijar (habilita `instanciar-harness` y su `--check`).
- La divergencia entre las cinco versiones deja de ser silenciosa: pasa a ser un **error de gate**.
- La política de incremento hace explícito qué merece bump mayor (la ley) y qué no.

**Negativas / deuda asumida**
- Cambiar cualquier configuración del harness exige ahora **dos ediciones** (el artefacto y el
  manifiesto). Es el precio del control; el validador indica exactamente qué falta.
- El manifiesto es un **duplicado controlado**. Se acepta porque el check lo hace verificado, no
  confiado — a diferencia de un duplicado sin check.

**Neutrales**
- Los adaptadores generados no cambian: `sync-adapters.sh` no lee este archivo.
- `.harness/**` está en `protectedFiles`, así que la implementación va por **PR separada con
  aprobación humana** (R4).

## Cómo revertir esta decisión

Eliminar `.harness/harness.version` y retirar el check del validador. Se vuelve al estado anterior
(cinco versiones sin coordinación) sin efecto en ningún otro artefacto.

## Cómo se verificará

1. `python scripts/validate_harness.py` → coherente, con el check nuevo incluido en el conteo.
2. **Prueba negativa obligatoria** (lección de ADR-001: *un validador que nunca ha fallado no ha
   demostrado nada*): modificar un artefacto sin actualizar el manifiesto y confirmar que el
   validador falla con código 1 señalando el artefacto concreto.
3. `bash init.sh` → PASS tras la implementación.

## Referencias

- `docs/propuesta-harness-instanciable.md` §2 (el problema medido), §5 D1, §11 A1
- ADR-001 y ADR-003 de este directorio (mismo patrón: dato duplicado sin check)
- `scripts/validate_harness.py`, `.harness/*.yaml`, `AGENTS.md`, `harness.config.json`
