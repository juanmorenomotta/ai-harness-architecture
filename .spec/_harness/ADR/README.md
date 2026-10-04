# ADR — Registro de decisiones del harness

Decisiones arquitectónicas sobre `.spec/_harness`. Cada ADR es **inmutable**: si una decisión
cambia, se escribe uno nuevo y el anterior pasa a `reemplazada por ADR-NNN`.

| ADR | Título | Estado | Fecha |
| :--- | :--- | :--- | :--- |
| [001](./001-validar-modelos-contra-catalogo-del-runtime.md) | Validar el nombre del modelo contra el catálogo del runtime, no contra la API | `aceptada` | 2026-09-15 |
| [002](./002-deepseek-v4-flash-como-verificador.md) | DeepSeek V4 Flash como modelo del rol `sdd-verifier` | `aceptada` | 2026-09-15 |
| [003](./003-relacion-agente-skill-como-dato-verificable.md) | La relación agente ↔ skill es un dato verificable, declarado en una sola dirección | `aceptada` | 2026-09-25 |
| [004](./004-identificador-unico-de-version-del-harness.md) | Identificador único de versión del harness (`.harness/harness.version` + check) | `aceptada` (impl. hecha 2026-10-04) | 2026-09-27 |
| [005](./005-un-solo-harness-base-especializacion-en-nivel-3.md) | Un solo harness base; la especialización por dominio vive en el nivel 3 | `aceptada` (impl. pendiente) | 2026-09-27 |
| [006](./006-agents-md-del-proyecto-generado.md) | El `AGENTS.md` del proyecto es un artefacto generado | `aceptada` (impl. pendiente) | 2026-09-27 |
| [007](./007-rol-harness-maintainer.md) | Rol `harness-maintainer`; `scripts/` no es escribible por el Developer | `aceptada` (impl. hecha 2026-10-04, pendiente de revisión humana) | 2026-09-27 |
| [008](./008-ciclo-completo-para-toda-aplicacion.md) | Ciclo SDD completo para todo componente de aplicación, sin umbral de tamaño | `aceptada` (impl. pendiente) | 2026-09-27 |
| [009](./009-primera-aplicacion-auth-laravel.md) | Módulo de autenticación (Laravel 12 / PHP 8.2) como primera aplicación y template | `aceptada` (impl. pendiente) | 2026-09-27 |
| [010](./010-remoto-privado-en-github.md) | Remoto privado en GitHub para que R3 sea ejecutable | `aceptada` (impl. pendiente) | 2026-09-27 |
| [011](./011-g3-revision-local-y-proteccion-inerte.md) | G3 es revisión humana local; la protección de rama queda inerte y declarada | `aceptada` (impl. pendiente) | 2026-09-27 |
| [012](./012-un-nivel-el-repositorio.md) | **Un solo nivel de instanciación**: el repositorio es la unidad de mantenimiento | `aceptada` (impl. pendiente) | 2026-09-28 |
| [013](./013-componentes-cross-ownership-y-gates.md) | Componentes **cross**: ownership declarado, contrato versionado y gate **G4** | `aceptada` (impl. pendiente) | 2026-09-28 |
| [014](./014-contribucion-externa-y-g4.md) | Contribución externa: `contrib/<change-id>` y la regla del «mismo humano en dos sombreros» | `aceptada` (impl. pendiente) | 2026-09-28 |
| [015](./015-adaptadores-llevan-el-procedimiento-del-rol.md) | Los adaptadores llevan el procedimiento del rol, verificado por contenido | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |
| [016](./016-arranque-en-frio-conversacion-nueva.md) | El arranque en frío se consigue con **conversación nueva**, no con la selección de agente | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |
| [017](./017-el-maintainer-amplia-el-gate-no-lo-vacia.md) | El maintainer puede **ampliar** el gate, no vaciarlo (alcance + check de integridad) | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |
| [018](./018-identidad-del-repositorio-verificada.md) | La identidad del repositorio se declara y se verifica (dos severidades) | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |
| [019](./019-instanciador-extrae-del-propio-arbol.md) | El instanciador extrae del propio árbol (`git archive`) y verifica la instancia | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |
| [020](./020-un-clon-por-aplicacion.md) | **Un clon del harness por aplicación**; el workspace es una carpeta sin versionar | `aceptada` (impl. hecha 2026-10-04) | 2026-10-04 |

> Los ADR 004–010 responden a las decisiones abiertas **A1–A7** de
> [`docs/propuesta-harness-instanciable.md`](../../../docs/propuesta-harness-instanciable.md).
> La columna *Estado* distingue la **decisión** (tomada y cerrada) de su **implementación** (pendiente),
> porque la decisión es lo que desbloquea el trabajo siguiente; la implementación se verifica aparte.

## Por qué estas decisiones existen

Este harness se construyó cometiendo y corrigiendo dos errores reales, y ambos quedaron
registrados porque son fáciles de repetir:

1. **Validar contra la fuente equivocada.** Se comprobaron nombres de modelo contra la
   documentación de las APIs de OpenAI/Anthropic en lugar de contra el catálogo del runtime que
   ejecuta los agentes. Varios nombres "corregidos" rompieron los cinco agentes. → ADR-001.

2. **Confundir catálogo nativo con extendido.** `DeepSeek V4 Flash` no aparece en el catálogo
   nativo de Copilot, y se concluyó que no existía. Lo aporta una extensión de terceros vía
   `languageModelChatProviders`. → ADR-002.

3. **Dejar un vínculo importante en prosa.** La relación entre los 5 roles y las 8 skills
   estaba escrita (cuando lo estaba) en el cuerpo de los prompts, y nada la comprobaba. Tres de
   los ocho vínculos estaban incompletos y el rol `sdd-developer` no citaba ni una skill. → ADR-003.

4. **Versiones repartidas sin coordinación.** El harness tenía **cinco** declaraciones de versión
   independientes (`AGENTS.md`, `harness.config.json`, `models.yaml`, `providers.yaml`,
   `routing.yaml`) y ninguna representaba al conjunto. Nada detectaba que divergieran. Tercera
   ocurrencia del mismo patrón: **un dato crítico en copias que pueden divergir en silencio**. → ADR-004.

5. **Confundir una garantía aparente con un control real.** La protección de rama en GitHub se
   guardó pero **no se aplica** en repositorios privados Free, y ni siquiera un plan de pago la haría
   efectiva frente a un agente que comparte credenciales con el humano. Es la variante del mismo
   patrón aplicada a una garantía en lugar de a un dato: **un check en `SKIP` no es un `PASS`; una
   regla inerte no es una protección**. → ADR-011.

6. **Un check que no puede fallar.** `sync-adapters.sh --check` comparaba la salida del generador
   contra la salida del generador, así que respondía «sincronizados» mientras 5 de los 6 adaptadores
   de Copilot estaban **sin el procedimiento de su rol** (un `sed` frágil ante CRLF). Un check solo es
   real cuando **mira algo distinto de sí mismo**. → ADR-015.

7. **Un protocolo sin mecanismo.** `AGENTS.md` §6 dice «no asumas contexto de sesiones anteriores»,
   pero el harness asumía que **seleccionar un agente** bastaba para conseguir el arranque en frío.
   La prueba de dos escenarios demostró que no: en un chat existente el agente hereda el historial; en
   uno **nuevo** no sabe qué es D-1 y va a buscarlo a disco. → ADR-016.

La lección transversal: **un validador que nunca ha fallado no ha demostrado nada**; **un límite es
real cuando es capacidad ausente, no cuando es una instrucción**; y **un check solo es real cuando mira
algo distinto de sí mismo**. Por eso
`scripts/validate_harness.py` se probó con un modelo inventado (`modelo-que-no-existe-123`) para
confirmar que falla de verdad (código de salida 1) en lugar de dar un falso verde.
