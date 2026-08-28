# ULTRON AI

An advanced AI assistant application built with Python. ULTRON AI features voice interaction, screen vision, system automation, and multi-provider AI support (Gemini, OpenAI, DeepSeek).

## ✨ Features

- **Voice Interaction** — Speech-to-text (Faster-Whisper) and text-to-speech (pyttsx3)
- **Multi-Provider AI** — Gemini, OpenAI, and DeepSeek agents with an AI orchestrator
- **Screen Vision** — Capture and analyze screen content with OCR
- **System Automation** — Control volume, brightness, media, power, and more
- **Memory System** — Conversation, session, and vector memory for context
- **Cognitive Proposals (Phase 9E)** — ULTRON surfaces change-proposals to your phone for review/approval (see `docs/PHASE_9E.md`)
- **Intent Routing** — Rule-based intent detection for tool execution
- **Wake Word Detection** — Activate with "Hey ULTRON"
- **Face ID & Voice ID** — Advanced identity verification
- **GPU Acceleration** — Optional GPU support for AI models
- **Transparent Overlay UI** — On-screen assistant interface

## 📁 Project Structure

```
ULTRON-AI/
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
```

## 🚀 Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/tagore1344/ULTRON-AI.git
cd ULTRON-AI

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your API keys to .env:
# GEMINI_API_KEY=your_gemini_key
# OPENAI_API_KEY=your_openai_key
# DEEPSEEK_API_KEY=your_deepseek_key
```

## 🎮 Usage

### Run the assistant

```bash
python run_ultron.py
```

Or on Windows:

```bash
start_ultron.bat
```

### Run tests

```bash
py -m pytest            # Windows (full suite)
python3 -m pytest       # Linux / macOS

# Fast subset without network calls:
py -m pytest ai/test_orchestrator_activation.py backend/tests/test_phase2.py
```

## 🧠 AI Providers

| Provider | File | Model | Role |
|----------|------|-------|------|
| Gemini | `ai/agents/gemini_agent.py` | gemini-2.5-flash | Coding / math / technical |
| OpenAI | `ai/agents/openai_agent.py` | gpt-4.1-mini | General conversation |
| DeepSeek | `ai/agents/deepseek_agent.py` | deepseek-chat | Cybersecurity / reasoning |

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

## 🛠️ Configuration

Configuration is stored in `assistant_config.json` (auto-created on first run). Key settings:

- `assistant_name` — Assistant display name
- `wake_words` — Wake word phrases
- `whisper_model` — STT model size
- `voice_speed` / `voice_volume` — TTS settings
- `use_gpu` — Enable GPU acceleration
- `theme` / `accent_color` — Overlay UI appearance

## 📦 Dependencies

- `google-generativeai` — Gemini API
- `openai` — OpenAI API
- `faster-whisper` — Speech-to-text
- `pyttsx3` — Text-to-speech
- `pyautogui` — Screen capture & automation
- `pytesseract` — OCR
- `psutil` — System monitoring
- `numpy` — Numerical operations
- `pyaudio` — Audio capture

## 📄 License

This project is for personal/educational use.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request