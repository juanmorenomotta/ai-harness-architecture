---
name: adr-record
description: "Registra una decisión arquitectónica con contexto, alternativas y consecuencias. Use when documenting a technical decision, recording why an approach was rejected, logging a tradeoff, or recording scope changes."
argument-hint: "<título de la decisión>"
---

# ADR Record (Architecture Decision Records)

Registra **por qué** se decidió algo, para que un agente en frío no re-litigue la decisión ni
la contradiga por desconocimiento.

## Cuándo usar

- Se elige una tecnología, patrón o estructura con alternativas reales.
- Se descarta una aproximación por una razón no obvia (rendimiento, normativa, coste).
- Se acepta un compromiso (deuda técnica, compatibilidad, límite de tiempo).
- Se cambia de opinión sobre una decisión anterior (se crea un ADR nuevo, **no** se edita el viejo).

## Cuándo NO usar

- Decisiones reversibles de bajo impacto (nombre de una variable local, orden de imports).
- Lo que ya está cubierto por `AGENTS.md` (convenciones generales).
- Detalles de implementación sin alternativas (no hay decisión, hay una única forma).

## Ubicación y numeración

```
.spec/<feature-slug>/ADR/NNN-<decision-en-kebab-case>.md
```

`NNN` es secuencial **dentro de la feature**, empezando en `001`. Nunca se reutiliza un número.

## Plantilla

```markdown
# ADR-NNN — <título de la decisión>

- **Fecha**: <YYYY-MM-DD>
- **Estado**: `propuesta` | `aceptada` | `reemplazada por ADR-MMM` | `rechazada`
- **Decisor**: <rol> (+ aprobación humana si aplica)
- **Feature**: `<feature-slug>`
- **Tareas afectadas**: NNN, NNN

## Contexto

<La fuerza que obliga a decidir. Restricciones reales: plazo, compatibilidad, normativa,
rendimiento medido, equipo disponible. Sin contexto, la decisión parece arbitraria.>

## Decisión

<Qué se decide, en voz activa y en una frase. "Usaremos X para Y.">

## Alternativas consideradas

| Alternativa | Pros | Contras | Por qué se descarta |
| :--- | :--- | :--- | :--- |
| <A> | … | … | … |
| <B> | … | … | … |
| <C — la elegida> | … | … | — |

<Mínimo dos alternativas descartadas. Una sola opción no es una decisión: es una imposición.>

## Consecuencias

**Positivas**
- <qué mejora>

**Negativas / deuda asumida**
- <qué empeora, y qué se acepta a cambio>

**Neutrales**
- <qué cambia sin ser mejor ni peor>

## Cómo revertir esta decisión

<Qué costaría deshacerla. Si es irreversible, decirlo explícitamente.>

## Referencias

- <enlace a issue, doc, benchmark, RFC>
```

## Reglas

- **Un ADR es inmutable.** Si la decisión cambia, se escribe un ADR nuevo con estado
  `reemplazada por ADR-MMM` en el antiguo, en el mismo PR.
- **Escribe el ADR en el momento de decidir**, no al final. Reconstruir el razonamiento
  después produce ficción.
- **No inventes alternativas** que nadie consideró. Si solo hubo una opción viable, dilo:
  el ADR documenta la restricción, no un falso debate.
- **Encabeza con el resultado.** Quien lee un ADR en frío quiere saber la decisión en los
  primeros 5 segundos.

## Ver también

- Rol [sdd-tech-lead](../../agents/sdd-tech-lead.md)
- `AGENTS.md` §9 (registro de decisiones)
