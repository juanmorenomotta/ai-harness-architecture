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

2. **Comprueba que el proveedor existe** en `.harness/providers.yaml` y que la variable de
   entorno está definida **en tu shell**, nunca escrita en un archivo del repo (R9):

   ```bash
   # Comprobar SIN imprimir el valor
   [ -n "${DEEPSEEK_API_KEY:-}" ] && echo "definida" || echo "FALTA"
   ```

3. **Sincroniza los adaptadores**:

   ```bash
   bash scripts/sync-adapters.sh
   ```

   Esto traduce `models.yaml` a `.claude/settings.json`, `.gemini/config.yaml`,
   `.codex/config.toml` y `.env.harness`. Si el script detecta que un rol no tiene modelo
   asignado, **falla** en lugar de inventar uno.

4. **Valida la coherencia**:

   ```bash
   python scripts/validate_harness.py
   ```

5. **Prueba el rol con una tarea trivial** antes de confiar en el cambio. Un modelo nuevo con
   tareas reales sin prueba es una apuesta.

6. **Registra el cambio**: si el cambio de modelo responde a una decisión relevante (coste,
   calidad, privacidad), escribe un ADR (`skills/adr-record`).

## Diagnóstico de errores del proveedor

| Código | Significado | Acción |
| :--- | :--- | :--- |
| **401** | Credencial inválida/revocada | Revisar la variable de entorno del proveedor. **No** es un problema del prompt. |
| **402** | **Saldo/cuota agotados** | Recargar crédito, o cambiar a un fallback. Es **facturación**, no código. |
| **403** | Modelo no permitido para esa cuenta | Revisar allowlist; cambiar de modelo o de proveedor. |
| **404** | Modelo inexistente | Typo en `models.yaml`. Verificar el nombre exacto del catálogo. |
| **429** | Rate limit | Reintentar con backoff (`routing.yaml` ya lo define). |
| **5xx** | Fallo del proveedor | Reintentar; si persiste, activar fallback. |

Un **402** jamás debe interpretarse como un bug del harness. Si ocurre, el `on_balance_exhausted:
block` de `routing.yaml` produce el bloqueo con instrucciones.

## Cambiar a un modelo local

1. Levanta el servidor OpenAI-compatible (vLLM, Ollama, LM Studio):
   ```bash
   vllm serve <modelo> --port 8000
   ```
2. Verifica que responde en `http://localhost:8000/v1/models`.
3. Apunta el rol a `provider: "local"` en `models.yaml`.
4. **Restricción de Nivel 1**: no asignes modelos locales al rol `sdd-verifier`. La verificación
   exige el máximo criterio disponible.

## Prohibiciones

- ❌ Escribir un nombre de modelo en un archivo de `.agents/agents/`.
- ❌ Poner la API key en cualquier archivo del repo (R9).
- ❌ Cambiar el modelo del Verifier y del Developer al mismo tiempo y no notar que la
  verificación pierde independencia.
- ❌ Editar `.harness/` desde una tarea SDD (R4): el cambio va en PR separado.

## Ver también

- [`.harness/models.yaml`](../../../.harness/models.yaml)
- [`.harness/providers.yaml`](../../../.harness/providers.yaml)
- [`.harness/routing.yaml`](../../../.harness/routing.yaml)
- Script `sync-adapters.sh`
