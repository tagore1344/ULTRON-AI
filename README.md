# ULTRON AI

An advanced AI assistant application built with Python. ULTRON AI combines voice interaction, screen vision, system automation, persistent memory, multi-provider AI, and an autonomous agent runtime.

## ✨ Features

- **Voice Interaction** — Speech-to-text (Faster-Whisper) and text-to-speech (pyttsx3)
- **Frontier Agent Runtime** — GPT-6 Astra reasoning with tool use, web search, coding, testing, and iterative execution
- **Multi-Provider AI** — Gemini, OpenAI, and DeepSeek compatibility
- **Goal Execution** — Planning, task state, execution, verification, and bounded retries
- **Workspace Coding Tools** — Inspect files, edit files, run tests/builds, inspect Git status/diff, and create local commits
- **Model Routing** — Capability-based routing for general, coding, vision, and future specialist models
- **Screen Vision** — Capture and analyze screen content with OCR
- **System Automation** — Control volume, brightness, media, power, and more
- **Memory System** — Conversation, session, and vector memory for context
- **Cognitive Proposals (Phase 9E)** — ULTRON surfaces change-proposals to your phone for review/approval (see `docs/PHASE_9E.md`)
- **Intent Routing** — Rule-based intent detection for tool execution
- **Wake Word Detection** — Activate with "Hey ULTRON"
- **Face ID & Voice ID** — Advanced identity verification
- **GPU Acceleration** — Optional GPU support for AI models
- **Transparent Overlay UI** — On-screen assistant interface

## 🧠 Agent Architecture

Complex requests follow an agentic loop rather than a single prompt/response:

```text
User Goal
   ↓
Plan + Task State
   ↓
Inspect / Research
   ↓
Act with tools
   ↓
Observe results
   ↓
Run tests / verify
   ↓
Diagnose + iterate
   ↓
Verified result
```

When GPT-6 Astra is configured, it is the primary reasoning engine for complex work. OpenAI describes Astra as its most capable model for end-to-end work across coding, computer use, browsing, science, and professional workflows.

### Agent modules

```text
core/agent/
├── __init__.py
├── task_state.py          # Serializable task state and execution history
├── planner.py             # Goal → explicit steps
├── model_router.py        # Capability-based model selection
├── verifier.py            # Output verification primitives
├── agent_loop.py          # Synchronous execution core
├── async_agent_loop.py    # ULTRON agent integration
├── astra_agent.py         # GPT-6 Astra Responses API + workspace tools
└── test_agent_core.py     # Agent-core tests
```

## ⚡ Enable GPT-6 Astra

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your API key in the environment or `.env`:

```text
OPENAI_API_KEY=your_key_here
ULTRON_MODEL=gpt-6-astra
ULTRON_REASONING_EFFORT=high
ULTRON_USE_ASTRA=1
ULTRON_WORKSPACE=.
```

`ULTRON_WORKSPACE` is the root directory available to the autonomous coding tools. File operations are constrained to that workspace. The agent can inspect and modify files and run development commands there, but it does not push Git changes remotely.

GPT-6 Astra supports the Responses API with function calling, web search, file search, code interpreter, hosted shell, apply patch, computer use, MCP, and other tools.

## 📁 Project Structure

```text
ULTRON-AI/
<<<<<<< HEAD
├── ai/                    # AI providers, memory, and orchestration
├── core/
│   ├── agent/             # Planning, state, routing, verification, Astra
│   ├── brain/             # AI brain
│   ├── intent/            # Intent detection
│   ├── speech/            # Speech engine
│   └── tools/             # Tool execution registry
├── services/              # Service layer
├── tools/                 # Application tools
├── assistant_engine.py    # Main agent-aware runtime
├── main.py                # Entry point
├── run_ultron.py          # Runner
└── config.py              # Configuration
=======
├── ai/                    # AI package
│   ├── agents/            # AI provider agents (Gemini, OpenAI, DeepSeek)
│   ├── memory/            # Memory systems (conversation, session, vector)
│   └── orchestrator/      # AI orchestration (prompt, model, response, consensus)
├── core/                  # Core package
│   ├── agent/             # Agent runtime: planner, judgment, policy, recovery
│   ├── brain/             # AI brain (delegates to orchestrator)
│   ├── context/           # Self/world models, memory manager, long-term goals
│   ├── evolution/         # Hypothesis engine, experiments, strategy learning
│   ├── intent/            # Intent detection
│   ├── neural/            # Neural schema, entity/concept graphs, predictions
│   ├── speech/            # Speech engine wrapper
│   ├── tools/             # Canonical tool execution registry
│   └── update/            # Cryptographically verified self-update pipeline
├── backend/               # FastAPI gateway (REST + WebSocket) for remote clients
│   ├── api/routes/        # auth, chat, commands, devices, health, system
│   ├── security/          # Token service, authentication, authorization
│   ├── database/          # SQLite device/context persistence
│   ├── services/          # Brain adapter, command + confirmation services
│   └── tests/             # Gateway & phase test suites
├── mobile/                # Flutter companion app + native Android node
├── services/              # Service layer
├── tools/                 # Tools (app launcher)
├── assistant_engine.py    # Main assistant engine (CLI loop)
├── main.py                # CLI entry point
├── run_ultron.py          # Desktop voice+overlay entry point (PyQt6)
└── config.py              # Configuration re-export
>>>>>>> origin/main
```

## 🚀 Installation

```bash
git clone https://github.com/tagore1344/ULTRON-AI.git
cd ULTRON-AI
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add provider keys as required.

## 🎮 Usage

```bash
python run_ultron.py
```

Or on Windows:

```bash
start_ultron.bat
```

Once `OPENAI_API_KEY` is configured, a request such as:

```text
Build the missing feature, run the tests, fix any failures, and verify it.
```

can be handled as an autonomous software-engineering task instead of a single chat response.

## 🧪 Tests

Run the agent-core tests:

```bash
<<<<<<< HEAD
python -m pytest core/agent/test_agent_core.py
=======
py -m pytest            # Windows (full suite)
python3 -m pytest       # Linux / macOS

# Fast subset without network calls:
py -m pytest ai/test_orchestrator_activation.py backend/tests/test_phase2.py
>>>>>>> origin/main
```

A live Astra integration test should only be run in an environment with `OPENAI_API_KEY` and a disposable/test workspace.

## 🧠 AI Providers

<<<<<<< HEAD
| Provider | File | Role |
|----------|------|------|
| OpenAI | `ai/agents/openai_agent.py` | GPT-6 Astra reasoning |
| Gemini | `ai/agents/gemini_agent.py` | Compatibility/fallback |
| DeepSeek | `ai/agents/deepseek_agent.py` | Compatibility/fallback |

## 🔭 Roadmap toward Astra-class capability
=======
| Provider | File | Model | Role |
|----------|------|-------|------|
| Gemini | `ai/agents/gemini_agent.py` | gemini-2.5-flash | Coding / math / technical |
| OpenAI | `ai/agents/openai_agent.py` | gpt-4.1-mini | General conversation |
| DeepSeek | `ai/agents/deepseek_agent.py` | deepseek-chat | Cybersecurity / reasoning |

Gemini uses the modern `google-genai` SDK by default with a graceful fallback to
the legacy `google-generativeai` backend. Set `ULTRON_GEMINI_SDK=legacy` to force
the fallback. OpenAI and DeepSeek use the OpenAI-compatible client (`openai`
package); DeepSeek points at `https://api.deepseek.com` automatically.

The `AIOrchestrator` routes each prompt to the best-suited provider via
`ModelSelector`, then automatically cascades through remaining providers when
the primary fails or its API key is missing (failure-aware fallback chain).

### Consensus modes

Set `ULTRON_CONSENSUS_MODE` in `.env`:

* `fallback` *(default)* — one strategic provider answers per request; failed or
  unconfigured providers are skipped gracefully.
* `multi` — every available provider answers; responses are merged by the
  `ResponseMerger` and consolidated by the `ConsensusEngine`.

Availability probes (`is_*_available()` in each agent) check provider setup
without network calls, so missing keys never crash the assistant.
>>>>>>> origin/main

1. **Agent Core — implemented:** planner, task state, model routing, verification, bounded retries.
2. **Autonomous coding — implemented foundation:** workspace inspection, file editing, terminal/test execution, Git status/diff/commit, iterative tool calls.
3. **Persistent agent memory:** project knowledge, episodic execution history, searchable task notes, context compaction.
4. **Computer-use agent:** screen observation, mouse/keyboard actions, application workflows, browser QA.
5. **Specialist agents:** architect, coder, tester, researcher, reviewer with shared task state.
6. **Evaluation harness:** benchmark ULTRON on coding, browser, computer-use, research, and recovery tasks.
7. **Improvement lab:** benchmark → propose change → sandbox → verify → human approval → deploy.

ULTRON is an agent system, not a recreation of the GPT-6 Astra foundation model. Matching Astra's underlying intelligence would require frontier-scale model training; the practical path is to make ULTRON an Astra-class orchestration, tool-use, memory, verification, and computer-control system around strong models.

The improvement lab remains sandboxed and approval-gated. Autonomous execution is powerful, but production deployment and self-modification must remain explicitly controlled.

## 📄 License

This project is for personal/educational use.
