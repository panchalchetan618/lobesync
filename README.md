# Lobesync

A personal AI assistant for your terminal. Manage tasks, notes, memories, and checklists through natural conversation — powered by your chosen LLM provider and built on LangGraph.

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
- **Optional memories** — cross-session retention is disabled by default and requires your consent
- **Session management** — multiple conversations, each with its own history and incremental summary
- **Streaming responses** with live Markdown rendering when supported by the provider
- **Cost-efficient** — one LLM planning call per turn; execution and result rendering are local
- **Local SQLite only** — the open-source edition keeps application data on your machine

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

- **Planner** — a single LLM call that streams a direct response when the provider supports it, or calls `make_plan` for data operations. Receives explicitly marked untrusted memory context, a session summary, and the last 5 messages.
- **Executor** — runs the plan. Atomic groups use one session (all-or-nothing). Independent steps run in separate sessions.
- **Completion** — deterministically renders verified tool results, including item IDs.
- **Commitment** — saves user messages, assistant messages, and tool calls to DB. Incrementally summarizes only unsummarized history every 5 messages.

## Installation

Lobesync currently supports Python 3.12 and 3.13. Python 3.14 support is deferred until its LangChain dependencies support it without compatibility warnings.

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

1. Choosing Anthropic, OpenAI, Google, or a custom OpenAI-compatible provider, then entering its model name and API key when required
2. Choosing whether to enable cross-session memory (disabled by default)

Config is saved to `~/.lobesync/config.json`. API keys are stored in your operating system credential store. Existing plaintext keys from older Lobesync versions are migrated automatically and removed from the config file only after that migration succeeds. The local database is stored at `~/.lobesync/lobesync.db`.

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
| `/memory` | Show whether cross-session memory is enabled |
| `/memory on` | Enable cross-session memory |
| `/memory off` | Disable cross-session memory without deleting existing local memories |
| `/configure` | Change provider, model, API key, or custom OpenAI-compatible endpoint |
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

When cross-session memory is enabled, ask the assistant explicitly to remember information. You can disable it at any time with `/memory off`.

When an action would delete multiple items, Lobesync shows the selected targets and asks for an immediate Yes/No decision. The safe default is No; use the arrow keys and Enter in supported terminals.

## Configuration

| Variable | Description |
|---|---|
| `LLM_API_KEY` | Optional environment-variable fallback for your provider API key |
| `LLM_BASE_URL` | Base URL for the custom OpenAI-compatible provider |
| `DATABASE_URL` | Local SQLite database URL |

Set via the setup wizard or in `~/.lobesync/config.json`:

```json
{
  "LLM_PROVIDER": "anthropic",
  "LLM_MODEL": "claude-haiku-4-5-20251001",
  "MEMORY_ENABLED": false,
  "DATABASE_URL": "sqlite:////home/you/.lobesync/lobesync.db"
}
```

The open-source edition supports local SQLite storage only. Remote storage, organization controls, and hosted integrations are planned for Lobesync Enterprise. You can also use a `.env` file in the working directory or environment variables as a non-persistent API-key fallback.

Custom providers must expose an OpenAI-compatible API. Use HTTPS for hosted endpoints; HTTP is accepted only for localhost endpoints. A custom endpoint receives the prompt context needed to answer requests. API keys are optional for custom providers so local keyless servers work too.

## Privacy

Lobesync stores conversations, tool-call records, notes, tasks, and optional memories in the local SQLite database. SQLite data is plaintext, so protect your device and backups with operating-system access controls or disk encryption. API keys are kept in the operating system credential store rather than the config file; environment variables remain an optional non-persistent fallback. The configured LLM provider receives the prompt context needed to answer a request; use a local provider such as Ollama when you need inference to stay on-device.

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

Back up the SQLite database before upgrades. The application records each executed tool's arguments and result with the assistant message for traceability. If a request fails after beginning independent operations, some operations may already have completed; review the displayed results and your data before retrying.

## Tech stack

- [LangChain](https://github.com/langchain-ai/langchain) (provider-agnostic LLM access)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Rich](https://github.com/Textualize/rich)

## Contributing

Pull requests are welcome. For major changes, open an issue first.

## License

MIT
