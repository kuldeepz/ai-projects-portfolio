# Skills

Custom Claude Code / VS Code agent skills built as SKILL.md files.

Each skill is a reusable, invocable prompt workflow — callable via `/skill-name` inside Claude Code or VS Code Copilot Chat.

## Structure

```
skills/
├── README.md          ← this file
└── <skill-name>/
    ├── SKILL.md       ← skill definition (trigger, instructions, steps)
    └── README.md      ← usage docs
```

## Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| _(coming soon)_ | | |

## How to Use a Skill

In Claude Code terminal:
```
/skill-name
```

In VS Code Copilot Chat:
```
@workspace /skill-name
```

## How to Build a Skill

A SKILL.md file defines:
- **name** — the `/command` to invoke it
- **description** — when the agent should activate it
- **instructions** — step-by-step behavior
- **tools** — allowed tool calls

See [Claude Code Skills documentation](https://docs.anthropic.com/en/docs/claude-code) for full reference.
