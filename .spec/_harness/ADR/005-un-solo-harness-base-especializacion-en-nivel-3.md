# ADR-005 — Un solo harness base; la especialización por dominio vive en el nivel 3

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A2** de `docs/propuesta-harness-instanciable.md`
- **Reemplaza**: la mitigación «herencia explícita» propuesta en §5 **D2** del documento de propuesta
- **Tareas afectadas**: `docs/propuesta-harness-instanciable.md` §5 D2 (a corregir)

## Contexto

La decisión **D2** partía de que existirían varios harness especializados por tipo de componente
(backend, frontend, mobile) y proponía un mecanismo de **herencia** desde un harness base, para
evitar que cada dominio derivara en un fork incompatible.

Al clasificar las diferencias reales entre dominios por nivel, el análisis mostró que **casi todas
viven en el nivel 3 (componente)**, no en el nivel 1:

| Diferencia entre backend / frontend / mobile | Nivel donde vive |
| :--- | :--- |
| Comandos del gate (`mvn verify` · `npm test` · `flutter test`) | **Nivel 3** — `template.yaml` |
| Rutas escribibles (`src/main/java` · `src/components` · `lib/`) | **Nivel 3** — `extensions` del template |
| Conocimiento idiomático (Spring · React · Flutter) | **Nivel 3** — `agent_profile.md` |
| Template a clonar | **Nivel 3** — `stack.md` |
| **Rol, fases SDD, gates G1–G3, R1–R10, arranque en frío** | **Igual en los tres** |

**Los roles no cambian.** `sdd-init` convierte una petición vaga en criterios verificables igual si el
destino es Java, PHP o Flutter: su prompt no menciona tecnología, y eso está verificado por comando.

El caso más distinto es **mobile** (firma de artefactos, revisión de tiendas, matriz de dispositivos,
verificación con emulador). Aun así, nada de eso cambia los roles ni las fases: son **checks del gate
y una skill extra**, es decir, aditivo.

Además, el proyecto tiene **cero aplicaciones**: el flujo SDD nunca ha pasado de la fase init. Construir
un mecanismo de herencia ahora obligaría a diseñarlo sobre diferencias **no medidas**.

## Decisión

**No existe mecanismo de herencia ni hay varios harness. Hay un solo harness base, y toda la
especialización por dominio se traslada al nivel 3 (el componente), vía `template.yaml`.**

La especialización se expresa en tres sitios, todos del componente:

1. **`commands`** — el gate de cada componente declara sus propios comandos (`lint`, `tests`, `gate`).
2. **`extensions`** — las rutas donde el agente puede escribir, declaradas por el componente.
3. **`agent_profile.md`** — el conocimiento idiomático de la tecnología (convenciones, anti-patrones,
   recetas de test), versionado junto al código que describe.

En consecuencia, `init.sh` deja de tener una rama por lenguaje y pasa a **leer** lo que cada componente
declara. La diferencia entre dominios es **aditiva** (skills y checks extra), nunca estructural.

**Regla de promoción**: si un dominio necesita algo que el base no puede expresar, la discusión es
*«¿debe el base ganar esa opción?»*, no *«creemos otro harness»*. Si la respuesta fuera «creemos otro
harness», eso indicaría que el base es la abstracción equivocada, y el caso se lleva a un ADR nuevo.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Perfiles de dominio que heredan del base** (propuesta original de D2) | Cambio en el base se propaga; delta acotado y visible | Obliga a **construir un mecanismo de herencia** en un harness que aún no funciona una vez. Y la mayor parte del delta no está en el nivel 1, así que el mecanismo resolvería poco | Se diseña sobre diferencias no medidas. Es abstracción anticipada |
| **B. Un harness independiente por dominio** | Aislamiento total; cada uno evoluciona libre | Divergencia garantizada: en seis meses, cinco harness incompatibles y ninguna lección compartida. Reproduce §2 del documento | Es el problema que D1/D2 querían evitar |
| **C. Monorepo con carpetas por dominio** | Un solo repo; historia compartida | Sigue requiriendo un mecanismo que decida qué se aplica a cada dominio, sin evidencia que lo justifique | Mismo problema que A |
| **D. Un solo base; especialización en el nivel 3** | Cero mecanismo nuevo; coherente con dónde está la diferencia real; el base se mantiene único y probado | Antes de que exista el sistema de templates del nivel 3, **no hay especialización posible** | — (la elegida) |

## Consecuencias

**Positivas**
- **No hay que construir ningún mecanismo de herencia**: se elimina trabajo y una fuente de complejidad.
- El base permanece **único**, con un solo ciclo de verificación y una sola versión (ADR-004).
- Refuerza la arquitectura ya decidida: hace del **nivel 3 el lugar load-bearing** de la
  especialización, que es donde el análisis demostró que corresponde.
- Un cambio de tecnología en un componente (de React a Vue) **no toca el harness**.

**Negativas / deuda asumida**
- La especialización depende por completo de que el **sistema de templates del nivel 3** exista. Hasta
  entonces, todos los componentes usan el base sin matices. Es deuda conocida y aceptada: el nivel 3
  es el paso 6 del orden de implementación.
- El `template.yaml` pasa a ser un artefacto crítico: si declara mal sus comandos, el gate del
  componente verificará lo que no debe. Mitigación: suite de conformidad de templates.

**Neutrales**
- Los perfiles de dominio, si algún día existen, serían **conjuntos de plantillas del nivel 3**, no
  harnesses.
- `AGENTS.md` no cambia por esta decisión.

## Cómo revertir esta decisión

Si con dos o tres proyectos reales se demuestra que el delta de un dominio **sí** vive en el nivel 1,
se escribe un ADR nuevo que introduce perfiles —esta vez con evidencia— y este ADR pasa a
`reemplazada por ADR-NNN`. Revertir es barato porque no se habrá construido ningún mecanismo.

## Cómo se verificará

1. `docs/propuesta-harness-instanciable.md` §5 D2 actualizado para reflejar esta decisión (hoy describe
   la herencia como mitigación).
2. Cuando exista el materializador del nivel 3: un componente con `template.yaml` propio pasa su gate
   **sin que se haya tocado nada del harness**. Ese es el criterio de éxito de esta decisión.
3. `python scripts/validate_harness.py` sigue con **un solo** juego de artefactos de harness.

## Referencias

- `docs/propuesta-harness-instanciable.md` §3 (tres niveles), §5 D2, §7, §11 A2
- `docs/desacoplamiento-arquitectura-software.md` — diseño del nivel 3 (`stack.md`, `template.yaml`)
- `AGENTS.md` §4 (regla de capas)
