# ADR — Registro de decisiones del harness

Decisiones arquitectónicas sobre `.spec/_harness`. Cada ADR es **inmutable**: si una decisión
cambia, se escribe uno nuevo y el anterior pasa a `reemplazada por ADR-NNN`.

| ADR | Título | Estado | Fecha |
| :--- | :--- | :--- | :--- |
| [001](./001-validar-modelos-contra-catalogo-del-runtime.md) | Validar el nombre del modelo contra el catálogo del runtime, no contra la API | `aceptada` | 2026-09-15 |
| [002](./002-deepseek-v4-flash-como-verificador.md) | DeepSeek V4 Flash como modelo del rol `sdd-verifier` | `aceptada` | 2026-09-15 |

## Por qué estas decisiones existen

Este harness se construyó cometiendo y corrigiendo dos errores reales, y ambos quedaron
registrados porque son fáciles de repetir:

1. **Validar contra la fuente equivocada.** Se comprobaron nombres de modelo contra la
   documentación de las APIs de OpenAI/Anthropic en lugar de contra el catálogo del runtime que
   ejecuta los agentes. Varios nombres "corregidos" rompieron los cinco agentes. → ADR-001.

2. **Confundir catálogo nativo con extendido.** `DeepSeek V4 Flash` no aparece en el catálogo
   nativo de Copilot, y se concluyó que no existía. Lo aporta una extensión de terceros vía
   `languageModelChatProviders`. → ADR-002.

La lección transversal: **un validador que nunca ha fallado no ha demostrado nada.** Por eso
`scripts/validate_harness.py` se probó con un modelo inventado (`modelo-que-no-existe-123`) para
confirmar que falla de verdad (código de salida 1) en lugar de dar un falso verde.
