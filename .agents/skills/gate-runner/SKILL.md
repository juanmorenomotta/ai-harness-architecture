---
name: gate-runner
description: "Ejecuta e interpreta el gate de verificación init.sh, clasifica el fallo y decide si se puede avanzar de fase. Use when running verification, interpreting a failing gate, or deciding PASS/FAIL between SDD phases."
argument-hint: "[--fast|--json]"
---

# Gate Runner (init.sh)

`init.sh` es el **único** gate del harness (R6). Esta skill enseña a ejecutarlo, a leer su
salida y a decidir sin violar las reglas.

## Cuándo usar

- El Developer terminó su tarea y necesita confirmar que puede commitear.
- El Verifier necesita la salida literal para `verify.md`.
- El gate falla y hay que clasificar si el fallo es de la tarea, del entorno o del harness.

## Ejecución

```bash
./init.sh              # todos los checks
./init.sh --fast       # lint + typecheck (sin tests), para iteración rápida
./init.sh --json       # salida máquina-legible, para diagnose_harness.py
```

Códigos de salida:

| Código | Significado | Qué hacer |
| :--- | :--- | :--- |
| `0` | PASS | Se puede commitear / avanzar de fase |
| `1` | FAIL | Arreglar el fallo. **No** avanzar (R6) |
| `2` | BLOQUEO | Config inválida o herramienta ausente → escalar |

## Clasificación de fallos (crítico)

Antes de tocar nada, determina **de quién es el fallo**:

| Tipo | Síntoma | Acción correcta |
| :--- | :--- | :--- |
| **De la tarea** | El check pasa en `main` pero falla en tu rama | Arregla tu código |
| **De entorno** | `ruff not found`, `pytest not found` → estado `SKIP` | **Bloquea y escala.** No instales globalmente |
| **Preexistente** | Ya fallaba en `main` antes de tu cambio | **Bloquea y escala.** No lo arregles dentro de tu tarea |
| **De harness** | El propio `init.sh` tiene un bug | **Bloquea.** Tocar `init.sh` es R4 (PR humano separado) |

Comprobar si es preexistente:

```bash
git stash && ./init.sh; git stash pop     # ¿falla sin tus cambios?
```

## Prohibiciones absolutas

- ❌ Saltar el gate (`--no-verify`, commit con hooks desactivados).
- ❌ Desactivar un check en `harness.config.json` para que pase (R4).
- ❌ Marcar/`skip`/`xfail` tests para que pasen (R7).
- ❌ "Arreglar" tests que reflejan comportamiento correcto.
- ❌ Instalar herramientas globalmente para que el check deje de dar `SKIP`.

Un `SKIP` **no es un PASS**. Si un check crítico está en `SKIP` por falta de herramienta,
la verificación es **incompleta** y el Verifier debe reportarlo.

## Protocolo cuando el gate no pasa y no es tu código

```
BLOQUEO: init.sh falla por causa <entorno|preexistente|harness>.
Evidencia: <comando exacto + 5 líneas de salida>
Verificado en main: sí | no
Necesito: <instalar la herramienta X en el entorno del proyecto | un humano que arregle Y en PR separado>
```

## Salida para `verify.md`

Pega la salida **literal**, sin resumir ni editar. El Verifier debe ver exactamente lo que viste:

````markdown
### Gate (`./init.sh`)

```
$ ./init.sh
== Gate del harness (init.sh) ==
  ✔ secrets      sin secretos detectados
  ✔ lint         ruff check
  ...
== GATE: PASS ==
```
````

## Ver también

- [`init.sh`](../../../init.sh)
- Skill `security-review` para el check de secretos
- Rol [sdd-verifier](../../agents/sdd-verifier.md)
