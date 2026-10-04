# ADR-017 — El maintainer puede ampliar el gate, no vaciarlo

- **Fecha**: 2026-10-04
- **Estado**: `aceptada` · **Implementación**: **HECHA** (pendiente de revisión humana)
- **Decisor**: Juan Moreno (responsable del harness)
- **Feature**: `_harness`
- **Cierra**: decisión abierta **D-4** de `docs/pendientes.md`
- **Modifica**: ADR-007 (amplía el alcance del rol que allí se definió)
- **Tareas afectadas**: `.agents/policies/permissions.yaml`, `scripts/validate_harness.py`

## Contexto

ADR-007 creó el rol `harness-maintainer` con escritura sobre `scripts/`, `.harness/` y `.agents/`. Al
implementarlo se tomaron **dos decisiones restrictivas que no estaban en el ADR original**, una de
ellas documentada como desviación a aprobar:

```yaml
protected_paths:
  - "AGENTS.md"
  - ".github/workflows/**"
  - "init.sh"                 # ← desviación: no estaba en ADR-007
  - "harness.config.json"     # ← desviación: no estaba en ADR-007
```

La decisión fue deliberadamente conservadora: ante la duda, aplicar **deny-first** y pedir permiso en
lugar de asumir que el rol podía tocar todo lo que necesitaba.

Con el tiempo, esa restricción bloqueó **tres pendientes**:

| Pendiente | Necesita | Qué queda impedido |
| :--- | :--- | :--- |
| **11** | `harness.config.json` | Corregir `"name": "deepseek-harness"` → identidad real |
| **9** | `harness.config.json` | Añadir el gate **G4** a `requireHumanApprovalGates` |
| **5** | `init.sh` | La rama PHP del gate (Pint, PHPStan, `vendor/bin/phpunit`) |

**El pendiente 11 es precondición del 3**: el instanciador (ADR-006) lee la identidad desde
`harness.config.json`. Si sigue diciendo `deepseek-harness`, **cada componente instanciado nacería con
el nombre de otro repositorio**, y el `AGENTS.md` generado heredaría ese error.

### La tensión

`init.sh` **es el único gate** (R6). Dar permiso de escritura sobre él significa que un rol podría, en
teoría, **debilitar las comprobaciones** en lugar de ampliarlas — que es exactamente lo que R6 prohíbe.

Pero sin ese permiso, **nadie puede añadirle la rama PHP**, y el gate seguiría dando PASS sin comprobar
nada para ese stack. La restricción protegía la garantía y a la vez impedía mejorarla.

## Decisión

**Se amplía el alcance del `harness-maintainer` a `init.sh` y `harness.config.json`, y se compensa con
un check que exige que el gate conserve sus comprobaciones obligatorias.**

### 1. El permiso se amplía

```yaml
harness-maintainer:
  writable_paths:
    - "scripts/**"
    - ".harness/**"
    - ".agents/**"
    - "init.sh"                 # nuevo (2026-10-04)
    - "harness.config.json"     # nuevo (2026-10-04)
  protected_paths:
    - "AGENTS.md"               # la ley sigue siendo solo humana (§9)
    - ".github/workflows/**"    # CI sigue fuera del alcance de todo agente
```

**`AGENTS.md` y CI se quedan protegidos en cualquier caso.** Eso no está en discusión.

### 2. La salvaguarda: `check_init_gate_integrity()`

El permiso se compensa con un check que verifica que `init.sh` **conserva sus siete comprobaciones
obligatorias** (`secrets`, `lint`, `format`, `typecheck`, `tests`, `harness`, `guardrails`) y que
termina con código de salida.

El principio es el de ADR-015: **el check mira algo distinto de sí mismo**. No pregunta «¿puede alguien
escribir el gate?» —eso ya está decidido— sino **«¿el gate sigue comprobando lo que debe?»**.

Así, el rol puede:
- ✅ **Añadir** la rama PHP de `lint`/`format`/`typecheck`/`tests`
- ✅ **Añadir** comprobaciones nuevas
- ❌ **Quitar** o renombrar una comprobación existente
- ❌ **Dejar el gate sin código de salida**

### 3. De límite técnico a límite de proceso, declarado

Este cambio **degrada una garantía**, y conviene nombrarlo: antes, debilitar el gate era imposible
(el archivo no era escribible); ahora es **posible pero detectable**. Es el mismo tipo de transición
que ADR-011 documentó para R3.

La mitigación completa es: permiso acotado + check de integridad + **revisión humana obligatoria de
todo su diff** (ADR-007). Las tres, no una.

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| **A. Mantener la restricción** (PR humana cada vez) | El gate sigue siendo inmodificable por agentes | Bloquea 3 pendientes, **incluido el 11, precondición del instanciador**. El humano tendría que editar `harness.config.json` para cada proyecto nuevo | Inviable ahora que el instanciador es el siguiente paso |
| **B. Ampliar el permiso sin salvaguarda** | Simple | El gate queda escribible **y sin comprobación**: se puede vaciar en silencio y el `init.sh` resultante seguiría dando PASS. Exactamente lo que R6 prohíbe | Es la lección de ADR-011 aplicada al revés |
| **C. Dejar `init.sh` fuera y `harness.config.json` dentro** | El gate sigue inmodificable; se desbloquean 9 y 11 | El pendiente 5 (rama PHP) queda bloqueado, y es necesario para la **verificación real** del primer componente | Retrasa el objetivo por un caso que la opción D resuelve |
| **D. Ampliar + check de integridad del gate** | Desbloquea los 3 pendientes; conserva R6 **como mecanismo**; coherente con ADR-015 | El gate pasa de inmodificable a detectable | — (la elegida) |

## Consecuencias

**Positivas**
- Se desbloquean los pendientes **5, 9 y 11**, incluido el que era precondición del instanciador.
- **R6 se conserva como mecanismo**, no como confianza: el gate no puede perder comprobaciones.
- La ampliación es **auditable**: el check corre en cada validación, no solo al editar.
- Coherente con la lección transversal: no se confía en la instrucción, se comprueba el efecto.

**Negativas / deuda asumida**
- **Degradación declarada**: el gate es escribible por un rol. Antes no lo era. La defensa pasa a ser
  detección + revisión humana, y eso **puede fallar** si la revisión es superficial.
- El check es **textual**: busca `record "<nombre>"` en `init.sh`. Un cambio de formato legítimo del
  script daría un falso error. Se acepta: el formato está fijado y el error es explícito, no silencioso.
- Un rol con permiso sobre `scripts/` **podría modificar el propio validador** para que no compruebe
  `init.sh`. Es el límite estructural del modelo de permisos: el vigilante está dentro del perímetro.
  Mitigación: revisión humana del diff (R4) — el mismo límite que ya existía antes de este ADR.

**Neutrales**
- `AGENTS.md` y `.github/workflows/**` no cambian de estado.
- Los otros cinco roles no se ven afectados.

## Cómo revertir esta decisión

Devolver `init.sh` y `harness.config.json` a `protected_paths` y retirar el check. Se recupera la
garantía técnica y se vuelven a bloquear los pendientes 5, 9 y 11.

## Cómo se verificó

1. `python scripts/validate_harness.py` → **132 comprobaciones, COHERENTE** (eran 123; el check nuevo
   añade 9: 7 comprobaciones obligatorias + la existencia del gate + su código de salida).
2. **Tres pruebas negativas**, cada una con código de salida 1 y el fixture revertido:
   - `init.sh` sin el check `guardrails` → `no declara la comprobacion obligatoria 'guardrails' (R6)`
   - `init.sh` vaciado a 5 líneas → falla por **cada** comprobación ausente
   - `harness-maintainer` con `AGENTS.md` fuera de `protected_paths` → `falta 'AGENTS.md' en protected_paths`
3. Verificado que no quedan fixtures (`.bak`) en el árbol.

## Referencias

- ADR-007 (el rol y sus límites; este ADR amplía su alcance)
- ADR-015 (un check solo es real cuando mira algo distinto de sí mismo)
- ADR-011 (de límite técnico a límite de proceso, declarado)
- `AGENTS.md` §1 R4 y R6, §9 (cambios a la ley)
- `docs/pendientes.md` §5 (decisión D-4)
