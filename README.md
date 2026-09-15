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

```bash
# .harness/models.yaml
roles:
  sdd-developer:
    model: "claude-sonnet-5"   # ← el único cambio
    provider: "anthropic"

bash scripts/sync-adapters.sh && python scripts/validate_harness.py
```

Los prompts, los artefactos SDD y los adaptadores no se tocan.

### Modelos verificados (2026-09-15)

Contrastados con la documentación oficial de cada proveedor. **Varios nombres habituales
ya no existen**, así que conviene no copiarlos de memoria:

| Proveedor | Válidos | ⚠ Ya no existen |
| :--- | :--- | :--- |
| **DeepSeek** | `deepseek-flash`, `deepseek-v4-pro` | ~~`deepseek-v4-flash`~~ (retirado; lo sirve V4.1-Flash) |
| **Anthropic** | `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5-1`, `claude-haiku-4-5` | ~~`claude-sonnet-4-20250514`~~, ~~`claude-opus-4-*`~~ |
| **OpenAI** | `gpt-6-astra`, `gpt-5.6`, `gpt-5.6-terra`, `gpt-5.6-luna` | ~~`gpt-5-mini`~~, ~~`gpt-5.3-codex`~~, ~~`gpt-5.4`~~ |
| **Google** | `gemini-3.8-flash`, `gemini-3.7-flash` | ~~`gemini-3-pro-preview`~~ (apagado) |

El catálogo completo está en `.harness/models.yaml` → `catalog`.

### Errores del proveedor

| Código | Significado | Acción |
| :--- | :--- | :--- |
| **401** | Credencial inválida | Revisar la variable de entorno del proveedor |
| **402** | **Saldo/cuota agotados** | Recargar crédito o usar fallback. Es facturación, **no** un bug del prompt |
| **403** | Modelo no permitido | Revisar allowlist o cambiar de proveedor |
| **404** | Modelo inexistente | Typo en `models.yaml`. Consulta la tabla de arriba |
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
