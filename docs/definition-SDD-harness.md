Perfecto, vamos a aterrizar ese flujo de trabajo con SDD (Specification-Driven Development) y orquestación multiagente. La clave está en usar **artefactos en disco** como única fuente de verdad, de modo que cada agente (o subagente) arranque "en frío", lea solo lo que necesita y no herede contexto innecesario. Esto es precisamente lo que propone `sdd-flow`: "no se escribe código hasta que el alcance, el diseño y las tareas están confirmados en disco".

## 🧭 Cómo integrar SDD con orquestación multiagente

### 1. El patrón central: "artefactos en disco + subagentes en frío"

En lugar de tener una conversación larga donde un solo agente lo recuerda todo, el flujo SDD se apoya en archivos versionados bajo una carpeta como `.spec/<feature>/`. Cada fase es ejecutada por un subagente distinto que **solo lee el artefacto que le corresponde** y escribe su propio artefacto de salida. Así, el orquestador se mantiene "delgado" y cada subagente trabaja con un contexto limpio y acotado.

El ciclo mínimo que propone `sdd-flow` es:

```
init → design + tasks → implement → verify
```

Y los roles que lo ejecutan son: **Orchestrator**, **Init**, **Tech Lead**, **Developer** y **Verifier** — todos definidos como prompts en archivos Markdown, no como llamadas a herramientas.

### 2. Roles del flujo SDD (mapeados a tus herramientas)

| Fase SDD | Rol | Artefacto de salida | Herramienta sugerida |
|---|---|---|---|
| **Init / Scope** | Product Owner (subagente) | `scope.md` con alcance, no-objetivos y criterios de aceptación | Claude Code (subagente con `tools` restringidas a lectura) |
| **Design + Tasks** | Tech Lead (subagente) | `design.md` + `tasks/*.md` | Antigravity CLI (modo `/planning`) |
| **Implement** | Developer (subagente) | Código + commits por tarea | Antigravity CLI o Codex CLI (`exec`) |
| **Verify** | Verifier (subagente) | `verify.md` + PR (nunca auto-merge) | Codex CLI (`review`) |

`specky` lleva esto a un extremo: **13 agentes especializados, 57 herramientas MCP y 10 fases** con puertas de revisión humana (LGTM gates) en cada transición. Para empezar, no necesitas esa complejidad; el patrón de 4–5 roles ya te da estructura.

### 3. Cómo "cablear" los subagentes en Claude Code

Claude Code es el que mejor soporta este patrón de forma nativa, porque distingue entre **Subagents** (trabajadores dentro de una sesión, con contexto aislado) y **Agent Teams** (múltiples sesiones independientes que se coordinan mediante una lista de tareas compartida).

Para SDD, lo más limpio es empezar con **Subagents**. Se definen como archivos Markdown en `.claude/agents/` con frontmatter YAML:

```markdown
---
name: sdd-tech-lead
description: Convierte una especificación en un diseño técnico y un plan de tareas
model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - Write
---
Eres el Tech Lead del flujo SDD. Recibes el archivo `scope.md` de la feature.
Debes producir:
1. `design.md` con la arquitectura propuesta y las interfaces.
2. `tasks/` con una tarea por archivo, cada una con criterio de aceptación verificable.

No escribas código. Solo diseño y descomposición.
```

Luego, desde la sesión principal (el Orquestador), puedes invocarlo así:

```
> Usa el subagente sdd-tech-lead para procesar .spec/login-feature/scope.md
```

El subagente se ejecuta en su propio contexto, escribe los artefactos en disco y devuelve solo un resumen a la conversación principal. Esto evita que tu sesión de orquestación se contamine con detalles de implementación.

### 4. Orquestación entre herramientas distintas: CLI Agent Orchestrator (CAO)

Si quieres que un supervisor en una CLI (por ejemplo, Claude Code) delegue a workers en **otras CLIs** (Codex, Antigravity, Copilot), el proyecto **CLI Agent Orchestrator (CAO)** es la pieza que falta. CAO corre cada agente en una sesión tmux aislada y los coordina con un patrón supervisor–worker sobre MCP. Usa tres primitivas: `handoff` (síncrono), `assign` (asíncrono) y `send_message` (bandeja de entrada entre agentes).

Esto te permite tener, por ejemplo:
- Un **supervisor en Claude Code** que planifica y valida.
- Un **worker en Antigravity** que implementa.
- Un **worker en Codex** que revisa seguridad.

Todos viven en el mismo repositorio, leen los mismos artefactos en `.spec/` y se comunican por MCP sin que tú tengas que estar copiando y pegando salidas entre terminales.

### 5. Codex CLI en el flujo: QA y revisión

Codex CLI brilla en la fase de **verificación** porque su comando `codex review` está diseñado para analizar cambios y buscar problemas que los linters no detectan. Para automatizarlo en un pipeline SDD, usas el modo no interactivo:

```bash
codex exec "Lee .spec/login-feature/tasks/ y verifica que cada criterio de aceptación se cumple en el código actual. Escribe el resultado en .spec/login-feature/verify.md"
```

Si además quieres una revisión de seguridad como subagente separado, `oh-my-codex` ofrece un modo `review:` que activa un **Reviewer + Security** en paralelo, con modelo de razonamiento alto.

### 6. Antigravity CLI en el flujo: diseño e implementación

Antigravity tiene un ecosistema de skills y subagentes muy orientado a SDD. El pack `oh-my-antigravity` define, por ejemplo, un `oma-architect` para límites del sistema e interfaces, un `oma-planner` para descomposición de tareas y un `oma-executor` para ciclos rápidos de implementación.

Para la fase de diseño, puedes activar el modo `/planning` y pedirle que genere los artefactos SDD:

```
/planning Genera el design.md y las tareas para la feature descrita en .spec/login-feature/scope.md
```

Y para implementar una tarea concreta:

```
$execute Implementa la tarea 03 de .spec/login-feature/tasks/ y haz commit con el mensaje "sdd: task 03 - <descripción>"
```

### 7. Un flujo mínimo end-to-end que puedes montar hoy

1. **Init (Claude Code, subagente `sdd-init`)**: Lee el prompt de la feature y escribe `.spec/<feature>/scope.md` con alcance, no-objetivos y criterios de aceptación medibles.
2. **Design + Tasks (Antigravity, `/planning`)**: Lee `scope.md` y produce `design.md` + `tasks/*.md`.
3. **Implement (Antigravity, `$execute` o Codex `exec`)**: Un subagente Developer toma **una tarea a la vez**, implementa, hace commit y pasa a la siguiente. Un commit por tarea, nunca un diff gigante.
4. **Verify (Codex, `exec` + `review`)**: Un Verifier lee `tasks/` y el código, ejecuta las verificaciones y escribe `verify.md`. Si pasa, abre un PR. **Nunca auto-merge**.
5. **Orquestación**: Al principio puedes hacerlo manualmente desde una terminal. Cuando quieras automatizarlo, introduces CAO con un supervisor que haga `assign` al worker de implementación y `handoff` al worker de verificación.

La ventaja de este esquema es que cada herramienta hace lo que mejor sabe: Claude Code para planificar y orquestar, Antigravity para diseñar e implementar con skills, Codex para verificar con criterio de revisión, y CAO como pegamento cuando necesitas que hablen entre sí.

-----

Claro. Para lograr un harness reutilizable e independiente del modelo, la clave está en separar estrictamente **tres capas**: la **definición del rol** (qué hace el agente), la **configuración de ejecución** (qué modelo usa) y los **artefactos SDD** (qué produce). Si mezclas estas capas, cambiar de modelo implica reescribir prompts; si las separas, cambiar de modelo es editar una línea.

A continuación te propongo una estructura de carpetas concreta y el mecanismo para asignar modelos intercambiables.

## 📁 Estructura de carpetas propuesta

```
mi-proyecto/
│
├── AGENTS.md                          # Ley del repositorio. Contrato compartido. Leído por TODOS los agentes.
├── harness.config.json                # Configuración del harness: comandos detectados, gates de verificación.
├── init.sh                            # Gate de verificación ejecutable (lint, tests, typecheck).
│
├── .spec/                             # Artefactos SDD. Generados por sdd-init y los subagentes.
│   └── <feature-slug>/                # Una carpeta por feature (ej: login-oauth)
│       ├── scope.md                   # Alcance, no-objetivos, criterios de aceptación (Init)
│       ├── design.md                  # Arquitectura, interfaces, decisiones técnicas (Tech Lead)
│       ├── tasks/                     # Descomposición en tareas atómicas
│       │   ├── 001-<slug>.md          # Cada tarea: criterio de aceptación verificable
│       │   ├── 002-<slug>.md
│       │   └── ...
│       ├── verify.md                  # Resultado de la verificación (Verifier)
│       └── ADR/                       # Architecture Decision Records (opcional)
│           └── 001-<decision>.md
│
├── .agents/                           # Capa de DEFINICIÓN de roles (agnóstica de modelo)
│   ├── agents/                        # Prompts de subagentes (Markdown + YAML frontmatter)
│   │   ├── sdd-init.md                # Rol: Init / Scope
│   │   ├── sdd-tech-lead.md           # Rol: Tech Lead / Design
│   │   ├── sdd-developer.md           # Rol: Developer / Implement
│   │   ├── sdd-verifier.md            # Rol: Verifier / QA
│   │   └── sdd-security-reviewer.md   # Rol: Security Review (opcional)
│   ├── skills/                        # Habilidades reutilizables (agentskills.io-compliant)
│   │   └── sdd-orchestrator/
│   │       └── SKILL.md               # Orquestador: lee AGENTS.md y delega
│   └── policies/                      # Reglas de seguridad, permisos, deny-first
│       └── permissions.yaml
│
├── .harness/                          # Capa de CONFIGURACIÓN DE EJECUCIÓN (modelo por agente)
│   ├── models.yaml                    # Mapeo rol → modelo (intercambiable)
│   ├── providers.yaml                 # Definición de proveedores (privativos y open source)
│   └── routing.yaml                   # Reglas de enrutamiento (fallback, coste, hardware)
│
├── .claude/                           # Adaptador específico para Claude Code
│   ├── agents/                        # Symlinks o copias de .agents/agents/
│   └── settings.json                  # availableModels allowlist
│
├── .gemini/                           # Adaptador específico para Antigravity CLI
│   ├── agents/                        # Subagentes descubiertos automáticamente
│   └── skills/                        # Skills cargadas globalmente
│
├── .codex/                            # Adaptador específico para Codex CLI
│   └── AGENTS.md                      # Puntero a AGENTS.md raíz
│
└── scripts/
    ├── validate_harness.py            # Valida que la configuración es coherente
    └── sync-adapters.sh               # Sincroniza .agents/ con los directorios de cada CLI
```

## 🔑 El mecanismo clave: `.harness/models.yaml`

Este archivo es el **único punto de verdad** para la asignación de modelos. Los prompts de los agentes **nunca** mencionan un modelo concreto. Ejemplo:

```yaml
# .harness/models.yaml
# Asignación de modelo por rol. Cambiar aquí afecta a TODOS los adaptadores.

roles:
  sdd-init:
    model: "claude-sonnet-4-20250514"
    provider: "anthropic"
    reasoning: "high"
    temperature: 0.2

  sdd-tech-lead:
    model: "gemini-2.5-pro"
    provider: "google"
    reasoning: "high"
    temperature: 0.3

  sdd-developer:
    model: "qwen-3-coder-480b"
    provider: "open-source"
    endpoint: "http://localhost:8000/v1"   # vLLM local
    reasoning: "medium"
    temperature: 0.1

  sdd-verifier:
    model: "gpt-5.4-codex"
    provider: "openai"
    reasoning: "high"
    temperature: 0.0

  sdd-security-reviewer:
    model: "claude-opus-4-20250514"
    provider: "anthropic"
    reasoning: "high"
    temperature: 0.0
```

Y el archivo de proveedores:

```yaml
# .harness/providers.yaml
providers:
  anthropic:
    type: "openai-compatible"
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"

  openai:
    type: "openai-compatible"
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"

  google:
    type: "openai-compatible"
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key_env: "GOOGLE_API_KEY"

  open-source:
    type: "openai-compatible"
    base_url: "http://localhost:8000/v1"
    api_key_env: "VLLM_API_KEY"   # opcional
```

## 🧩 Cómo se conecta cada capa

### 1. El prompt del agente no menciona modelo

En `.agents/agents/sdd-developer.md`, el frontmatter **no** incluye `model:`. Solo define el rol:

```yaml
---
name: sdd-developer
description: Implementa una tarea atómica del plan SDD
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
skills:
  - sdd-orchestrator
---
Eres el Developer del flujo SDD. Recibes UNA tarea de `tasks/` y la implementas.
Haz commit con el mensaje `sdd: task <id> - <descripción>`.
No implementes más de una tarea a la vez.
```

### 2. El orquestador lee la configuración y lanza al agente con el modelo correcto

El orquestador (o el script de arranque) consulta `.harness/models.yaml` y pasa el modelo como parámetro de invocación. En Claude Code, esto se hace con el parámetro `model` del tool `Agent`:

```
# Invocación desde el orquestador (pseudocódigo)
model = models_yaml["roles"]["sdd-developer"]["model"]
Agent(subagent_type="sdd-developer", model=model, prompt="Implementa .spec/login-oauth/tasks/003.md")
```

En Antigravity CLI, el campo `model` del frontmatter del subagente puede sobreescribirse por sesión, y el motor elige el tier (`flash` o `pro`) según el rol. Para modelos externos (open source), el adaptador traduce el nombre del modelo a un endpoint OpenAI-compatible.

### 3. Los adaptadores traducen la configuración genérica a cada CLI

- **Claude Code**: lee `.claude/agents/` (symlink a `.agents/agents/`) y usa `availableModels` allowlist para validar el modelo. Si el modelo no está en la allowlist, sustituye por el más cercano.
- **Antigravity CLI**: descubre subagentes en `.agents/agents/<name>.md` o en `~/.gemini/config/agents/`. El campo `model` acepta tiers nativos (`flash`, `pro`) o nombres específicos vía extensión nativa.
- **Codex CLI**: lee `AGENTS.md` como contrato y usa `codex exec` para invocaciones no interactivas. El modelo se pasa con `--model` o se configura en `~/.codex/config.toml`.
- **CLI Agent Orchestrator (CAO)**: almacena la configuración en `~/.aws/cli-agent-orchestrator/settings.json` y los perfiles de agente en `agent-store/`. Cada perfil es Markdown con YAML frontmatter que incluye el campo `model`. CAO puede enrutar a distintos proveedores según el perfil.

## 🔄 Flujo de trabajo con modelo intercambiable

El ciclo completo queda así:

1. **sdd-init** lee `AGENTS.md` y el prompt de la feature, y escribe `.spec/<feature>/scope.md`. El modelo que usa está definido en `models.yaml` → `sdd-init.model`.
2. **sdd-tech-lead** lee `scope.md` y escribe `design.md` + `tasks/`. Su modelo viene de `models.yaml` → `sdd-tech-lead.model`.
3. **sdd-developer** toma una tarea de `tasks/`, implementa y hace commit. Su modelo puede ser **open source local** (vLLM/Ollama) porque la tarea está bien acotada.
4. **sdd-verifier** lee `tasks/` y el código, ejecuta `init.sh` y escribe `verify.md`. Su modelo puede ser **privativo de alto razonamiento** (Codex o Claude Opus) porque la verificación requiere criterio.
5. **sdd-security-reviewer** (opcional) analiza el diff buscando vulnerabilidades. Su modelo es independiente y puede ser el más potente disponible.

Si mañana quieres cambiar el modelo del Developer de Qwen local a GPT-5.4, **solo editas una línea en `models.yaml`**. Los prompts, los artefactos SDD y los adaptadores no cambian.

## 🛠️ Herramientas que ya implementan este patrón

- **localharness**: harness open source que define agentes en YAML con tools, memoria y permisos deny-first, y los ejecuta contra cualquier endpoint OpenAI-compatible (vLLM, Ollama, LM Studio, llama.cpp). Es el ejemplo más claro de "model-agnostic harness".
- **agentic-orchestration**: orquestación multiagente sobre CrewAI con catálogos YAML de agentes y proveedores. Permite mezclar Ollama, OpenAI, Anthropic y HuggingFace por tarea sin reescribir la lógica de orquestación.
- **team-harness**: coordinador que lanza workers CLI (Codex, Gemini, Claude Code, Antigravity, OpenHands) como acciones de tool-use. Configura el proveedor del coordinador con `TEAM_HARNESS_PROVIDER` y los workers con `--agents`.
- **agent-sdd-toolkit**: genera el scaffold del repositorio con `AGENTS.md` como fuente de verdad, `harness.config.json`, `init.sh` y adaptadores para Codex, Claude, Copilot, Cursor y Windsurf.

## ⚠️ Puntos de atención

- **La allowlist de Claude Code puede bloquear modelos**: si tu organización restringe `availableModels`, Claude Code sustituye el modelo bloqueado por el más cercano de la misma familia. Para modelos open source fuera de la allowlist, necesitas un adaptador que los exponga como endpoint OpenAI-compatible y que Claude Code los reconozca.
- **Antigravity usa tiers, no nombres exactos**: el campo `model` en subagentes acepta `inherit`, `flash` o `pro`. Para usar un modelo open source específico, necesitas una skill con extensión nativa o un adaptador externo.
- **CAO centraliza la configuración en `settings.json`**: si usas CAO como orquestador, la asignación de modelos vive ahí, no en `models.yaml`. Puedes hacer que CAO lea `models.yaml` como fuente y genere el `settings.json`, pero requiere un script de sincronización.
- **El contexto se pierde entre fases**: esto es intencional en SDD. Cada subagente arranca "en frío" y solo lee el artefacto que necesita. El precio es que debes escribir todo en disco antes de pasar a la siguiente fase. La ventaja es que ningún agente alucina sobre decisiones que no están documentadas.

-----

Abordas dos cuestiones que están en el corazón de un harness agéntico maduro. La respuesta corta es: **los SKILLs se definen durante el diseño del harness, no durante la ejecución del SDD**, y **el equipo necesita un nivel de madurez organizacional mínimo (procesos documentados, disciplina de specs) antes de que el patrón multiagente aporte valor real, no caos acelerado**.

A continuación, desarrollo ambos puntos.

---

## 🧩 Cuándo se definen los SKILLs y para qué se utilizan

### La distinción fundamental: Skill vs. Especificación vs. Prompt de Rol

En un harness SDD conviven tres tipos de artefactos que es un error frecuente confundir:

| Artefacto | Naturaleza | Cuándo se carga | Quién lo define |
| :--- | :--- | :--- | :--- |
| **Especificación** (`scope.md`, `design.md`) | **Normativa** ("qué debe respetar todo cambio") | **Siempre activa** durante la feature | El subagente de Init y el Tech Lead, **por feature** |
| **Skill** (`SKILL.md`) | **Procedimental** ("cómo hacer X") | **Bajo demanda**, solo cuando la tarea la dispara | El **equipo de plataforma/harness**, una vez, antes de empezar a usar el flujo |
| **Prompt de Rol** (`sdd-developer.md`) | **Identitaria** ("quién eres y qué entregas") | Al invocar al subagente, en cada fase | El equipo, una vez, y se versiona con el harness |

La clave está en que **la skill es conocimiento procedimental reutilizable que el orquestador carga solo cuando la tarea lo requiere**, deliberadamente no antes, para no contaminar el contexto del agente con reglas que no aplican al trabajo actual. Si pones reglas normativas dentro de una skill, corres el riesgo de que una restricción obligatoria solo se aplique cuando esa skill se cargue por casualidad.

### ¿Cuándo se define una skill?

**Antes de que el equipo empiece a usar el harness en features reales.** Las skills son parte de la **infraestructura del harness**, no del trabajo por feature. Se definen una vez, se versionan en el repositorio y se refinan iterativamente.

La pregunta correcta no es "¿cuándo en el flujo SDD?", sino **"¿qué conocimiento procedimental repetitivo tenemos que empaquetar para que los agentes lo apliquen consistentemente?"** Se crea una skill cuando el contenido es:

- **Demasiado detallado para el `AGENTS.md`**: plantillas de código, workflows multi-paso, procedimientos de diagnóstico.
- **Relevante solo para tareas específicas**: no se necesita en cada sesión, solo cuando se dispara una condición concreta.

### Ejemplos concretos en tu flujo

En el ecosistema `sdd-flow`, las skills son precisamente eso: el **orquestador + estándares**, con frontmatter compatible con agentskills.io. En `sdd-skills`, cada skill es un comando del pipeline (`/sdd-init`, `/sdd-feature`, `/sdd-plan`, etc.) que "recoge donde lo dejó el anterior usando los archivos producidos en el camino".

Para tu harness, las skills candidatas serían:

1. **`sdd-orchestrator`**: la skill que lee `AGENTS.md`, consulta `.harness/models.yaml` y delega a los subagentes. Es el "pegamento" del harness.
2. **`code-review-checklist`**: una skill que el Verifier carga solo cuando va a revisar, con la lista de comprobaciones específicas de tu dominio (seguridad, rendimiento, convenciones del repo).
3. **`migration-pattern`**: una skill que el Developer carga solo cuando la tarea implica migrar un módulo, con el procedimiento paso a paso que el equipo ha validado.

Cada skill vive en `skills/<nombre>/SKILL.md` con frontmatter YAML que declara **cuándo debe dispararse** (`description` con "Use when: ..."). El agente decide cargarla cuando el contexto de la tarea coincide con los triggers.

---

## 📈 Niveles de madurez: ¿en qué punto debe estar el equipo?

Sí, existen múltiples modelos de madurez, y convergen en una idea: **el patrón multiagente con SDD no es un punto de partida, es un punto de llegada**. Adoptarlo sin la madurez organizacional adecuada acelera el caos en lugar de la entrega.

### Modelo 1: Madurez de SDD (4 niveles)

Este es el modelo más directamente aplicable a tu pregunta sobre SDD:

| Nivel | Nombre | Idea central | ¿Apto para harness multiagente? |
| :--- | :--- | :--- | :--- |
| **1** | **Spec-First** (disciplina de prompt) | Escribes una spec antes de promptear. La spec es efímera (chat). | **No**. La spec se desvía del código inmediatamente. Sirve para explorar, no para producción. |
| **2** | **Spec-Anchored** (workflow agéntico) | Las specs viven en el repo; los agentes implementan desde ellas. Fases estructuradas: specify → plan → tasks → implement. | **Sí, es el mínimo viable.** Aquí encaja tu harness. El riesgo es la varianza del agente (misma spec, distinta implementación). |
| **3** | **Spec-as-Source** (regeneración) | La spec es canónica; el código se **regenera** cuando la spec cambia. | **Avanzado.** Alineación spec-código forzada por regeneración. No determinista todavía. |
| **4** | **Spec-to-Application** (compilación determinista) | La spec es un modelo formal; el código es un artefacto compilado (M2T). El LLM puede estar fuera del camino crítico. | **Para entornos regulados.** Misma spec → mismo output. Auditable. Air-gapped. |

**Recomendación**: tu harness debería apuntar a **Nivel 2 (Spec-Anchored)** como base. La estructura de carpetas que definimos (`.spec/<feature>/scope.md`, `design.md`, `tasks/`) es exactamente eso: specs versionadas en el repo que los subagentes leen en frío. El Nivel 3 es una evolución posible si tu equipo quiere que la spec sea la fuente de verdad absoluta y el código un derivado.

### Modelo 2: Madurez del Harness (5 etapas)

Este modelo evalúa qué tan robusta es la infraestructura que ejecuta a los agentes:

| Etapa | Nombre | Qué existe | ¿Dónde encaja tu harness? |
| :--- | :--- | :--- | :--- |
| **0** | Ad-hoc | Scripts manuales, sin registro, sin logging estructurado. | No. |
| **1** | Basic | Specs de herramientas schema-first, registro simple, verificación mínima con tests unitarios. | El harness "funciona" pero no es confiable. |
| **2** | **Verified** | Verificación estática en CI, ejecución en sandbox, tracing estructurado, evals de comportamiento, branch-per-agent. | **Aquí debería estar tu harness.** El `init.sh` como gate de verificación y los subagentes en contexto frío apuntan a esto. |
| **3** | Observability-first | Tracing end-to-end, LLM-as-judge scoring, middleware componible, memoria versionada. | Mejora continua. |
| **4** | Self-healing | Remediación automática, orquestación consciente de coste, governance-as-code. | **Emergente en 2026.** Trátalo como dirección, no como objetivo. |

La lectura de esta escalera es clara: **la Etapa 1 hace que el agente funcione. La Etapa 2 lo hace confiable. La Etapa 3 lo hace mejorable.** La mayoría del valor en producción está en la transición 2→3, y la mayoría de equipos que dicen estar en 3 en realidad están en 1.

### Modelo 3: GUIDO Scale (madurez organizacional + esfuerzo de migración)

Este modelo es el más completo porque **separa dos preguntas que CMMI no distingue**: "¿qué tan maduros son nuestros procesos?" y "¿cuánto esfuerzo nos costará migrar a SDD agéntico?". Evalúa disciplina de proceso, madurez de documentación, estructuras de governance, capacidades de automatización, readiness cultural para IA y complejidad de migración.

Los niveles GUIDO van de **1 (Caótico)** a **5 (Optimizado)**, y la señal clave es esta: **"Introducir agentes de IA en un estado caótico acelera el caos, no la entrega"**. Antes de adoptar SDD con multiagente, necesitas al menos:

- **Documentación a nivel de proyecto** (no solo de persona).
- **Governance parcial** (permisos, gates de revisión).
- **Adopción consistente de procesos** (no cada equipo a su manera).

### Modelo 4: Evaluación de SDLC Agéntico (9 dimensiones)

Este enfoque puntúa la organización en **nueve dimensiones independientes** en lugar de una sola nota agregada, porque "un solo número oculta más de lo que revela". Las dimensiones incluyen: ingeniería de contexto, adopción de herramientas, integración en workflow, revisión de código con IA, controles de governance, cobertura de skills, autonomía agéntica, generación de tests y gates de CI/CD con IA.

Para tu harness, las dimensiones críticas serían:
- **Cobertura de skills**: ¿existen skills para las tareas recurrentes reales del repo?
- **Controles de governance**: ¿están definidos los permisos, allow/deny lists y rutas de escalado?
- **Ingeniería de contexto**: ¿hay una única fuente de verdad actual que el agente lee, o documentación dispersa y obsoleta?

---

## 🎯 Respuesta consolidada: ¿qué nivel necesita tu equipo?

**Tu equipo necesita estar en Nivel 2 (Spec-Anchored) de SDD y Etapa 2 (Verified) de harness antes de que el patrón multiagente con roles diferenciados aporte valor sostenible.**

Eso implica, en términos prácticos:

1. **Procesos documentados y consistentes**: no "cada quien hace lo que puede", sino convenciones escritas en `AGENTS.md` que todos los agentes (y humanos) respetan.
2. **Specs versionadas en el repo**: el `scope.md` y `design.md` no son documentos efímeros de chat; viven en `.spec/` y son la fuente de verdad.
3. **Verificación ejecutable**: el `init.sh` corre lint, tests y typecheck, y es un gate que bloquea la transición de fase.
4. **Governance mínima**: permisos deny-first, revisión humana en el gate de aprobación del plan, PR-only (nunca auto-merge).
5. **Cobertura de skills para tareas recurrentes**: al menos el orquestador y una skill de revisión.

**Lo que NO necesitas para empezar**: self-healing, regeneración automática desde spec (Nivel 3), o compilación determinista (Nivel 4). Esos son destinos, no puntos de partida.

**La advertencia más importante**: si tu equipo está en GUIDO 1 (caótico) o en SDD Nivel 1 (spec efímera), introducir un harness multiagente no resolverá el problema; lo amplificará. La disciplina de escribir specs antes de código, y de verificar antes de mergear, es una **precondición humana**, no una capacidad que el agente aporte por sí solo.

