---
name: spec-authoring
description: "Escribe scope.md con criterios de aceptación verificables y no-objetivos. Use when defining feature scope, writing acceptance criteria, describing non-goals, or turning a vague request into a measurable specification."
argument-hint: "<prompt de la feature>"
---

# Spec Authoring (scope.md)

Convierte una petición vaga en un alcance **medible**. Usada por el rol `sdd-init`.

## Cuándo usar

- No existe `.spec/<slug>/scope.md` y hay una feature nueva.
- Un criterio de aceptación existente no es verificable y hay que reescribirlo.
- Aparece una idea nueva a mitad de feature (va a §No-objetivos, no a implementación).

## La regla que lo gobierna todo

**Todo criterio de aceptación debe poder verificarse con un comando o una observación binaria (R5).**

| ❌ No verificable | ✅ Verificable |
| :--- | :--- |
| "El código debe ser limpio" | "`./init.sh` pasa en verde sin nuevos warnings" |
| "Debe ser rápido" | "`GET /users?limit=100` responde en < 300 ms con p95 sobre 1000 peticiones" |
| "Buen manejo de errores" | "Un payload sin `email` devuelve HTTP 400 con `{"error":"email_required"}`" |
| "Debe ser seguro" | "Un intento de login con contraseña incorrecta no revela si el usuario existe" |
| "Fácil de usar" | "Un usuario completa el flujo en ≤ 3 clics desde la home" |

## Plantilla

```markdown
# Scope — <nombre de la feature>

- **Slug**: `<feature-slug>`
- **Autor**: <rol que lo escribe>
- **Fecha**: <YYYY-MM-DD>
- **Estado**: `borrador` | `aprobado`
- **Aprobado por**: —            <!-- G1: lo rellena un humano, nunca un agente -->

## 1. Problema

<Quién sufre qué y por qué importa ahora. 2–4 frases. Sin solución técnica.>

## 2. Resultado esperado

<En una frase: qué será verdad cuando esto esté terminado.>

## 3. Criterios de aceptación

| ID | Criterio | Verificación |
| :--- | :--- | :--- |
| AC-1 | Dado <contexto>, cuando <acción>, entonces <resultado observable> | `<comando o comprobación>` |
| AC-2 | … | … |

<!-- Cada AC debe tener un comando o una comprobación binaria. Sin excepciones. -->

## 4. No-objetivos

<!-- Mínimo 3. Es la defensa contra el crecimiento de alcance (R8). -->

- NO se implementa <X>.
- NO se modifica <Y>.
- NO se migra <Z>; queda para una feature futura.

## 5. Supuestos

| # | Supuesto | ¿Confirmado? | Si es falso… |
| :--- | :--- | :--- | :--- |
| S1 | <supuesto> | sí / **ABIERTO** | <qué cambia> |

<!-- Todo supuesto ABIERTO bloquea el gate G1. -->

## 6. Preguntas abiertas

- [ ] <pregunta> — responsable: <humano>

## 7. Fuera de discusión (restricciones)

<Restricciones fijas: plazos, compatibilidad, normativa, presupuesto, hardware.>

## 8. Métricas de éxito

<Cómo se sabrá, después del despliegue, que la feature valió la pena. Si no hay forma de medirlo, dilo.>
```

## Procedimiento

1. **Extrae el slug**: `kebab-case`, 2–4 palabras, sin verbos genéricos
   (`login-oauth` ✅ · `mejoras-varias` ❌).
2. **Escribe §1–§2 sin mencionar tecnología.** Si nombras un framework aquí, ya estás diseñando.
3. **Deriva los AC del §2**, uno por resultado observable. Ordena de más a menos crítico.
4. **Comprueba cada AC** preguntándote: *¿qué comando exacto lo demuestra?* Si no se te ocurre
   ninguno, el criterio está mal formulado: reescríbelo o elimínalo.
5. **Escribe §4 (no-objetivos)** con al menos 3 items. Piensa en lo que un lector *asumiría*
   que entra y no entra.
6. **Marca los supuestos ABIERTOS.** No los resuelvas tú: son del humano en G1.
7. **Escribe el archivo** en `.spec/<slug>/scope.md`.
8. **Devuelve el resumen** de ≤ 10 líneas definido en el rol `sdd-init`.

## Anti-patrones

- **Criterios de proceso** ("seguir TDD") en vez de criterios de resultado. El proceso es del
  harness, no de la feature.
- **AC duplicados**: si dos criterios siempre pasan o fallan juntos, es uno solo.
- **Alcance elástico**: "y además aprovechamos para…". Corta: va a §4.
- **No-objetivos vacíos**: sin ellos, la Fase de diseño inventará alcance.
- **Supuestos disfrazados de hechos**: si no lo confirmó un humano, es `ABIERTO`.

## Ver también

- Rol [sdd-init](../../agents/sdd-init.md)
- Skill `task-decomposition` (fase siguiente)
