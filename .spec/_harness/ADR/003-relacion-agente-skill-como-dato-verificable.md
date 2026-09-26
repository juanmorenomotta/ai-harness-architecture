# ADR-003 — La relación agente ↔ skill es un dato verificable, declarado en una sola dirección

- **Fecha**: 2026-09-25
- **Estado**: `aceptada`
- **Decisor**: Humano responsable del harness
- **Feature**: `_harness` (decisión sobre el propio harness, no sobre una feature)
- **Tareas afectadas**: ninguna (afecta a `.agents/agents/*.md`, `scripts/validate_harness.py`)

## Contexto

El harness tiene **5 roles** (`.agents/agents/*.md`) y **8 skills** (`.agents/skills/*/SKILL.md`).
Son dos capas distintas y ortogonales:

- El **agente** responde a *quién* actúa, *en qué fase*, *con qué permisos* y *con qué modelo*.
  Es un rol ejecutable, con `tools`, `inputs`/`outputs` y entrada en `.harness/models.yaml`.
- La **skill** responde a *cómo* se hace un procedimiento. No tiene fase, ni `tools`, ni modelo.
  No se ejecuta: se consulta bajo demanda cuando su `description` encaja con la tarea.

Al auditar la relación entre ambas capas se encontró que **el vínculo existía solo en prosa**,
y que esa prosa estaba incompleta y desigualmente distribuida:

| Vínculo | Dónde estaba declarado | Problema |
| :--- | :--- | :--- |
| `spec-authoring` → `sdd-init` | Agente (2×) **y** skill ("Usada por") | Duplicado en dos sitios |
| `task-decomposition` → `sdd-tech-lead` | **Solo en la skill** | El agente no la cita |
| `adr-record` → `sdd-tech-lead` | **Solo en el agente** | La skill no lo declara |
| `verify-report` → `sdd-verifier` | **Solo en la skill** | El agente no la cita |
| `security-review` → 2 roles + `init.sh` | En ambos agentes y en la skill | 3 consumidores heterogéneos |
| `gate-runner` → Developer y Verifier | **Solo en `README.md`** | Ningún prompt la cita |
| `model-switching` → humano | En ninguna parte | Sin dueño declarado |
| `sdd-orchestrator` → Orchestrator | **No existe el prompt de agente** | Rol sin definición en `.agents/agents/` |

Consecuencia concreta y verificable: **`sdd-developer` no citaba ninguna skill**, a pesar de que
`README.md` documenta `gate-runner` como suya. En arranque en frío (AGENTS.md §6), el Developer
**no cargaba** esa skill, porque nada en su prompt la nombraba.

El daño potencial es del mismo tipo que el que ya se corrigió dos veces en este repositorio:
antes de ADR-001 un validador comprobaba el dato equivocado y "un validador que nunca ha
fallado no ha demostrado nada". Aquí ocurría lo mismo con otro dato: **nada comprobaba que el
vínculo agente ↔ skill fuera real**. Renombrar o borrar una skill rompía referencias en silencio.

## Decisión

**La relación agente ↔ skill se declara en UNA sola dirección — el campo `skills:` del
frontmatter del rol — y la relación inversa se DERIVA de ella. `scripts/validate_harness.py`
falla si la declaración y el uso no coinciden.**

1. Cada prompt de rol declara sus skills en el frontmatter:

   ```yaml
   # .agents/agents/sdd-verifier.md
   name: sdd-verifier
   phase: "verify"
   skills:
     - gate-runner
     - verify-report
     - security-review
   tools: [read, search, execute, todo]
   ```

2. **No se escribe `used_by:` en el frontmatter de la skill.** El frontmatter de `SKILL.md`
   solo admite cinco campos (`name`, `description`, `argument-hint`, `user-invocable`,
   `disable-model-invocation`), y VS Code documenta que un frontmatter mal formado produce
   **fallo silencioso**: la skill deja de descubrirse sin mensaje de error. Declarar el vínculo
   dos veces, en una superficie con esa fragilidad, es invitar a que las copias diverjan.

3. El validador comprueba cuatro invariantes:

   | Invariante | Tipo | Qué evita |
   | :--- | :--- | :--- |
   | Lo declarado en `skills:` existe en `.agents/skills/` | **error** | Referencia a una skill borrada o mal escrita |
   | Lo citado como `skills/<nombre>` en el procedimiento está declarado | **error** | Vínculo implícito que no sobrevive al arranque en frío |
   | Toda skill tiene declarante o mención en el harness | **warn** | Skill huérfana que nadie carga |
   | El frontmatter de la skill no usa campos ajenos | **warn** | Fallo silencioso de descubrimiento |

4. Se añade la **simetría de la regla de capas** (AGENTS.md §4): un prompt de rol ya no podía
   mencionar un modelo; ahora **tampoco una skill**. Con una excepción explícita:
   `model-switching` existe *para* explicar el cambio de modelo, así que citar nombres de modelo
   es su contenido y no un acoplamiento.

5. `sdd-orchestrator` se declara explícitamente como **rol autoconsumido**: su definición *es*
   la skill, no tiene prompt en `.agents/agents/` y por eso no puede ser huérfana. La asimetría
   se acepta y se documenta aquí, en lugar de dejar un silencio que parezca un olvido.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Dejar el vínculo en prosa (statu quo)** | Cero trabajo; nada que mantener | Es lo que produjo el fallo: 3 de 8 vínculos incompletos y el Developer sin `gate-runner`. No es verificable | Es la causa raíz del incidente; no se puede comprobar por comando |
| **B. Declarar `used_by:` en la skill, además de `skills:` en el rol** | El vínculo es visible desde la skill misma | Duplica el dato; `used_by` no es un campo admitido en `SKILL.md` y un frontmatter inválido es un fallo silencioso. Requiere mantener dos copias sincronizadas a mano | El inverso se deriva gratis del rol. Duplicar un vínculo en una superficie frágil es deuda con interés |
| **C. Validar solo que la skill citada existe (lo que ya hacía el validador)** | Es lo que ya estaba implementado; mínimo cambio | No detecta el fallo real: `sdd-developer` no citaba ninguna skill, y eso no es un error bajo esta regla. Tampoco detecta huérfanas ni campos ajenos | Cubría la mitad del problema y dejaba pasar el caso que motivó este ADR |
| **D. Un archivo de mapeo aparte (`.harness/skills-map.yaml`)** | Separa el vínculo de los artefactos; un solo sitio | Tercer lugar donde mirar; el vínculo se aleja del prompt que lo usa y se desincroniza sin que se note | La cercanía al rol es lo que hace que el vínculo sobreviva a ediciones del prompt |
| **E. Declarar el vínculo en una sola dirección (rol → skill), derivando el inverso** | Un único sitio de verdad; el inverso es siempre correcto por construcción; el validador puede fallar de verdad | El vínculo no es visible desde el directorio de la skill (se ve en `validate_harness.py --json` y en la tabla de este ADR) | — (la elegida) |

## Consecuencias

**Positivas**
- Los 8 vínculos agente ↔ skill pasan a ser **comprobables por comando**, igual que ya lo era el
  vínculo rol → modelo. La coherencia del harness sube de 59 a 85 comprobaciones.
- `gate-runner` deja de ser un vínculo documental: el Developer y el Verifier la declaran y la
  citan en su procedimiento, así que la cargan en arranque en frío.
- El check **se probó fallando** (ver "Verificación"): detecta tanto una skill inventada como una
  cita no declarada, y devuelve código 1. No es un verde sin evidencia.
- Detectar campos ajenos en el frontmatter de una skill convierte un fallo silencioso de
  descubrimiento en una advertencia visible.

**Negativas / deuda asumida**
- El validador crece en lógica y en acoplamiento a un detalle de formato (el frontmatter de
  `SKILL.md`). **Se acepta**: el conjunto de campos admitidos es pequeño, estable y está
  documentado por VS Code.
- El check de huérfanas es una **advertencia**, no un error. Un falso positivo por mención
  textual (el nombre se busca como palabra completa en todo el corpus) degrada a ruido, no
  bloquea. Preferible a que bloquee trabajo legítimo.
- La excepción de `model-switching` es un **allowlist en código** (`MODEL_SCOPED_SKILLS`). Si
  crecen las skills sobre modelos, hay que ampliarla a mano. Es una lista explícita y visible.

**Neutrales**
- Los adaptadores generados (`.github/agents/*.agent.md`, `.claude/`, `.gemini/`) **no** se ven
  afectados: `sync-adapters.sh` solo lee `description`, `tools` y `model` del rol, e ignora
  cualquier otra clave del frontmatter.
- Ningún rol cambia de permisos, de fase ni de modelo.

## Cómo revertir esta decisión

Barato y localizado en dos sitios: retirar el bloque `skills:` del frontmatter de los cinco
roles y revertir `check_skills_referenced()` a su versión que solo comprobaba existencia. Los
prompts recuperarían su estado anterior y el validador volvería a 59 comprobaciones. No hay
migración de datos ni efecto en los adaptadores.

## Verificación de la decisión

1. **Estado coherente**: `python scripts/validate_harness.py` → **85 comprobaciones, COHERENTE**,
   código de salida **0**.
2. **El check falla de verdad** (prueba negativa, siguiendo la lección de ADR-001). Se introdujo
   a propósito en `sdd-developer.md` una skill inexistente (`skill-que-no-existe-fixture`) y una
   cita no declarada (`skills/adr-record` en el procedimiento). Resultado:

   ```
   ✘ .agents\agents\sdd-developer.md: declara la skill 'skill-que-no-existe-fixture' en
     'skills:', pero no existe en .agents/skills/
   ✘ .agents\agents\sdd-developer.md: cita 'skills/adr-record' en el procedimiento pero no lo
     declara en 'skills:'; en arranque en frío ese vínculo no existe
   == INVÁLIDO: 2 incoherencia(s) ==
   EXIT=1
   ```

   El fixture se revirtió después; el estado commiteado es el coherente.
3. **El check encontró un caso real no previsto.** Al extenderse el agnosticismo de modelo a las
   skills, la primera ejecución detectó `qwen-3-coder-480b` en `model-switching`. Se resolvió
   como excepción explícita (invariante 4), no desactivando el check.
4. **Prueba de no regresión**: los checks preexistentes (roles, catálogo, capas, permisos, ley,
   adaptadores, `harness.config.json`, secretos) siguen ejecutándose sin cambios en su semántica.

## Registro de la relación resultante

Derivada del campo `skills:` de cada rol (fuente de verdad única):

| Skill | Declarada por | Tipo |
| :--- | :--- | :--- |
| `spec-authoring` | `sdd-init` | 1:1 |
| `task-decomposition` | `sdd-tech-lead` | 1:1 |
| `adr-record` | `sdd-tech-lead` | 1:1 |
| `verify-report` | `sdd-verifier` | 1:1 |
| `security-review` | `sdd-security-reviewer`, `sdd-verifier` | compartida (además `init.sh` la usa como política) |
| `gate-runner` | `sdd-developer`, `sdd-verifier` | compartida |
| `model-switching` | — (humano) | fuera del ciclo SDD |
| `sdd-orchestrator` | — (rol autoconsumido) | su propia definición |

## Referencias

- `AGENTS.md` §4 (regla de capas), §6 (arranque en frío), §8 (obligaciones del Verifier)
- ADR-001 de este mismo directorio (validar contra la fuente correcta; probar que el validador falla)
- ADR-002 de este mismo directorio (un modelo de extensión en el rol `sdd-verifier`)
- `scripts/validate_harness.py` → `check_skills_referenced()`, `check_layer_separation()`
- Referencia oficial de VS Code sobre agent skills (campos admitidos en `SKILL.md`)
