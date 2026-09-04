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
python -m pytest core/agent/test_agent_core.py
```

A live Astra integration test should only be run in an environment with `OPENAI_API_KEY` and a disposable/test workspace.

## 🧠 AI Providers

| Provider | File | Role |
|----------|------|------|
| OpenAI | `ai/agents/openai_agent.py` | GPT-6 Astra reasoning |
| Gemini | `ai/agents/gemini_agent.py` | Compatibility/fallback |
| DeepSeek | `ai/agents/deepseek_agent.py` | Compatibility/fallback |

## 🔭 Roadmap toward Astra-class capability

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
