---
name: task-decomposition
description: "Descompone un diseño en tareas atómicas, una por archivo, con archivos permitidos y criterio verificable. Use when writing tasks/NNN-*.md, splitting a design into single-commit units, or refactoring a task that is too large."
argument-hint: "<feature-slug>"
---

# Task Decomposition (tasks/NNN-*.md)

Convierte `design.md` en tareas que un Developer puede completar con **un commit**.
Usada por el rol `sdd-tech-lead`.

## Cuándo usar

- Ya existe `design.md` aprobado (G2) y hay que producir el plan.
- Una tarea resultó demasiado grande (estimación `L`) y hay que partirla.
- El Verifier devolvió `FAIL` y hay que reformular el criterio de una tarea.

## La prueba de atomicidad

Una tarea es atómica si cumple las **cuatro** condiciones:

1. **Un objetivo** — se puede describir en una frase sin la conjunción "y".
2. **Un commit** — el diff completo es coherente por sí solo (`git bisect` no se rompe).
3. **Lista cerrada de archivos** — se enumeran las rutas exactas que tocará.
4. **Criterio verificable** — hay un comando que dice sí o no (R5).

Si falla cualquiera, la tarea hay que partirla o reescribirla.

## Plantilla de tarea

```markdown
# Tarea NNN — <título en imperativo>

- **Feature**: `<feature-slug>`
- **Criterios de scope**: AC-N, AC-M
- **Depende de**: NNN-NNN | ninguna
- **Estimación**: S | M        <!-- si es L, partirla -->
- **Rama**: `task/<feature-slug>/NNN`

## Objetivo

<Una frase. Un solo resultado.>

## Archivos

<!-- Lista CERRADA. El diff debe coincidir exactamente. -->

- `src/foo/bar.ts` (modificar)
- `tests/foo/bar.test.ts` (crear)

## Criterio de aceptación

- [ ] **AC-N.1**: <condición observable>
      Verificación: `<comando exacto>`
- [ ] **AC-N.2**: …

## Evidencia para el Verifier

<Qué debe poder comprobar: nombre del test, salida esperada del comando, archivo:línea.>

## Notas de implementación

<Opcional. Pistas del diseño: firma de la función, caso borde conocido, sin decisiones abiertas.>

## Fuera de alcance de esta tarea

<Lo que NO se hace aquí, para evitar que el Developer se expanda.>
```

## Estrategia de descomposición

1. **Cortes verticales primero.** Una tarea debe atravesar el sistema (tipo → lógica → test),
   no ser una "tarea de tipos" seguida de "tarea de lógica".
2. **Ordena por dependencia real**, no por preferencia. La tarea NNN no puede requerir NNN+1.
3. **Empieza por el camino crítico**: la tarea que, si no funciona, invalida el diseño.
4. **Deja la integración y el pulido al final**, pero **no** como tarea única de "integración":
   eso no es atómico.
5. **Un test por criterio observable**, dentro de la tarea que lo implementa. No agrupes todos
   los tests en una tarea final.
6. **Nombra las tareas con verbo en imperativo**: `añadir-validacion-email`,
   no `validacion-email`.

## Anti-patrones

| Anti-patrón | Por qué falla | Arreglo |
| :--- | :--- | :--- |
| "Refactor general" | Sin criterio verificable, sin límite de archivos | Dividir por archivo/módulo con criterio medible |
| Tarea de `L` | Imposible de revisar, commits gigantes | Partir en dos o tres |
| Tarea "y además" | Rompe el objetivo único | Extraer la segunda parte a su propia tarea |
| Criterio sin comando | El Verifier no puede decidir | Añadir el comando o el resultado binario (R5) |
| Archivos abiertos ("y lo que surja") | El alcance se expande, R2 se rompe | Lista cerrada; si hace falta otra ruta, se reformula la tarea |
| Tarea que toca el harness | Viola R4 | Va en PR separado, revisado por humano |

## Verificación del plan antes de entregarlo

```
[ ] ¿Cada tarea tiene exactamente un objetivo?
[ ] ¿Cada tarea tiene lista cerrada de archivos?
[ ] ¿Cada criterio tiene un comando de verificación?
[ ] ¿Ninguna tarea estima L?
[ ] ¿Las dependencias forman un DAG sin ciclos?
[ ] ¿Ninguna tarea toca AGENTS.md, .harness/, .agents/ o CI?
[ ] ¿El conjunto de tareas cubre TODOS los AC de scope.md?
[ ] ¿Ninguna tarea añade alcance fuera del scope (R8)?
```

## Ver también

- Rol [sdd-tech-lead](../../agents/sdd-tech-lead.md)
- Skill `adr-record` para las decisiones que surjan al descomponer
- Skill `gate-runner` para el comando que el Developer usará
