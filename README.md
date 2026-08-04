# ULTRON AI

An advanced AI assistant application built with Python. ULTRON AI features voice interaction, screen vision, system automation, and multi-provider AI support (Gemini, OpenAI, DeepSeek).

## ✨ Features

- **Voice Interaction** — Speech-to-text (Faster-Whisper) and text-to-speech (pyttsx3)
- **Multi-Provider AI** — Gemini, OpenAI, and DeepSeek agents with an AI orchestrator
- **Screen Vision** — Capture and analyze screen content with OCR
- **System Automation** — Control volume, brightness, media, power, and more
- **Memory System** — Conversation, session, and vector memory for context
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
│   ├── brain/             # AI brain (delegates to orchestrator)
│   ├── intent/            # Intent detection
│   ├── speech/            # Speech engine wrapper
│   └── tools/             # Tool execution registry
├── services/              # Service layer
│   ├── ai_service.py      # AI service
│   ├── speech_service.py  # Speech service
│   ├── vision_service.py  # Vision service
│   └── automation_service.py  # System automation service
├── tools/                 # Tools
│   └── app_launcher.py    # App launcher
├── assistant_engine.py    # Main assistant engine
├── main.py                # Entry point
├── run_ultron.py          # Runner script
└── config.py              # Configuration
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
python -m pytest ai/test_orchestrator.py ai/test_router.py ai/test_gemini.py test_app_controller.py
```

## 🧠 AI Providers

| Provider | File | Model |
|----------|------|-------|
| Gemini | `ai/agents/gemini_agent.py` | gemini-2.5-flash |
| OpenAI | `ai/agents/openai_agent.py` | (configurable) |
| DeepSeek | `ai/agents/deepseek_agent.py` | (configurable) |

The `AIOrchestrator` selects the best provider based on the prompt content and merges responses.

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