# ADR-007 — Rol `harness-maintainer`; `scripts/` no es escribible por el Developer

- **Fecha**: 2026-09-27
- **Estado**: `aceptada` · **Implementación**: **HECHA 2026-10-04** (ver "Implementación" al final)
- **Decisor**: Juan Moreno (responsable del harness)
- **Co-firma**: **Juan Moreno, Tech Lead humano** (los roles pueden coincidir en la misma persona; lo
  que la ley prohíbe es que un **agente** apruebe un cambio de governance)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **A4** de `docs/propuesta-harness-instanciable.md`
- **Tareas afectadas**: `.agents/agents/harness-maintainer.md` (nuevo), `.agents/policies/permissions.yaml`, `.harness/models.yaml`, adaptadores

## Contexto

Dos features necesitan escribir herramientas del harness, y **hoy ningún rol puede**:

| Feature | Necesita escribir |
| :--- | :--- |
| `validator-runner` | `scripts/run_all.py` |
| Materializador de stack (nivel 3) | `scripts/resolve-stack.py`, `scripts/materialize-stack.sh` |

`sdd-developer` tiene `writable_paths: [src/**, tests/**, lib/**, app/**]`. `scripts/**` no está en la
lista de **ningún** rol, y la política es **deny-first**: lo que no está permitido, está prohibido.

### El conflicto de interés estructural

Existe una regla general que resuelve el caso y explica por qué la solución obvia es equivocada:

> **El Developer no puede escribir nada que el Verifier use como evidencia de su trabajo.**

Es la misma lógica que **R7** (*prohibido debilitar tests*). `scripts/` contiene las herramientas con
las que el Verifier juzga: `validate_harness.py`, `harness_yaml.py`, `diagnose_harness.py` y el
`init.sh` que los orquesta. Si el Developer pudiera editarlas, podría hacer que su propio juez lo
declare inocente.

**Abrir `scripts/**` es por tanto un error de governance**, aunque sea la solución aparentemente obvia.

## Decisión

**Se crea un rol nuevo, `harness-maintainer`, con permiso de escritura sobre el harness. `scripts/**`
sigue cerrado para todos los demás roles.**

```yaml
# .agents/policies/permissions.yaml
harness-maintainer:
  allow:
    - read
    - edit
    - search
    - execute
    - todo
  deny:
    - web
    - agent
  writable_paths:
    - "scripts/**"
    - ".harness/**"
    - ".agents/**"
  protected_paths:
    - "AGENTS.md"            # la ley sigue siendo solo humana (§9)
    - ".github/workflows/**"  # CI sigue siendo solo humana
```

### Límites duros del rol

1. **No puede editar `AGENTS.md`.** La ley exige bump de versión y aprobación humana explícita (§9).
2. **No puede editar `.github/workflows/**`.** CI sigue fuera del alcance de todo agente.
3. **Toda su salida va por PR con revisión humana.** No aprueba su propio gate (R4 + §7).
4. **Nunca se invoca en el contexto de una tarea de feature fallida.** Este es el límite que preserva
   R4: si el Developer falla el gate, el camino es arreglar el código, **jamás** invocar a
   `harness-maintainer` para ajustar el validador. El rol opera exclusivamente sobre PRs de harness.
5. **Su tarea no es una tarea SDD.** Es una chore de harness, sin `tasks/NNN-*.md` ni ciclo SDD completo
   (coherente con ADR-008: el ciclo completo es para componentes de aplicación).

### Modo ligero de operación

Igual que los componentes de infraestructura, el trabajo del harness usa el **modo ligero**:

| Aspecto | Aplicación | `harness-maintainer` |
| :--- | :--- | :--- |
| Fases | `init → design → tasks → implement → verify` | `init → design → implement` |
| `tasks/` | Una tarea por archivo | Sin descomposición formal |
| Verificación | `verify.md` con trazabilidad | Gate + revisión humana del diff |
| Gates humanos | G1 + G2 + G3 | **Revisión humana obligatoria de la PR** |

> El modo ligero **no** relaja R1, R6, R7 ni R9: solo ajusta la ceremonia.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Abrir `scripts/**` al Developer con lista negra** | Sin rol nuevo; menos ceremonia | Una **deny-list envejece mal**: cada script nuevo del harness queda escribible por olvido. Y cambia el modelo de permisos de allowlist a deny-list para un caso puntual | Contradice el modelo **deny-first** que ya declara `permissions.yaml` |
| **B. PR autorada por un humano** | Cero cambio de governance; máximo control | Ata la evolución del harness al tiempo disponible del humano. Con dos features esperando, es un cuello de botella real | No escala, y el harness necesita evolucionar |
| **C. Un rol nuevo `harness-maintainer`** | Separa de verdad quién escribe el harness de quién implementa la aplicación; mantiene deny-first; el conflicto de interés queda cerrado por diseño | Un rol más que mantener; exige disciplina en el límite 4 | — (la elegida) |
| **D. Ampliar `writable_paths` del Tech Lead** | Sin rol nuevo | El Tech Lead escribe diseño, no herramientas; mezcla responsabilidades | Confunde la separación de capas |

## Consecuencias

**Positivas**
- El conflicto de interés **desaparece por diseño**: quien escribe el harness no es quien implementa
  la aplicación, ni quien la verifica.
- Desbloquea **dos features** a la vez (`validator-runner` y el materializador del nivel 3).
- Mantiene el modelo **deny-first** sin excepciones ni listas negras.
- `scripts/` sigue siendo superficie confiable para el Verifier.

**Negativas / deuda asumida**
- Un rol más que mantener: prompt, política, entrada en `models.yaml` y adaptadores.
- **Riesgo real de abuso del límite 4**: nada impide técnicamente invocar `harness-maintainer` tras un
  gate fallido. Mitigación: el cargo `harness-maintainer` en la PR debe declarar que **no** responde a
  una tarea de feature, y la revisión humana lo verifica. Es un control de proceso, no de máquina.
- `harness-maintainer` puede editar `.agents/**`, lo que incluye su propia política. Mitigación: el
  cambio de su política requiere PR con revisión humana, igual que cualquier otro cambio de governance.

**Neutrales**
- No afecta a los cinco roles existentes: su lista de permisos no cambia.
- Requiere re-ejecutar `sync-adapters.sh` para generar el adaptador del rol nuevo.

## Cómo revertir esta decisión

Retirar el rol (prompt, política y entrada en `models.yaml`) y volver a la alternativa B: PRs autoradas
por humanos para el harness. Los artefactos que haya producido quedan intactos.

## Cómo se verificará

1. `python scripts/validate_harness.py` → coherente, con `harness-maintainer` en `EXPECTED_ROLES`
   (requiere actualizar la constante, que hoy fija los cinco roles).
2. `bash scripts/sync-adapters.sh` genera `.github/agents/harness-maintainer.agent.md` con modelo
   asignado y **sin** mencionar el modelo en el prompt (regla de capas).
3. **Prueba negativa**: confirmar que `sdd-developer` **no** puede escribir `scripts/**` (su política
   sigue sin esa ruta).
4. `bash init.sh` → PASS.

## Referencias

- `docs/propuesta-harness-instanciable.md` §11 A4, §13 Anexo B
- `AGENTS.md` §1 R4 (no modificar el harness para hacer pasar una tarea), R7, §7 (gates)
- `.agents/policies/permissions.yaml` (modelo deny-first), `.agents/agents/sdd-developer.md`
- ADR-008 de este directorio (modo ligero, que este rol reutiliza)

## Implementación (2026-10-04)

Hecha en una rama de harness, pendiente de la revisión humana que exige R4. El rol queda con modelo
`gpt-5.3-codex` (fallback `claude-sonnet-5`) y `models.yaml` pasa de 1.2.0 a 1.3.0 (rol nuevo = minor,
según la política de ADR-004).

**Dos desviaciones respecto a lo decidido arriba, a aprobar explícitamente:**

1. **`global_deny.paths` exigía una excepción.** Prohibía `.harness/**` y `.agents/**` a *todos* los
   roles "sin excepción", de modo que el `writable_paths` de este rol se contradecía con la política
   global. Se añadió `except_roles: [harness-maintainer]` **solo** a esas dos rutas; `AGENTS.md`,
   `.github/workflows/**` y el resto siguen denegadas a todos.
2. **`protected_paths` incluye también `init.sh` y `harness.config.json`**, que la decisión original
   no mencionaba. Son el gate y la configuración de guardrails: darle escritura sobre ellos amplía el
   alcance de ADR-007 y es una decisión humana. Consecuencia: la rama PHP de `init.sh` y el gate G4 en
   `harness.config.json` (ADR-009, ADR-013) **no podrá hacerlos este rol** hasta que se decida.

**Verificación realizada**: `validate_harness.py` 94 → 116 comprobaciones, coherente; adaptadores
sincronizados; y tres pruebas negativas con código de salida 1 (el Developer declarando `scripts/**`,
el maintainer con `AGENTS.md` escribible, y la excepción global ampliada a otro rol).

**Defectos preexistentes corregidos en la misma PR** porque tocaban `scripts/`: la dimensión 4 de
`diagnose_harness.py` exigía `deny: edit` para el Verifier (lo contrario de lo correcto desde la
corrección del 2026-09-28) y bajaba el diagnóstico a 3/4; y `validate_harness.py` tenía una constante
duplicada.
