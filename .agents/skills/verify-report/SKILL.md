---
name: verify-report
description: "Produce verify.md con evidencia de trazabilidad, salida del gate y veredicto PASS/FAIL. Use when writing a verification report, documenting acceptance evidence, recording a task as verified, or reporting a root cause for a failed task."
argument-hint: "<feature-slug>"
---

# Verify Report (verify.md)

Produce el artefacto de la fase de verificación. Usada por el rol `sdd-verifier`.

## Cuándo usar

- El Developer terminó una o varias tareas y hay que decidir si pasan.
- Hay que documentar por qué una tarea falla (causa raíz, no síntoma).
- Antes de abrir el PR (el PR debe poder leerse junto con `verify.md`).

## Principios

1. **Evidencia o no cuenta.** Cada afirmación va acompañada de `archivo:línea`, comando o salida.
2. **La salida del gate es literal.** No se resume, no se recorta, no se embellece.
3. **Causa raíz, no síntoma.** "El test `test_email` falla" es síntoma; "la validación acepta
   cadenas sin `@` porque la regex no ancla el final" es causa raíz.
4. **El veredicto es binario con matices explícitos**: `PASS`, `PASS-CON-NOTAS`, `FAIL`.

## Plantilla

```markdown
# Verify — <feature-slug>

- **Verifier**: sdd-verifier (modelo resuelto desde `.harness/models.yaml`)
- **Fecha**: <YYYY-MM-DD>
- **Commits verificados**: `<hash>`..`<hash>`
- **Tareas cubiertas**: NNN, NNN, NNN

## 1. Veredicto

**`PASS` | `PASS-CON-NOTAS` | `FAIL`**

<Una o dos frases con la justificación del veredicto.>

## 2. Trazabilidad de criterios

| AC / Tarea | Criterio | Evidencia | Estado |
| :--- | :--- | :--- | :--- |
| AC-1 / 001 | <criterio> | `src/foo.ts:42`, test `email_rejects_empty` | ✅ |
| AC-2 / 002 | <criterio> | — sin evidencia localizable | ❌ |

## 3. Gate de verificación

```
$ ./init.sh
<salida literal completa>
```

## 4. Alcance

```
$ git diff --stat <base>..<head>
<salida literal>
```

- ¿Cada commit toca una sola tarea? sí | no (`<hash>` toca NNN y NNN → R2)
- ¿Algún archivo fuera de la lista `## Archivos` de su tarea? no | sí (`<ruta>`)

## 5. Regresión

- Tests eliminados o deshabilitados: ninguno | `<archivo:línea>` (R7)
- Tests existentes que ahora fallan: ninguno | `<nombre>`

## 6. Reglas de oro (AGENTS.md §1)

| Regla | Estado | Evidencia |
| :--- | :--- | :--- |
| R1 artefactos antes del código | CUMPLIDA | `scope.md`, `design.md`, `tasks/` previos |
| R2 una tarea = un commit | CUMPLIDA | 1 commit por tarea |
| R3 sin auto-merge | CUMPLIDA | PR abierto, sin merge |
| R4 harness intacto | CUMPLIDA | diff sin `.harness/` ni `AGENTS.md` |
| R5 criterios verificables | CUMPLIDA | todos los AC con comando |
| R6 gate no saltado | CUMPLIDA | sin `--no-verify` |
| R7 tests no debilitados | CUMPLIDA | sin cambios en `tests/` a la baja |
| R8 alcance sin crecer | CUMPLIDA | sin archivos fuera de alcance |
| R9 sin secretos | CUMPLIDA | check `secrets` en verde |
| R10 artefactos en disco | CUMPLIDA | este archivo escrito |

## 7. Definition of Done (AGENTS.md §5)

- [ ] Criterio de aceptación demostrado
- [ ] `./init.sh` en verde
- [ ] Un commit con `sdd: task NNN - ...`
- [ ] Sin archivos fuera de alcance
- [ ] Harness sin modificar
- [ ] Sin TODOs huérfanos ni código comentado
- [ ] Tests fallan antes / pasan después

## 8. Seguridad

<Sección del `sdd-security-reviewer`, o `N/A — sin superficie de ataque en el diff`.>

## 9. Deuda registrada

| # | Deuda | Dónde | Cuándo se paga |
| :--- | :--- | :--- | :--- |
| D1 | <descripción> | `archivo:línea` | <tarea/feature> |

## 10. Bloqueos y escalado

<Ninguno, o el `BLOQUEO:` con su evidencia.>

## 11. Gate humano

- **G3 (merge)**: **pendiente** de revisor humano.
- Este PR **no** ha sido mergeado por ningún agente (R3).
```

## Reglas del Verifier

- **No edita código.** Su único artefacto escribible es `verify.md`.
- **No verifica su propia implementación.** Developer y Verifier nunca coinciden.
- Un hallazgo de seguridad `crítica`/`alta` fuerza `FAIL`.
- Un check crítico en `SKIP` por falta de herramienta → `PASS-CON-NOTAS` **como máximo**,
  nunca `PASS`.

## Ver también

- Rol [sdd-verifier](../../agents/sdd-verifier.md)
- Skill `gate-runner`, `security-review`
