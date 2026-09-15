# ADR-002 — DeepSeek V4 Flash como modelo del rol `sdd-verifier`

- **Fecha**: 2026-09-15
- **Estado**: `aceptada`
- **Decisor**: Humano responsable del harness
- **Feature**: `_harness`
- **Tareas afectadas**: ninguna (afecta a `.harness/models.yaml` y `.github/agents/sdd-verifier.agent.md`)

## Contexto

El rol `sdd-verifier` necesita un modelo que (a) sea **distinto** al del `sdd-developer` para
evitar el error correlacionado, y (b) soporte **tool calling**, porque su trabajo incluye
ejecutar `./init.sh` y leer el diff (`tools: read, search, execute, todo`).

El humano indicó que en su selector de Copilot utilizaba **DeepSeek V4 Flash**. En una primera
versión de este harness el verificador se asignó a `deepseek-v4-pro` y luego a `gpt-5.6-terra`,
buscando siempre el "modelo más capaz". El humano corrigió: quiere DeepSeek V4 Flash.

El obstáculo fue de descubrimiento: DeepSeek V4 Flash **no aparece** en el catálogo nativo del
selector (`models.json`) y se concluyó por error que no existía. La evidencia mostró lo contrario:
lo aporta la extensión `DenizhanDaklr.copilot-vscode-deepseek-0.11.0`, que se registra como
`languageModelChatProviders` con `vendor: "deepseek"`.

Evidencia recogida del propio entorno:

| Comprobación | Fuente | Resultado |
| :--- | :--- | :--- |
| Catálogo nativo de Copilot | `models.json` (57 modelos) | DeepSeek **no está** |
| Provider de la extensión | `package.json` de la extensión | `languageModelChatProviders`, `vendor: deepseek` |
| Modelo activo | `chatSessions/<session>.jsonl` → `selectedModel` | `deepseek/deepseek-v4-flash`, name `DeepSeek V4 Flash` |
| Tool calling | mismo log | **390** llamadas (`run_in_terminal` 36×, `replace_string_in_file` 65×) |
| Agente visible en el chat | Comprobación del humano | `sdd-verifier` aparece en el selector de agentes |

## Decisión

**El rol `sdd-verifier` usa `DeepSeek V4 Flash`, aportado por la extensión
`DenizhanDaklr.copilot-vscode-deepseek`, referenciado con el nombre cualificado
`"DeepSeek V4 Flash (deepseek)"` y con `gpt-5.6-terra` como fallback.**

```yaml
sdd-verifier:
  model: "DeepSeek V4 Flash (deepseek)"
  model_id: "deepseek-v4-flash"
  runtime: "copilot"
  provided_by: "extension:DenizhanDaklr.copilot-vscode-deepseek"
  reasoning: "high"
  temperature: 0.0
  fallback: ["gpt-5.6-terra"]
```

La asignación resultante del harness queda:

| Rol | Modelo | Procedencia |
| :--- | :--- | :--- |
| `sdd-init` | Claude Sonnet 5 | nativa |
| `sdd-tech-lead` | GPT-5.6 Terra | nativa |
| `sdd-developer` | GPT-5.3-Codex | nativa |
| `sdd-verifier` | **DeepSeek V4 Flash** | **extensión** |
| `sdd-security-reviewer` | Claude Sonnet 5 | nativa |

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. `gpt-5.6-terra` (nativo)** | Sin dependencia de extensión; máxima capacidad; catálogo nativo | Deja al verificador y al `tech-lead` con el mismo modelo; ignora la elección del humano | El humano pidió explícitamente DeepSeek, y la independencia respecto al Developer se mantiene mejor con un proveedor distinto |
| **B. `deepseek-v4-pro` vía la API directa de DeepSeek** | No depende de la extensión; un solo punto de configuración | Requiere `DEEPSEEK_API_KEY` y saldo gestionado por el harness; sobrecomplica el Nivel 1 | El Nivel 1 busca el mínimo viable. La extensión ya resuelve la credencial |
| **C. Un modelo local (vLLM/Ollama)** | Coste cero, sin dependencia externa | Prohibido en Nivel 1 para el verificador por la regla propia del harness; requiere GPU | La verificación exige el máximo criterio disponible |
| **D. DeepSeek V4 Flash vía extensión de Copilot** | Es la elección del humano; distinto proveedor que el Developer; tool calling verificado | Depende de que la extensión esté instalada y con saldo | — (la elegida) |

## Consecuencias

**Positivas**
- El verificador usa un **proveedor distinto** al del Developer (DeepSeek frente a OpenAI), lo
  que reduce el riesgo de que ambos compartan el mismo punto ciego.
- Tool calling verificado en uso real; el rol puede ejecutar `./init.sh` y leer el diff.
- La credencial la gestiona la extensión, así que el harness **no** almacena ninguna clave (R9).

**Negativas / deuda asumida**
- **Dependencia de una extensión de terceros.** Si se desinstala, `sdd-verifier` no resuelve su
  modelo. Mitigación: `fallback: ["gpt-5.6-terra"]` y `provided_by` declarado, que hace visible
  la dependencia.
- El modelo consume saldo de DeepSeek; un 402 lo degradaría al fallback. Ya ocurrió una vez
  durante la construcción y **resuelve recargando saldo, no tocando el código**.
- Se asume como deuda menor un coste por verificación no trivial (modelo de razonamiento alto).

**Neutrales**
- El frontmatter usa el formato cualificado `"<name> (<vendor>)"`, que es el que documenta
  VS Code para modelos aportados por extensiones.

## Cómo revertir esta decisión

Barato: cambiar `model` del rol `sdd-verifier` en `.harness/models.yaml` a un modelo nativo
(p. ej. `gpt-5.6-terra`), retirar `model_id` y `provided_by`, y ejecutar
`bash scripts/sync-adapters.sh`. No hay que tocar ningún prompt ni artefacto SDD, gracias a la
regla de capas (AGENTS.md §4).

## Verificación de la decisión

- `python scripts/validate_harness.py` → **59 comprobaciones, COHERENTE**, con el modelo de
  extensión validado contra `catalog.copilot`.
- Frontmatter generado: `.github/agents/sdd-verifier.agent.md` → `model: "DeepSeek V4 Flash (deepseek)"`.
- **El agente `sdd-verifier` aparece en el selector de agentes del chat** (confirmado por el
  humano). Esto resuelve la única incertidumbre que quedaba abierta: el frontmatter acepta el
  nombre cualificado de un modelo aportado por extensión.

## Referencias

- ADR-001 de este mismo directorio (dónde se valida un nombre de modelo)
- `.harness/models.yaml` → `roles.sdd-verifier`, `catalog.copilot`
- `.harness/routing.yaml` → `aliases.copilot.model_map`
- `.agents/agents/sdd-verifier.md` (prompt del rol, agnóstico de modelo)
