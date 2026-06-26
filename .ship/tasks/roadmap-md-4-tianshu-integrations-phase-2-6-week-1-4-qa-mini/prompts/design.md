You must use Skill('ship:design'). Skip preamble and auth gate.

Planning request:
---

严格按照 ROADMAP.md 4 周计划推进 Tianshu Integrations 项目。当前进入 Phase 2-6:Week 1-4 工程实现 + QA + 收尾。MiniMax API key 已提供,Obsidian vault 锁定 ~/Desktop/知识库/
---

IMPORTANT: You MUST write both spec.md and plan.md to the artifacts directory.
The orchestrator validates these files exist and are non-empty before advancing
to the dev phase. Do NOT respond conversationally — write the artifacts to disk.

If this task involves frontend/UI changes and no DESIGN.md exists at project root,
note in spec.md that one should be created via /ship:visual-design before or
after this pipeline run.

task_id: roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini
Artifacts: .ship/tasks/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini/plan/
Raw input: .ship/tasks/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini/input/requirement.md
Run state: .ship/tasks/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini/control/run_state.yaml
Branch: ship/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini
HEAD: HEAD
unknown
Scope mode: full
Mode: /ship:auto staged workflow — no user questions, treat escalations as blocked.

If lightweight YAML planning notes would help this specific task, you may write
them under .ship/tasks/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini/control/. Choose the schema yourself and keep
Markdown/code as the real deliverables.

Scope mode `refactor` means the task is behavior-preserving (refactor,
simplify, rename, extract, dedupe, etc.). In that mode, skip Phase 6
(Execution Drill) — the "every step is implementable" check adds little
value when the steps are small code movements. Peer investigation and
diff still run. See design SKILL.md "Scope Mode" for details.
Scope mode `full` runs all six phases.
