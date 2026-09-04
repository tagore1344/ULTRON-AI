# ULTRON AI

An advanced AI assistant application built with Python. ULTRON AI features voice interaction, screen vision, system automation, multi-provider AI, persistent memory, and an agent execution foundation.

## ✨ Features

- **Voice Interaction** — Speech-to-text (Faster-Whisper) and text-to-speech (pyttsx3)
- **Multi-Provider AI** — Gemini, OpenAI, and DeepSeek agents with an AI orchestrator
- **Agent Execution** — Goal decomposition, task state, execution, verification, and bounded retries
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

Complex requests now enter an explicit loop instead of going directly from prompt to response:

```text
Goal
  ↓
Plan
  ↓
Task State
  ↓
Execute
  ↓
Observe result
  ↓
Verify
  ↓
Complete / Retry / Fail
```

The agent layer is model-agnostic. It can sit above the existing Gemini/OpenAI/DeepSeek providers and can later route work to local or specialist models.

### Agent modules

```text
core/agent/
├── __init__.py
├── task_state.py          # Serializable task state and execution history
├── planner.py             # Goal → explicit steps
├── model_router.py        # Capability-based model selection
├── verifier.py            # Output verification primitives
├── agent_loop.py          # Synchronous execution core
├── async_agent_loop.py    # Existing ULTRON tools + async agent execution
└── test_agent_core.py     # Agent-core tests
```

`AssistantEngine` remains the entry point. Existing direct tool intents continue to use the existing ToolRegistry, while complex chat goals are routed through the agent loop.

## 📁 Project Structure

```text
ULTRON-AI/
├── ai/                    # AI providers, memory, and orchestration
├── core/
│   ├── agent/             # Planning, state, routing, verification
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

## 🧪 Tests

Run the existing tests plus the new agent-core coverage:

```bash
python -m pytest core/agent/test_agent_core.py
```

## 🧠 AI Providers

| Provider | File | Model |
|----------|------|-------|
| Gemini | `ai/agents/gemini_agent.py` | gemini-2.5-flash |
| OpenAI | `ai/agents/openai_agent.py` | configurable |
| DeepSeek | `ai/agents/deepseek_agent.py` | configurable |

The existing `AIOrchestrator` remains intact. The new agent layer is an orchestration layer above it, preserving the project's current architecture rather than replacing it.

## 🔭 Roadmap toward a frontier-style agent

1. **Agent Core — implemented:** planner, task state, model router, verification, bounded retry loop.
2. **Real coding agent:** repository inspection, terminal execution, tests, patching, debugging, and Git workflows.
3. **Persistent agent memory:** project knowledge, episodic execution history, and searchable task notes.
4. **Computer-use agent:** screen observation, mouse/keyboard actions, and application workflows.
5. **Multi-agent system:** architect, coder, tester, researcher, and reviewer roles.
6. **Improvement lab:** benchmark → propose change → sandbox → verify → human approval → deploy.

The improvement lab must remain sandboxed and approval-gated; ULTRON should not silently rewrite and deploy its own production code.

## 📄 License

This project is for personal/educational use.
