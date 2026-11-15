# ADR-022 — Los agentes gobiernan desde el harness; los componentes no llevan agentes

- **Fecha**: 2026-11-15
- **Estado**: `aceptada` · **Implementación**: **HECHA en este PR** (pendiente de revisión humana)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Refina**: ADR-021 (su §3 y §4 asumían agentes copiados al componente) y ADR-019 (la
  «autosuficiencia» del componente, que incluía `validate_harness.py` y los adaptadores)
- **Tareas afectadas**:
  - `scripts/instantiate_harness.py` (`HARNESS_ONLY_PATHS`, §4 generada, README generado)
  - `.agents/policies/permissions.yaml` (rutas relativas al workspace)
  - `templates/workspace/.vscode/{tasks,settings}.json` (nuevo)
  - `templates/permissions/{laravel,vue}.yaml` (nuevo; sustituyen a
    `.agents/policies/templates/permissions.*.yaml` de ADR-021, eliminadas)
  - `README.md` (sección «Workspace de desarrollo»)

## Contexto

ADR-021 resolvió la inyección del harness en los componentes `backend` y `frontend`
asumiendo que cada instancia llevaría su propia copia de los 5 roles SDD y sus adaptadores.
Al diseñar la operación real apareció el modelo correcto: **el humano abre VS Code en la
raíz del workspace** (la carpeta padre que contiene harness y componentes) y la gobernanza
se ejecuta **desde el harness**. Copiar los agentes a cada componente tendría tres
consecuencias indeseadas:

1. **Copias idénticas que divergen en silencio** — el patrón transversal de este
   repositorio (ver ADR-004, ADR-015): el mismo rol en N componentes deja de actualizarse
   a la par sin que nada lo detecte.
2. **Selector de agentes duplicado** en el chat (mismo nombre, N ubicaciones).
3. Cada componente arrastraría `scripts/`, `.claude/`, `.gemini/`, `.codex/` y las
   plantillas del molde, que no usa.

Además, habilitar los agentes desde el workspace es un mecanismo ya existente:
`chat.agentFilesLocations` en `.vscode/settings.json` apuntando a
`ai-harness-architecture/.github/agents`.

## Decisión

**Los agentes (roles, skills, políticas, adaptadores y herramientas) viven únicamente en el
harness. Un componente instanciado recibe solo ley, gate, configuración y `.spec/` propio.
La política de permisos del harness usa rutas relativas a la raíz del workspace. Los
comandos y la habilitación de agentes del workspace se entregan como plantilla que el humano
copia manualmente a `<workspace>/.vscode/`.**

### 1. Qué recibe un componente (y qué no)

| Recibe | Ya NO recibe |
| :--- | :--- |
| `AGENTS.md` (generado) | `.agents/` (roles, skills, políticas) |
| `init.sh` (gate) | `.github/agents/`, `.claude/`, `.gemini/`, `.codex/` |
| `harness.config.json` | `scripts/` (las herramientas corren desde el harness) |
| `.harness/` (procedencia) | `templates/`, `docs/`, `.spec/_harness/` |
| `.spec/` vacío, `README.md` | `.env.harness` |

`HARNESS_ONLY_PATHS` del instanciador se amplía en consecuencia. La §4 generada y el
`README.md` del componente pasan a instruir el arranque **desde la raíz del workspace**.

### 2. Anclaje de rutas en la política (única, en el harness)

Los agentes corren con el workspace como cwd, así que `permissions.yaml` distingue dos
anclajes:

- **Roles SDD** (`sdd-init`, `sdd-tech-lead`, `sdd-developer`, `sdd-verifier`): rutas
  **relativas a la raíz del workspace**, prefijadas por componente (`backend/`,
  `frontend/`, `ai-harness-architecture/` para las features del propio harness).
  **Agregar un componente = agregar sus rutas por PR humana** (fragmentos de referencia por
  stack en `templates/permissions/`).
- **`harness-maintainer`**: rutas relativas a la **raíz del harness**, sin prefijo
  (`scripts/**`, `.harness/**`, …). El validador exige esas cadenas exactas
  (`check_harness_maintainer_limits`); cambiarlas rompería el control, no solo el estilo.

La ley generada de cada componente queda protegida con un patrón nuevo de `global_deny`:
`**/AGENTS.md`.

### 3. `.vscode` del workspace: plantilla + paso manual

`templates/workspace/.vscode/` contiene:

- `settings.json` — habilita `ai-harness-architecture/.github/agents` en el chat.
- `tasks.json` — comandos de gobernanza: validar el harness, sincronizar adaptadores,
  instanciar/verificar componentes y correr el gate (`bash init.sh`) de cada componente.

La copia a la raíz del workspace es **manual y está documentada en el README**: el harness
no escribe fuera de sí mismo (mismo principio que R4).

### 4. Sustitución de las plantillas de ADR-021

Las plantillas de política completa (`.agents/policies/templates/permissions.*.yaml`,
creadas en ADR-021) quedan **sustituidas** por fragmentos de referencia por stack en
`templates/permissions/`: ya no hay ninguna política que copiar al componente; lo que se
propaga por PR humana son **rutas** dentro de la política única del harness.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Agentes duplicados por componente** (ADR-021 §4) | Cada componente «autónomo» en VS Code | Copias que divergen en silencio; selector duplicado; mantener N juegos de adaptadores | Es el patrón que este repo persigue: un dato crítico en copias |
| **B. Orquestador agente con MCP cross-repo** | Fan-out automático | Complejidad (CAO/tmux/MCP) y rompe el arranque en frío | El fan-out humano desde el harness es explícito y suficiente |
| **C. Política por componente** | Rutas sin prefijo | N políticas que mantener; el agente corre con cwd = workspace, no con cwd = componente | Una política única con rutas prefijadas es auditable en un solo archivo |
| **D. Agentes solo en el harness + `.vscode` del workspace** | Un solo juego de agentes; mecanismo nativo de VS Code; componente mínimo | La política queda acoplada a los nombres de carpeta del workspace | Aceptable: ADR-020 fija un clon del harness por aplicación |

## Consecuencias

**Positivas**
- **Un solo juego de agentes** que mantener; imposible que diverjan entre componentes.
- El selector del chat no muestra duplicados.
- Instanciar un componente queda mínimo y su estructura no arrastra maquinaria del molde.
- El `.vscode` del workspace es explícito, revisable y se instala con una sola copia.

**Negativas / deuda asumida**
- **El componente ya no auto-valida la coherencia del harness**: `validate_harness.py` es
  herramienta del harness; la verificación de una instancia queda en
  `instantiate_harness.py --check`. ADR-019 §«autosuficiencia» queda refinada en ese punto.
- La política del clon referencia carpetas concretas (`backend/`, `frontend/`). Es
  deliberado (ADR-020: un clon por aplicación); el molde aguas arriba conservaría rutas
  genéricas.
- Las rutas de `permissions.yaml` son **declarativas** para Copilot (no las impone el
  runtime): su fuerza es la misma que tienen hoy — instrucción normativa + revisión humana.
- ADR-016 se mantiene, pero el «abre VS Code en el componente» de ADR-019 pasa a ser
  «abre VS Code en la raíz del workspace».

**Neutrales**
- `validate_harness.py` y `init.sh` no cambian; el validador sigue en **COHERENTE** con la
  nueva política (136 comprobaciones).
- ADR-021 queda parcialmente refinada; no se edita (los ADR son inmutables), queda enlazada
  desde el índice.

## Cómo revertir esta decisión

Restaurar `HARNESS_ONLY_PATHS` a su lista anterior y volver a copiar `.agents/` a las
instancias. Se pierde la garantía de un solo juego de agentes. Barato de ejecutar; el
riesgo asumido (deriva silenciosa entre copias) es alto.

## Cómo se verificó / se verificará

1. `python scripts/validate_harness.py` → **COHERENTE (136 comprobaciones, exit 0)** con la
   política de rutas prefijadas (hecho en este PR).
2. Tras el commit (árbol limpio): instanciación de prueba en carpeta temporal → el
   componente resultante **no** contiene `.agents/`, `.github/agents/`, `scripts/`,
   `templates/` ni adaptadores; `--check` → **INSTANCIA COHERENTE**; la carpeta temporal se
   elimina.
3. **Prueba negativa**: `sdd-developer` con cwd = workspace intenta escribir
   `backend/composer.json` → fuera de `writable_paths`, bloqueado; intenta
   `backend/.spec/x/verify.md` → bloqueado por `protected_paths` (verificación en la primera
   feature real).

## Referencias

- ADR-016 (arranque en frío por conversación nueva), ADR-019 (instanciador), ADR-020 (un
  clon por aplicación), ADR-021 (inyección y permisos por stack — refinada aquí),
  ADR-007 (límites del maintainer)
- `scripts/instantiate_harness.py`, `.agents/policies/permissions.yaml`,
  `templates/workspace/.vscode/`, `templates/permissions/`, `README.md`
