---
name: model-switching
description: "Cambia el modelo de un rol editando models.yaml y sincronizando adaptadores. Use when swapping the model for a role, switching to a local model, fixing a 402/401 provider error, or updating provider credentials."
argument-hint: "<rol> <modelo>"
---

# Model Switching

Cambiar el modelo de un rol **nunca** implica editar prompts. Es una edición de una línea en
`.harness/models.yaml` seguida de una sincronización.

## Cuándo usar

- Quieres un modelo distinto para un rol (más barato, más rápido, local).
- Un proveedor falla (401, 402, 403, 404) y hay que cambiar o activar el fallback.
- Añades un proveedor nuevo.
- Migras de Nivel 1 (un modelo por rol) a enrutamiento dinámico.

## Por qué la separación importa

| Capa | Archivo | Contiene |
| :--- | :--- | :--- |
| **Definición del rol** | `.agents/agents/*.md` | Qué hace el agente. **Sin nombre de modelo.** |
| **Configuración de ejecución** | `.harness/models.yaml` | Qué modelo usa cada rol. |
| **Proveedores** | `.harness/providers.yaml` | Endpoints y variables de entorno. |
| **Enrutamiento** | `.harness/routing.yaml` | Fallback, error handling, alias. |

Si mezclas la primera con la segunda, cambiar de modelo obliga a reescribir prompts y a
re-verificar que ningún agente se comporta distinto. Evítalo.

## Procedimiento

1. **Edita solo `.harness/models.yaml`**:

   ```yaml
   roles:
     sdd-developer:
       model: "qwen-3-coder-480b"     # ← la única línea que cambia
       provider: "local"
   ```

2. **Comprueba que el proveedor existe** en `.harness/providers.yaml`. Y si el modelo lo
   aporta una extensión, declara su procedencia en `models.yaml`:

   ```yaml
   sdd-verifier:
     model: "DeepSeek V4 Flash (deepseek)"   # lo que acepta el frontmatter
     model_id: "deepseek-v4-flash"           # id limpio: es lo que se valida
     provided_by: "extension:DenizhanDaklr.copilot-vscode-deepseek"
   ```

   Para un modelo nativo basta con `model` (p. ej. `"Claude Sonnet 5"`).

3. **Sincroniza los adaptadores**:

   ```bash
   bash scripts/sync-adapters.sh
   ```

   Esto traduce `models.yaml` a `.github/agents/*.agent.md`, `.claude/settings.json`,
   `.gemini/config.yaml`, `.codex/config.toml` y `.env.harness`. Si el script detecta que un
   rol no tiene modelo asignado, **falla** en lugar de inventar uno.

4. **Valida la coherencia**: `python scripts/validate_harness.py`. Si dice que el modelo no
   está en el catálogo, comprueba **las dos procedencias** (nativa y de extensión) antes de
   cambiar nada; el error suele estar en la comprobación, no en el archivo.

5. **Prueba el rol con una tarea trivial** antes de confiar en el cambio. Un modelo nuevo con
   tareas reales sin prueba es una apuesta.

6. **Registra el cambio**: si responde a una decisión relevante (coste, calidad, privacidad),
   escribe un ADR (`skills/adr-record`).

## Diagnóstico de errores del proveedor

| Código | Significado | Acción |
| :--- | :--- | :--- |
| **401** | Credencial inválida/revocada | Revisar la configuración del proveedor. **No** es un problema del prompt. |
| **402** | **Saldo/cuota agotados** | Recargar crédito, o cambiar a un fallback. Es **facturación**, no código. |
| **403** | Modelo no permitido para esa cuenta | Revisar allowlist; cambiar de modelo o de proveedor. |
| **404** | Modelo inexistente | Nombre mal escrito. Validar contra el catálogo del **runtime**. |
| **429** | Rate limit | Reintentar con backoff (`routing.yaml` ya lo define). |
| **5xx** | Fallo del proveedor | Reintentar; si persiste, activar fallback. |

Un **402** jamás debe interpretarse como un bug del harness. Si ocurre, el `on_balance_exhausted:
block` de `routing.yaml` produce el bloqueo con instrucciones. Se resuelve recargando saldo,
no tocando el código.

### El error de criterio que hay que evitar

**El nombre del modelo se valida contra el catálogo del RUNTIME que lo ejecuta, no contra la
documentación de la API del fabricante.** Son catálogos distintos:

| Runtime | Catálogo válido | Dónde consultarlo |
| :--- | :--- | :--- |
| GitHub Copilot (VS Code) | Nombres del selector | `models.json` en el `workspaceStorage` (`model_picker_enabled`) |
| GitHub Copilot + extensión | Nombres del `languageModelChatProviders` | `package.json` de la extensión |
| Llamada directa a la API | Nombres de la API | Documentación del proveedor |

Ejemplo real: `gpt-5.3-codex` no aparece en los docs de la API de OpenAI, pero sí en el
selector de Copilot. Y `DeepSeek V4 Flash` no aparece en el catálogo nativo de Copilot,
pero sí en el que aporta la extensión. Confundir estas fuentes lleva a "corregir" un
archivo que estaba bien.

## Cambiar a un modelo local

1. Levanta el servidor OpenAI-compatible (vLLM, Ollama, LM Studio):
   ```bash
   vllm serve <modelo> --port 8000
   ```
2. Verifica que responde en `http://localhost:8000/v1/models`.
3. Apunta el rol a `provider: "local"` en `models.yaml`.
4. **Restricción de Nivel 1**: no asignes modelos locales al rol `sdd-verifier`. La
   verificación exige el máximo criterio disponible.

## Prohibiciones

- ❌ Escribir un nombre de modelo en un archivo de `.agents/agents/`.
- ❌ Poner la API key en cualquier archivo del repo (R9). En VS Code, la credencial de una
  extensión se guarda en su propia configuración, no en el harness.
- ❌ Cambiar el modelo del Verifier y del Developer al mismo tiempo y no notar que la
  verificación pierde independencia.
- ❌ Editar `.harness/` desde una tarea SDD (R4): el cambio va en PR separado.

## Ver también

- [`.harness/models.yaml`](../../../.harness/models.yaml)
- [`.harness/providers.yaml`](../../../.harness/providers.yaml)
- [`.harness/routing.yaml`](../../../.harness/routing.yaml)
- Script `sync-adapters.sh`
