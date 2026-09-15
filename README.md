# deepseek-harness

Harness SDD (Specification-Driven Development) **agnóstico de modelo**, para orquestación
multiagente sobre artefactos en disco.

La ley del repositorio es [`AGENTS.md`](./AGENTS.md). Es el archivo que **todo** agente lee como
precondición, y prevalece sobre cualquier prompt, skill o tarea.

---

## Arranque rápido

```bash
# 1. Traducir models.yaml → adaptadores de cada CLI (Claude Code, Antigravity, Codex)
bash scripts/sync-adapters.sh

# 2. Comprobar que las cuatro capas son coherentes
python scripts/validate_harness.py

# 3. Auto-diagnóstico en las 9 dimensiones del SDLC agéntico
python scripts/diagnose_harness.py --write

# 4. Gate de verificación (lint + formato + typecheck + tests + secretos)
bash init.sh
```

Detección temprana de problemas:

```bash
bash scripts/sync-adapters.sh --check   # ¿los adaptadores están desincronizados? (para CI)
python scripts/diagnose_harness.py --dimension 9   # una sola dimensión
```

---

## Arquitectura en cuatro capas

La separación estricta de capas es lo que hace el harness intercambiable de modelo: cambiar de
modelo **no** obliga a reescribir prompts.

| Capa | Ubicación | Qué contiene | ¿Menciona modelos? |
| :--- | :--- | :--- | :--- |
| **Ley** | `AGENTS.md` | Contrato compartido, reglas de oro, estándares | No |
| **Definición de rol** | `.agents/agents/*.md` | Qué hace cada agente, sus `tools`, sus salidas | **No** (verificado en CI) |
| **Configuración de ejecución** | `.harness/models.yaml` | Asignación rol → modelo | **Solo aquí** |
| **Adaptadores** | `.github/agents/`, `.claude/`, `.gemini/`, `.codex/` | Traducción al vocabulario de cada CLI | Generados |

**Ruta de uso principal**: GitHub Copilot en VS Code. `sync-adapters.sh` genera
`.github/agents/*.agent.md`, incrustando la ley y el prompt del rol en cada agente, porque
los subagentes de Copilot no leen `AGENTS.md` automáticamente.

`scripts/validate_harness.py` **falla** si un prompt de rol menciona un modelo: la regla se
comprueba, no se confía.

---

## Estructura

```
AGENTS.md                     Ley del repositorio (leída por todos los agentes)
harness.config.json           Comandos detectados, gates, guardrails
init.sh                       Gate único de verificación
.spec/                        Artefactos SDD (por feature)
.agents/
  ├── agents/                 5 roles: init, tech-lead, developer, verifier, security
  ├── skills/                 7 skills de Nivel 1
  └── policies/               Permisos deny-first + gates humanos
.harness/
  ├── models.yaml             Único punto de verdad de modelos
  ├── providers.yaml          Endpoints OpenAI-compatible
  └── routing.yaml            Fallback, errores no reintentables, alias
scripts/
  ├── sync-adapters.sh        models.yaml → adaptadores de cada CLI
  ├── validate_harness.py     Coherencia entre las cuatro capas
  ├── diagnose_harness.py     Auto-diagnóstico de 9 dimensiones
  └── harness_yaml.py         Parser YAML sin dependencias externas
```

---

## Roles y ciclo SDD

```
humano: prompt de feature
  └─ sdd-init         → scope.md                    ── G1 (humano) ──┐
       └─ sdd-tech-lead → design.md + tasks/        ── G2 (humano) ──┤
            └─ sdd-developer (× N tareas, 1 commit cada una)         │
                 └─ sdd-verifier → verify.md                        │
                      ├─ (opcional) sdd-security-reviewer           │
                      └─ veredicto ────────────────── G3 (humano) ──┘
```

Cada subagente arranca **en frío**: lee `AGENTS.md` y **solo** sus artefactos de entrada.
Los gates G1/G2/G3 exigen aprobación humana; ningún agente aprueba su propio gate.

### Skills de Nivel 1

| Skill | Para qué | La usa |
| :--- | :--- | :--- |
| `sdd-orchestrator` | Delega fases, resuelve modelo por rol, respeta gates | Orchestrator |
| `spec-authoring` | Convierte una petición vaga en criterios verificables | sdd-init |
| `task-decomposition` | Diseño → tareas atómicas de un commit | sdd-tech-lead |
| `gate-runner` | Ejecuta e interpreta `init.sh`; clasifica el fallo | Developer, Verifier |
| `verify-report` | Produce `verify.md` con evidencia y veredicto | sdd-verifier |
| `adr-record` | Registra decisiones con alternativas y consecuencias | sdd-tech-lead |
| `security-review` | Checklist de seguridad sobre el diff | sdd-security-reviewer |
| `model-switching` | Cambia el modelo de un rol; diagnostica 401/402/403 | Humano |

---

## Cambiar el modelo de un rol

Edita **una línea** en `.harness/models.yaml` y resincroniza:

```yaml
# .harness/models.yaml
roles:
  sdd-developer:
    model: "claude-sonnet-5"   # ← el único cambio
    runtime: "copilot"
```

```bash
bash scripts/sync-adapters.sh && python scripts/validate_harness.py
```

Los prompts, los artefactos SDD y los adaptadores no se tocan.

### Catálogo de modelos: DOS procedencias

El nombre del modelo se valida contra el **catálogo del runtime**, no contra la
documentación de una API. En GitHub Copilot hay dos vías distintas, y confundirlas
es un error real que se cometió al construir este harness:

| Procedencia | Cómo llega | Dónde se ve |
| :--- | :--- | :--- |
| **Nativo** | Lo sirve GitHub | `models.json` del `workspaceStorage` (`model_picker_enabled`) |
| **Extensión** | `languageModelChatProviders` de una extensión | `package.json` de la extensión |

#### Nativos confirmados en este entorno

`claude-sonnet-5`, `gpt-5.6-terra`, `gpt-5.3-codex`, `gpt-5.4`, `gpt-5.4-mini`,
`gemini-3.8-flash`, `claude-haiku-4.5`, `mai-code-1.1-flash`.

> Nota: `gpt-5.3-codex` **existe en Copilot** aunque no figure en la documentación de
> la API de OpenAI. Son catálogos distintos.

#### Aportados por extensión

| Modelo | Extensión | Cómo referenciarlo |
| :--- | :--- | :--- |
| **DeepSeek V4 Flash** | `DenizhanDaklr.copilot-vscode-deepseek` | `model: "DeepSeek V4 Flash (deepseek)"` + `model_id` |

**DeepSeek V4 Flash está operativo y con saldo**, usando tool calling (verificado por
el propio uso: `run_in_terminal`, `replace_string_in_file`, etc.).

El catálogo completo y su procedencia están en `.harness/models.yaml` → `catalog.copilot`.

### Errores del proveedor

| Código | Significado | Acción |
| :--- | :--- | :--- |
| **401** | Credencial inválida | Revisar la configuración del proveedor en la extensión |
| **402** | **Saldo/cuota agotados** | Recargar crédito o usar fallback. Es facturación, **no** un bug del prompt |
| **403** | Modelo no permitido | Revisar allowlist o cambiar de modelo |
| **404** | Modelo inexistente | Nombre mal escrito. Consulta el catálogo en `models.yaml` |
| **429** / **5xx** | Rate limit / fallo del proveedor | Reintento con backoff (ya configurado) |

Detalle completo en la skill `model-switching`.

---

## Estado del harness

Última ejecución de `python scripts/diagnose_harness.py`:

| # | Dimensión | Puntuación |
| :-- | :--- | :--- |
| 1 | Ingeniería de contexto | 4/4 |
| 2 | Adopción de herramientas | 4/4 |
| 3 | Integración en el workflow | 4/4 |
| 4 | Revisión de código con IA | 4/4 |
| 5 | Controles de governance | 4/4 |
| 6 | Cobertura de skills | 4/4 |
| 7 | Autonomía agéntica | 4/4 |
| 8 | Generación de tests | 4/4 |
| 9 | Gates de CI/CD con IA | 3/4 |

**35/36 (97%)** — Niveles 1 y 2 alcanzados, con una salvedad: los checks de `lint`, `format`,
`typecheck`, `tests`, `secrets` y `guardrails` están **inertes** hasta que exista código y un
repositorio git. La dimensión 9 ya está penalizada por ello; el informe completo lista qué falta.

Informe completo: [`.spec/_harness/diagnostic.md`](./.spec/_harness/diagnostic.md).

---

## Requisitos

- **Bash** (Git Bash o WSL) para `init.sh` y `sync-adapters.sh`.
- **Python 3.10+** para los scripts.
- Opcionales, y cada uno mejora un check del gate: `gitleaks`, `ruff`, `mypy`, `pytest`, `git`.
- `scripts/harness_yaml.py` no requiere dependencias: usa PyYAML si está, y si no, un parser
  interno (así el harness funciona en imágenes mínimas y entornos air-gapped).
