# Superpowers Integration

The Cabinet of IMD should leverage the Superpowers plugin skills when they are available. These structured development workflows complement the cabinet's own protocols.

## Skill Mapping

### /brainstorming
**When:** Before any creative work — new features, components, architecture decisions, design approaches.
**Cabinet integration:** Kevijntje or the relevant specialist should invoke `/brainstorming` at the start of any significant creative task. This precedes the cabinet's own planning and gate system. The brainstorming output feeds into the first gate.

### /dispatching-parallel-agents
**When:** When 2+ independent tasks can be worked on without shared state.
**Cabinet integration:** This is how collaboration pairings actually execute in practice. When Henske + Thieuke are on UI polish AND Sakke + Jonasty are on backend simultaneously, use parallel agent dispatch. Each agent pair runs independently, results converge at the next gate.

### /executing-plans
**When:** A written implementation plan exists and needs executing with review checkpoints.
**Cabinet integration:** After a gate is approved and work begins, use `/executing-plans` to structure the execution phase. The plan's review checkpoints align with the cabinet's gate system.

### /finishing-a-development-branch
**When:** Implementation is complete, tests pass, and the branch needs integrating.
**Cabinet integration:** Tom, Jonas, and Sakke coordinate branch finishing. This skill should be invoked when approaching a merge gate. Bostrol ensures documentation is current before the branch closes.

### /requesting-code-review
**When:** Completing tasks, implementing major features, or before merging.
**Cabinet integration:** The relevant specialist (or Jonasty for QA) requests a code review at the gate. This formalizes the cabinet's quality checkpoint.

### /receiving-code-review
**When:** Receiving code review feedback before implementing suggestions.
**Cabinet integration:** When feedback comes in, the specialist who owns the code handles it. Jonasty may assist with integration/API feedback. Thieuke handles frontend review responses. Sakke handles security findings.

## Priority Order

When both Superpowers and Cabinet protocols apply to a situation:
1. Superpowers provides the **structural workflow** (brainstorm → plan → execute → review → finish)
2. The Cabinet provides the **personality, governance, and gate approval** layer on top
3. Tom always approves gates regardless of which system generated the checkpoint

The cabinet does NOT replace Superpowers — it rides on top of it with character, governance, and team dynamics.
