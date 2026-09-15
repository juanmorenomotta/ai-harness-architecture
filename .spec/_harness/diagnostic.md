# Auto-diagnóstico del harness — 2026-09-15

Informe generado automáticamente por `scripts/diagnose_harness.py`. Nueve dimensiones independientes: **un solo número agregado oculta más de lo que revela**.

**Puntuación global**: 35/36 (97%)

## ⚠ Checks inertes (verde falso)

Estos checks existen y reportan PASS, pero **no pueden verificar nada todavía**. La puntuación de la dimensión 9 ya está penalizada por ello.

- `secrets`: sin repo git, el escaneo del árbol no se ejecuta
- `guardrails`: sin repo git, no se detectan cambios en archivos protegidos
- `lint`/`format`/`typecheck`/`tests`: sin manifiesto de proyecto, todo da SKIP
- `secrets`: gitleaks no instalado (solo se usa el patrón grep de respaldo)

## Resumen por dimensión

| # | Dimensión | Nivel | Puntuación |
| :-- | :--- | :--- | :--- |
| 1 | Ingeniería de contexto | completo | `████` 4/4 |
| 2 | Adopción de herramientas | completo | `████` 4/4 |
| 3 | Integración en el workflow | completo | `████` 4/4 |
| 4 | Revisión de código con IA | completo | `████` 4/4 |
| 5 | Controles de governance | completo | `████` 4/4 |
| 6 | Cobertura de skills | completo | `████` 4/4 |
| 7 | Autonomía agéntica | completo | `████` 4/4 |
| 8 | Generación de tests | completo | `████` 4/4 |
| 9 | Gates de CI/CD con IA | sólido | `███░` 3/4 |

## Lectura frente a los niveles objetivo

| Nivel | Requisito | Estado |
| :--- | :--- | :--- |
| nivel-1 | ≥ 9 puntos y dimensiones [1, 3, 5, 6] en nivel ≥ parcial | ✅ alcanzado |
| nivel-2 | ≥ 22 puntos y dimensiones [1, 2, 3, 4, 5, 6, 9] en nivel ≥ parcial | ✅ alcanzado |

## Detalle

### 1. Ingeniería de contexto — completo (4/4)

**Evidencia**
- AGENTS.md presente con reglas de oro numeradas (ley del repo)
- convención de artefactos SDD en `.spec/<feature>/` documentada
- contexto acotado por rol vía `writable_paths`

### 2. Adopción de herramientas — completo (4/4)

**Evidencia**
- adaptadores generados: Claude Code, Antigravity, Codex CLI, orquestador propio
- sincronización automatizada de adaptadores

### 3. Integración en el workflow — completo (4/4)

**Evidencia**
- 5 roles definidos: sdd-developer.md, sdd-init.md, sdd-security-reviewer.md, sdd-tech-lead.md, sdd-verifier.md
- skill de orquestación presente (delega fases en frío)
- workflow declarado en harness.config.json (patrones de commit/rama)

### 4. Revisión de código con IA — completo (4/4)

**Evidencia**
- rol Verifier definido, separado del Developer
- el Verifier no puede editar código (independencia forzada)
- skill de informe de verificación con veredicto PASS/FAIL

### 5. Controles de governance — completo (4/4)

**Evidencia**
- política deny-first con patrones de comando prohibidos
- archivos protegidos declarados (AGENTS.md, .harness/, .agents/)
- auto-merge explícitamente deshabilitado (R3)
- tres gates humanos definidos (G1 scope, G2 plan, G3 merge)

### 6. Cobertura de skills — completo (4/4)

**Evidencia**
- 8 skills: cubre spec, tareas, verificación, seguridad y cambio de modelo

### 7. Autonomía agéntica — completo (4/4)

**Evidencia**
- protocolo de bloqueo/escalado explícito (el agente sabe cuándo parar)
- errores no reintentables clasificados (401/402/403/404)
- gestión de saldo/cuota agotada → bloqueo, no reintento infinito

### 8. Generación de tests — completo (4/4)

**Evidencia**
- el Developer debe escribir el test que falla antes de implementar
- el Verifier comprueba regresión y que no se debiliten tests (R7)
- R7 en la ley: prohibido borrar o debilitar tests

### 9. Gates de CI/CD con IA — sólido (3/4)

**Evidencia**
- gate ejecutable `./init.sh` → FAIL: /bin/bash: A:jmmlibrosAI-Firstdeepseek-harnessinit.sh: No such file or directory
- checks de lint/tests/formato/typecheck declarados en la configuración
- el gate incluye verificación de integridad y secretos

**Carencias**
- 4 check(s) INERTE(S): el gate pasa sin verificar nada real (un PASS así no debe contarse como 4/4)

**Atención**
- el gate falla ahora mismo; revisar antes de delegar trabajo
- `secrets`: sin repo git, el escaneo del árbol no se ejecuta
- `guardrails`: sin repo git, no se detectan cambios en archivos protegidos
- `lint`/`format`/`typecheck`/`tests`: sin manifiesto de proyecto, todo da SKIP
- `secrets`: gitleaks no instalado (solo se usa el patrón grep de respaldo)

---

Advertencia operativa: introducir agentes de IA en un estado caótico **acelera el caos, no la entrega**. Si las dimensiones de contexto (1), workflow (3), governance (5) y gates (9) están por debajo de *parcial*, el patrón multiagente amplificará la desorganización en lugar de la productividad.
