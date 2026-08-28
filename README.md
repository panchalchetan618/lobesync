# Lobesync

A personal AI assistant for your terminal. Manage tasks, notes, memories, and checklists through natural conversation — powered by Claude and built on LangGraph.

```
Lobesync — Personal AI Assistant
Type /help for commands · exit to quit

You: Create a checklist "Launch" and add tasks for writing tests and updating docs
Lobesync: Done! Created checklist "Launch" (ID: 1) with two tasks — "Write tests" (ID: 2)
          and "Update docs" (ID: 3), both set to pending.

You: Mark write tests as in progress
Lobesync: Updated "Write tests" to in progress. ✓
```

## Features

- **Natural language interface** — just talk to it, no commands to memorize
- **Tasks** with deadlines, statuses, and checklist grouping
- **Checklists** with items and pending-task guards
- **Notes** for storing anything
- **Memories** — the agent proactively remembers personal facts about you across sessions
- **Session management** — multiple conversations, each with its own history and incremental summary
- **Streaming responses** with live Markdown rendering
- **Cost-efficient** — one LLM planning call per turn; execution and result rendering are local
- **Local SQLite** by default — your data stays on your machine

## Architecture

Lobesync uses a [LangGraph](https://github.com/langchain-ai/langgraph) graph with four nodes:

```
user input
    │
    ▼
┌─────────┐   direct response (streamed)   ┌────────────┐
│ Planner │ ──────────────────────────────▶ │ Commitment │ ──▶ END
└─────────┘                                 └────────────┘
    │ tool calls needed                            ▲
    ▼                                              │
┌──────────┐                              ┌────────────────┐
│ Executor │ ────────────────────────────▶ │   Completion   │
└──────────┘                              └────────────────┘
```

- **Planner** — single LLM call (Haiku). Streams a direct response for chat, or calls `make_plan` for data operations. Receives user memories in system prompt (cached) + session summary + last 5 messages.
- **Executor** — runs the plan. Atomic groups use one session (all-or-nothing). Independent steps run in separate sessions.
- **Completion** — deterministically renders verified tool results, including item IDs.
- **Commitment** — saves user messages, assistant messages, and tool calls to DB. Incrementally summarizes only unsummarized history every 5 messages.

## Installation

### Using pipx (recommended for CLI tools)

```bash
pipx install lobesync
```

### Using pip

```bash
pip install lobesync
```

### From source

```bash
git clone https://github.com/panchalchetan618/lobesync
cd lobesync
pip install -e .
```

## Setup

Run `lobesync` for the first time and the setup wizard will guide you through:

1. Choosing an LLM provider (Anthropic, OpenAI, Google, Groq, Mistral, or local Ollama) and entering its model name and API key
2. Choosing a local SQLite database (recommended) or providing your own database URL

Config is saved to `~/.lobesync/config.json`. Local database is stored at `~/.lobesync/lobesync.db`.

Only providers whose LangChain package is installed appear in the wizard. To enable another provider, install its package first, e.g. `pip install langchain-openai`, then run setup again.

## Usage

```bash
lobesync
```

### CLI Commands

| Command | Description |
|---|---|
| `/sessions` | List all chat sessions |
| `/session new` | Start a new session |
| `/session new <name>` | Start a new named session |
| `/session <id>` | Switch to an existing session |
| `/help` | Show all commands |
| `exit` | Quit |

### Example interactions

```
You: Add a task to review PRs by Friday
You: What are my pending tasks?
You: Create a note about the deployment process
You: I prefer concise responses
You: Mark the PR review task as done
You: Start a new checklist for the Q2 release
```

The agent remembers personal facts across sessions — tell it your preferences, goals, or anything relevant and it will factor them in automatically.

## Configuration

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DATABASE_URL` | SQLAlchemy database URL (default: local SQLite) |

Set via the setup wizard or in `~/.lobesync/config.json`:

```json
{
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "DATABASE_URL": "sqlite:////home/you/.lobesync/lobesync.db"
}
```

You can also use a `.env` file in the working directory or environment variables as fallback.

## Model

All nodes use the model configured during setup (`LLM_PROVIDER` + `LLM_MODEL` in `~/.lobesync/config.json`).

## Quality and operations

Schema changes are versioned with Alembic and applied automatically at startup. Before release, run the same checks enforced in CI:

```bash
pip install -e .[dev]
python -m ruff check .
python -m mypy lobesync
python -m pytest
python -m build
```

Back up the SQLite database before upgrades. The application records each executed tool's arguments and result with the assistant message for traceability.

## Tech stack

- [LangChain](https://github.com/langchain-ai/langchain) (provider-agnostic LLM access)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Rich](https://github.com/Textualize/rich)

## Contributing

Pull requests are welcome. For major changes, open an issue first.

## License

MIT
