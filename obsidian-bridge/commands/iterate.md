---
description: Set iteration status (drafting / on-shelf / picked / parked / rejected / superseded). May be sunset in favour of conversational use
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Set the status of an iteration. Replaces `/vault-bridge iteration-set-status`.

> **May be sunset.** Iteration creation and listing are conversational ("new iteration D for foo on the navy track", "show on-shelf iterations"). Only state transitions get a command, for mechanical reliability. If conversational handling proves robust across model versions, this command may be removed in a future release. See `obsidian-bridge:vault-bridge` skill for the full iteration workflow.

## Usage

```
/iterate <id> <status>                Set iter <id> in current project to <status>
/iterate <slug>:<id> <status>         Same, but explicit project slug
```

### Valid statuses

```
drafting       work in progress
on-shelf       done thinking, available to pick
picked         selected as the direction
parked         interesting later, not now
rejected       no, killed
superseded     newer iteration replaces this
```

Dispatch to the `vault-bridge` skill's `/iterate` section.
