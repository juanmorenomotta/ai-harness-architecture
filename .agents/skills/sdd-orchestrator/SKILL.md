---
name: sdd-orchestrator
description: "Orquesta el flujo SDD completo delegando a subagentes en frío. Use when starting a feature, running the SDD cycle (init/design/implement/verify), deciding which role goes next, or checking gate status between phases."
argument-hint: "<feature-slug> [fase]"
---

# SDD Orchestrator

Pegamento del harness. Lee la ley del repo, consulta la configuración de modelos y delega
cada fase a un subagente con **contexto aislado**. El orquestador no implementa: coordina.

## Cuándo usar

- Arrancar una feature nueva (`.spec/` no existe).
- Retomar una feature a medias (¿en qué fase quedó?).
- Decidir qué rol va después.
- Comprobar si un gate humano (G1/G2/G3) está aprobado.

## Procedimiento

1. **Lee `AGENTS.md` completo.** Es la precondición de toda sesión.
2. **Lee `.harness/models.yaml`.** Es el único punto de verdad de modelos.
   El orquestador resuelve `role → model` aquí y lo pasa como parámetro de invocación.
   **Nunca** copies nombres de modelo a los prompts de rol.
3. **Determina la fase real leyendo disco**, no la conversación:

   | Existe en `.spec/<slug>/` | Fase actual | Siguiente acción |
   | :--- | :--- | :--- |
   | nada | — | invocar `sdd-init` |
   | `scope.md` sin `Aprobado por:` | G1 pendiente | **detener** y pedir aprobación humana |
   | `scope.md` aprobado | init | invocar `sdd-tech-lead` |
   | `design.md` + `tasks/` sin aprobar | G2 pendiente | **detener** y pedir aprobación humana |
   | `tasks/` aprobado, tareas sin commit | implement | invocar `sdd-developer` **una tarea** |
   | todas las tareas commiteadas | verify | invocar `sdd-verifier` |
   | `verify.md` = FAIL | implement | devolver la tarea fallida al Developer |
   | `verify.md` = PASS | G3 pendiente | abrir PR y **detener** (nunca auto-merge, R3) |

4. **Delega con arranque en frío.** Cada subagente recibe **solo**:
   - La instrucción de leer `AGENTS.md`.
   - La ruta de **sus** artefactos de entrada (nada más).
   - El modelo resuelto desde `models.yaml`.
   No le pases resúmenes de conversación ni el contenido de otros artefactos.
5. **Verifica la salida antes de avanzar**: ¿existe el artefacto en disco? ¿el resumen tiene ≤ 10
   líneas? ¿respetó su lista de `tools`? Si no, **no avances de fase**.
6. **Respeta los gates.** El orquestador nunca aprueba un gate propio (AGENTS.md §7).
7. **Un paso por turno.** Não encadenes init→design→implement en una sola invocación:
   cada fase termina con su artefacto escrito y su resumen leído.

## Secuencia de delegación (Nivel 1)

```
humano: prompt de feature
  └─ sdd-init        → scope.md                    ── G1 (humano) ──┐
       └─ sdd-tech-lead → design.md + tasks/       ── G2 (humano) ──┤
            └─ sdd-developer (× N tareas, 1 commit cada una)         │
                 └─ sdd-verifier → verify.md                        │
                      ├─ (opcional, en paralelo) sdd-security-reviewer
                      └─ veredicto ────────────────── G3 (humano) ──┘
```

## Reglas del orquestador

- **Nunca** implementa código ni edita artefactos SDD.
- **Nunca** salta un gate humano.
- **Nunca** permite que el Developer tome más de una tarea.
- **Nunca** hereda contexto entre fases: cada subagente arranca leyendo disco.
- Si dos artefactos se contradicen (`scope.md` vs `design.md`) → **bloquea** y escala.
- Si un subagente devuelve `BLOQUEO:` → propaga el bloqueo al humano con su evidencia.

## Ver también

- [Definición de roles](../../agents/sdd-developer.md)
- [Gate de verificación](../../../init.sh)
- [Política de permisos](../..//policies/permissions.yaml)
- Skill `gate-runner` para interpretar el resultado del gate.
- Skill `model-switching` para cambiar el modelo de un rol.
