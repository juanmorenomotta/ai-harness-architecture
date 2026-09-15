# ADR-001 — Validar el nombre del modelo contra el catálogo del runtime, no contra la API

- **Fecha**: 2026-09-15
- **Estado**: `aceptada`
- **Decisor**: Orchestrator (a propuesta del humano responsable del harness)
- **Feature**: `_harness` (decisión sobre el propio harness, no sobre una feature)
- **Tareas afectadas**: ninguna (afecta a `scripts/validate_harness.py` y `.harness/models.yaml`)

## Contexto

Al construir el harness, `.harness/models.yaml` declaraba modelos como `claude-sonnet-5`,
`gpt-5-mini`, `gpt-5.3-codex` y `deepseek-v4-flash`. Se quiso verificar que existían y se
consultó la **documentación pública de las APIs** de OpenAI, Anthropic y DeepSeek.

Esa consulta produjo una conclusión falsa: `gpt-5.3-codex` y `gpt-5-mini` "no existían", así
que el archivo se "corrigió" a `gpt-6-astra`, `gpt-5.6-terra` y `claude-sonnet-5`.

El resultado fue un daño real: los **cinco agentes** de `.github/agents/` quedaron apuntando a
modelos que el entorno no ofrece, y el verificador pasó a usar un modelo distinto del que el
humano había elegido. Los agentes dejaron de ser usables.

La causa raíz no fue un dato equivocado, sino un **error de fuente**: se validó contra el
catálogo equivocado. En este repositorio los agentes no llaman a una API; los ejecuta el
selector de modelos de GitHub Copilot, y ese selector tiene su propio catálogo, con **dos
procedencias distintas**:

1. **Nativos**: los sirve GitHub. Se enumeran en `models.json` (campo `model_picker_enabled`).
2. **De extensión**: los aporta una extensión de terceros vía `languageModelChatProviders`.
   **No aparecen** en `models.json`.

`gpt-5.3-codex` es nativo de Copilot pero no figura en los docs de la API de OpenAI.
`DeepSeek V4 Flash` no es nativo pero lo aporta `DenizhanDaklr.copilot-vscode-deepseek`.

## Decisión

**El nombre de un modelo se valida contra el catálogo del runtime que lo ejecuta, y ese catálogo
incluye tanto los modelos nativos como los aportados por extensiones.** La asignación por rol
vive en `.harness/models.yaml` → `catalog.<runtime>.models`, y cada entrada declara su
`provided_by`.

Cuando un modelo lo aporta una extensión, se declaran dos campos:

```yaml
model: "DeepSeek V4 Flash (deepseek)"   # nombre cualificado que acepta el frontmatter
model_id: "deepseek-v4-flash"           # id limpio: es lo que se valida
provided_by: "extension:DenizhanDaklr.copilot-vscode-deepseek"
```

`scripts/validate_harness.py` **falla** si el modelo de un rol no está en el catálogo del
runtime, considerando ambas procedencias.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Validar contra la documentación de la API del fabricante** | Fuente pública, siempre accesible, sin depender del entorno | Catálogo distinto del runtime. Produce falsos 404 y "correcciones" que rompen el harness. Fue exactamente el fallo cometido | Es la causa raíz del incidente. Una API y un runtime agéntico no son el mismo catálogo |
| **B. No validar: confiar en que el humano escriba bien el nombre** | Cero mantenimiento | Un typo pasa desapercibido hasta que el agente falla en tiempo de ejecución, con un 404 opaco | Deja sin red de seguridad el punto que ya falló una vez |
| **C. Validar contra el catálogo nativo de Copilot únicamente** | Fácil: existe un archivo con la lista (`models.json`) | Ignora los modelos de extensión. Concluye que DeepSeek "no existe" cuando sí está disponible | Reproduce el segundo error del incidente |
| **D. Validar contra el catálogo del runtime, nativo + extensión** | Refleja la realidad del entorno; detecta typos y evita falsos negativos | Requiere mantener el catálogo en `models.yaml` y declarar `provided_by` | — (la elegida) |

## Consecuencias

**Positivas**
- El validador detecta un nombre de modelo inválido **antes** de que el agente falle en ejecución.
- Queda registrado de dónde sale cada modelo (`native` o `extension:<id>`), lo que permite
  distinguir "no existe" de "no está instalado".
- La regla de capas se mantiene: los prompts de rol siguen sin mencionar modelos.

**Negativas / deuda asumida**
- El catálogo es un duplicado parcial del entorno y puede quedar desactualizado cuando el
  usuario instale, quite o actualice una extensión o un modelo. **Se acepta**: un catálogo
  desactualizado produce un falso error, no un falso verde, y el mensaje indica qué revisar.
- Añade dos campos (`model_id`, `provided_by`) para modelos de extensión, lo que hace la
  entrada más verbosa que un simple nombre.

**Neutrales**
- Los adaptadores de otros CLIs (`.claude/`, `.gemini/`, `.codex/`) siguen funcionando igual;
  solo cambia la fuente contra la que se valida.

## Cómo revertir esta decisión

Barato. Basta con devolver `_check_role_catalog` a una comprobación contra
`providers.yaml` y retirar `active_runtime` y `catalog` de `models.yaml`. Coste: se pierde la
detección de typos y vuelve a ser posible el falso negativo con modelos de extensión.

## Verificación de la decisión

No basta con que el validador pase: **un validador que nunca ha fallado no ha demostrado nada**.
Se ejecutó una prueba negativa con un modelo inventado (`modelo-que-no-existe-123`) y se
comprobó que el validador **sale con código 1** y lo señala:

```
x 'sdd-tech-lead': el modelo 'modelo-que-no-existe-123' no está en el catálogo del
  runtime 'copilot'. Válidos: claude-haiku-4.5, claude-sonnet-5, deepseek-v4-flash, ...
== INVÁLIDO: 2 incoherencia(s) ==
```

## Referencias

- `scripts/validate_harness.py` → `runtime_catalog()`, `_check_role_catalog()`
- `.harness/models.yaml` → `active_runtime`, `catalog.copilot`
- `.harness/routing.yaml` → `aliases.copilot.model_map`
- `.agents/skills/model-switching/SKILL.md` → "El error de criterio que hay que evitar"
- Evidencia del catálogo: `%APPDATA%/Code/User/workspaceStorage/<id>/GitHub.copilot-chat/debug-logs/<session>/models.json`
