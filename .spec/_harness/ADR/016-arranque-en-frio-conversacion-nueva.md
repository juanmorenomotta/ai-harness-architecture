# ADR-016 — El arranque en frío se consigue con conversación nueva, no con la selección de agente

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (documental: guía y protocolo)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Tareas afectadas**: `docs/inicio-harness-sdd.md` (guía de fases), `AGENTS.md` §6 (mecanismo, PR humana)

## Contexto

`AGENTS.md` §6 establece el protocolo de arranque en frío:

> **Regla de arranque en frío: no asumas contexto de sesiones anteriores.** Si un dato no está en
> disco (en `AGENTS.md`, `.spec/` o `.harness/`), **no existe**.

Y el §0 añade:

> Regla de arranque en frío: **no asumas contexto de sesiones anteriores**.

Este protocolo es **load-bearing** para el harness, y en particular para la independencia del Verifier:
`sdd-verifier` verifica «contra el criterio escrito, no contra lo que el Developer dijo que hizo». Si
hereda la conversación del Developer, esa independencia es una convención, no una garantía.

### El supuesto no verificado

El harness asumía implícitamente que **invocar a un subagente produce arranque en frío**. Nunca se
había comprobado. Se probó el 2026-10-04 con `harness-maintainer`, en dos condiciones:

| Escenario | Pregunta | Respuesta observada |
| :--- | :--- | :--- |
| **Chat existente**, agente recién seleccionado | «¿Tu recomendación es D-1 opción B, clonar por tag?» | Respondió **con el contenido de la conversación** («mi recomendación fue precipitada»): sabía qué era D-1 y cuál era la recomendación previa |
| **Chat nuevo**, mismo agente seleccionado | «D-1, opción B, clonar tag?» | **«Voy a buscar el contexto de "D-1" y las opciones en disco antes de opinar»** — no sabía qué era |

**Conclusión**: la **selección de agente no produce aislamiento**. Lo produce **abrir una conversación
nueva**. En un chat existente, el agente hereda el historial completo aunque esté correctamente
seleccionado.

### Dato secundario: el arreglo de ADR-015 surte efecto

En el chat nuevo, el agente cargó su procedimiento (`Precondición`, `Procedimiento`, `Límites`) y siguió
el paso 3 de su precondición: *«Comprueba el origen de la petición»* y buscar en disco. Antes del
2026-10-04 el adaptador no llevaba esa sección, así que **ninguna prueba anterior habría sido
concluyente**: el agente no tenía instrucciones que seguir.

## Decisión

**El arranque en frío se obtiene abriendo una conversación nueva por fase. Se documenta el mecanismo,
porque hoy la ley dice QUÉ debe pasar pero no CÓMO se consigue.**

1. **Regla operativa**: cada fase del ciclo SDD se lanza en una **conversación nueva**, con el agente
   ya seleccionado. No se cambia de agente dentro de la misma conversación.

   | Fase | Conversación | Agente |
   | :--- | :--- | :--- |
   | init | **nueva** | `sdd-init` |
   | design | **nueva** | `sdd-tech-lead` |
   | implement | **nueva por tarea** | `sdd-developer` |
   | verify | **nueva** | `sdd-verifier` |

2. **La documentación refleja el mecanismo**: `docs/inicio-harness-sdd.md` §7 indica, en cada fase, que
   se abra una conversación nueva. La obligación deja de ser un supuesto tácito.

3. **`AGENTS.md` §6 precisa el mecanismo** (→ **PR humana**, R4): la sección describe el protocolo pero
   no cómo se consigue. Añadir esa frase es un cambio de ley y requiere bump de versión (ADR-004).

4. **Se registra la verificación**: la prueba de dos escenarios queda como evidencia de que el
   mecanismo es el correcto.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Confiar en la selección de agente** (el supuesto anterior) | Cero fricción; «seleccionar el agente» parecía suficiente | **Refutado por la prueba**: en chat existente el agente hereda el historial | Es el supuesto que la evidencia desmiente |
| **B. Un chat por fase** | Aislamiento real y verificado; el agente lee de disco o bloquea | Más conversaciones; el humano debe recordar abrir una nueva | — (la elegida) |
| **C. Delegar a un subagente desde el orquestador** | Automatiza el aislamiento sin intervención humana | Requiere que el orquestador no esté en el mismo chat (mismo problema, un nivel arriba); y no está claro que la plataforma aísle el subagente | No resuelve la causa y añade un nivel de indirección |
| **D. Confiar en la instrucción, sin verificar** | Cero trabajo | Es el estado anterior: una regla sin mecanismo ni verificación | Contradice la lección transversal del repositorio |

## Consecuencias

**Positivas**
- El arranque en frío pasa de **supuesto** a **mecanismo verificado**, con evidencia de dos escenarios.
- La independencia del Verifier deja de depender de la buena voluntad: si arranca en conversación nueva,
  **no tiene** el contexto del Developer.
- El protocolo §6 se vuelve ejecutable: la guía dice cómo.

**Negativas / deuda asumida**
- **El aislamiento depende de un acto humano**: abrir la conversación. Nada lo impone. Es un límite de
  proceso, no de máquina — igual que R3 antes de separar identidades (ADR-011).
- Más fricción operativa: una conversación por fase y por tarea.
- Si alguien continúa en la misma conversación, **el harness no lo detecta**. Se acepta: detectarlo
  requeriría inspeccionar la sesión, fuera del alcance del gate.

**Neutrales**
- No cambia ningún artefacto del harness ni el gate.
- No afecta a los adaptadores.

## Cómo revertir esta decisión

Volver a asumir que la selección de agente aísla. Se recupera la comodidad de una sola conversación y se
pierde la garantía de que cada fase lee de disco.

## Cómo se verificó

1. **Escenario 1 (chat existente)**: el agente respondió con contenido de la conversación → **no hay
   aislamiento** por selección.
2. **Escenario 2 (chat nuevo)**: el agente declaró no saber qué era D-1 y fue a buscar en disco →
   **hay aislamiento** en conversación nueva.
3. Ambos escenarios con el **mismo agente seleccionado** (`harness-maintainer`) y adaptador completo
   (ADR-015), de modo que la diferencia observada es la conversación, no el rol.

## Lección transversal

**Séptima ocurrencia del patrón del repositorio**, y la segunda en su forma de «garantía aparente»
(tras ADR-011):

> **Un protocolo sin mecanismo es una convención.** «No asumas contexto» es una instrucción; abrir una
> conversación nueva es el mecanismo que la hace real.

Refuerza la lección de ADR-007 y ADR-011: *un límite es real cuando es capacidad ausente, no cuando es
una instrucción*. Aquí la capacidad ausente es «no tener el historial», y se consigue con una
conversación nueva.

## Referencias

- `AGENTS.md` §0 y §6 (protocolo de arranque en frío), §8 (independencia del Verifier)
- ADR-015 (el adaptador llevaba la ley pero no el procedimiento: sin él, la prueba no era concluyente)
- ADR-011 (garantía aparente: la protección de rama inerte)
- `docs/inicio-harness-sdd.md` §7 (guía de fases)
