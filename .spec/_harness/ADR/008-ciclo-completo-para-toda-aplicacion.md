# ADR-008 — Ciclo SDD completo para todo componente de aplicación, sin umbral de tamaño

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **PENDIENTE**
- **Decisor**: Juan Moreno (Product Owner)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A5** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: `docs/propuesta-harness-instanciable.md` §5 D3 (precisa el umbral)

## Contexto

La decisión **D3** estableció dos modos: **ciclo completo** para componentes de aplicación y **modo
ligero** para componentes de infraestructura. Quedaba abierto si todo componente de aplicación merece
el ciclo completo o si conviene un umbral por tamaño.

El contexto duro: un proyecto multi-repo con N componentes multiplica los ciclos (4 componentes × 5
fases = 20 ciclos), y el coste de los gates humanos (G1, G2, G3) se paga por componente.

## Decisión

**Todo componente de aplicación pasa por el ciclo SDD completo, con independencia de su tamaño. El
modo ligero se reserva para lo que no es aplicación.**

| Tipo de componente | Modo | Criterio de asignación |
| :--- | :--- | :--- |
| **Aplicación** (backend, frontend, móvil, servicio con dominio) | **Ciclo completo** | Tiene comportamiento de dominio y criterios de aceptación de usuario |
| **Infraestructura** (base de datos, IaC, observabilidad, CI) | **Modo ligero** | No tiene comportamiento de dominio propio |
| **Harness** (herramientas del propio framework) | **Modo ligero** | Sirve al método, no al producto (ver ADR-007) |

La frontera **no es el tamaño** sino la **naturaleza**: un módulo de autenticación de un endpoint y un
módulo de autenticación de treinta endpoints reciben el mismo tratamiento, porque ambos tienen
comportamiento de dominio.

### Por qué sin umbral

1. **La especificación es lo que produce el valor, no la ceremonia.** Al escribir los criterios de
   aceptación es donde se descubren los huecos del alcance. Omitirlos en componentes pequeños es
   omitir precisamente el paso que más aporta.
2. **Un componente "pequeño" lo es hoy, no mañana.** El umbral exigiría re-clasificar componentes al
   crecer, y un componente re-clasificado arrastra artefactos SDD ausentes justo cuando más se
   necesitan.
3. **El tamaño no es una magnitud estable ni verificable.** Un umbral («menos de X archivos», «menos
   de Y puntos de historia») es ambiguo, y **R5** prohíbe criterios de aceptación no verificables. Un
   umbral de tamaño sería exactamente eso.
4. **El coste ya está controlado por otra vía**: el número de componentes es una decisión de diseño
   (lo acota el nivel 3), no algo que haya que compensar degradando el proceso de cada uno.

### Modo ligero: qué se ajusta y qué no

| Aspecto | Aplicación | Infraestructura / harness (ligero) |
| :--- | :--- | :--- |
| Fases SDD | `init → design → tasks → implement → verify` | `init → design → implement` |
| `design.md` | Completo (interfaces, alternativas, riesgos) | Mínimo (qué, por qué, cómo se verifica) |
| `tasks/` | Una tarea por archivo, un commit cada una | Sin descomposición formal |
| Gates humanos | G1 + G2 + G3 | G1 (alcance) + revisión del diff |
| Verificación | `verify.md` con trazabilidad AC↔código | Gate del componente + revisión |
| Adaptadores de agente | Todos | Subconjunto |

> El modo ligero **no relaja las garantías**: aplican **R1** (nada de código sin spec), **R6**
> (`init.sh` como único gate), **R7** (no se debilitan tests) y **R9** (sin secretos). Lo que se ajusta
> es la **ceremonia**, no la ley.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Umbral por tamaño** (componentes pequeños en modo ligero) | Menos ciclos y menos gates | El umbral es ambiguo y no verificable (viola **R5**); omite la especificación justo donde más se descubre; exige re-clasificar al crecer | Introduce un criterio no verificable en la ley |
| **B. Ciclo completo solo si hay criterios de usuario** | Distingue con criterio funcional, no de tamaño | Es subjetivo y difícil de arbitrar en la práctica; genera discusión en cada componente | Ambigüedad operativa |
| **C. Modo ligero para todo componente pequeño, sin umbral definido** | Flexible | Ausencia de regla = cada quien decide; precisamente lo que el harness quiere evitar | Deja la decisión al criterio del momento |
| **D. Ciclo completo para toda aplicación, criterio por NATURALEZA** | Criterio claro y verificable (¿tiene dominio?); sin umbral ambiguo; el coste se controla acotando el número de componentes | Puede resultar pesado en componentes genuinamente triviales | — (la elegida) |

## Consecuencias

**Positivas**
- El criterio es **verificable y estable**: «¿tiene comportamiento de dominio?» es una pregunta binaria,
  no una estimación de tamaño (coherente con R5).
- Ningún componente queda sin especificación por ser pequeño, que es donde el descubrimiento de
  alcance rinde más.
- Refuerza **D3** con una frontera operativa: cierra la ambigüedad que tenía.

**Negativas / deuda asumida**
- **Coste aceptado**: N componentes de aplicación × 5 fases y 3 gates. La mitigación no es degradar el
  proceso, sino **acotar el número de componentes** al diseñar el nivel 3.
- La asignación app/infra exige un juicio al declarar cada componente en `stack.md`. Mitigación: el
  campo `kind` de `stack.md` lo hace explícito y auditable, y cambiarlo requiere decisión, no omisión.

**Neutrales**
- No cambia el conjunto de gates ni la ley.
- `validator-runner` y el materializador del nivel 3 son infraestructura/harness → modo ligero.

## Cómo revertir esta decisión

Introducir un umbral en la tabla de D3 y documentarlo en `stack.md`. Barato de ejecutar, y reintroduce
el problema de verificabilidad de R5, razón por la que se descartó.

## Cómo se verificará

1. Un componente de aplicación declarado en `stack.md` produce los cuatro artefactos
   (`scope.md`, `design.md`, `tasks/NNN-*.md`, `verify.md`) y pasa G1, G2 y G3.
2. Un componente de infraestructura **no** requiere `tasks/` ni `verify.md` y pasa su gate.
3. El campo `kind` de cada componente en `stack.md` clasifica sin ambigüedad app vs. infra.

## Referencias

- `docs/propuesta-harness-instanciable.md` §5 D3, §11 A5
- `AGENTS.md` §1 R1/R6/R7/R9, §5 (Definition of Done), §7 (gates G1–G3)
- ADR-007 de este directorio (el modo ligero que aplica al harness)
