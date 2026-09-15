import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:ultron_mobile/features/chat/chat_controller.dart';

/// Siri-style voice orchestration for TAG Mobile.
/// Device speech handles recognition/playback; the paired TAG gateway handles reasoning.
class VoiceController extends ChangeNotifier {
  final ChatController chat;
  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();

  bool _initialized = false;
  bool _listening = false;
  bool _thinking = false;
  bool _speaking = false;
  bool _handsFree = false;
  String _status = 'READY';
  String _transcript = '';
  String _lastReply = '';
  double _soundLevel = 0;
  bool _submitting = false;

  VoiceController({required this.chat});

  bool get initialized => _initialized;
  bool get listening => _listening;
  bool get thinking => _thinking;
  bool get speaking => _speaking;
  bool get handsFree => _handsFree;
  String get status => _status;
  String get transcript => _transcript;
  String get lastReply => _lastReply;
  double get soundLevel => _soundLevel;

  Future<void> initialize() async {
    if (_initialized) return;

    final available = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (_) {
        _status = 'MIC ERROR';
        _listening = false;
        notifyListeners();
      },
    );

    await _tts.setLanguage('en-IN');
    await _tts.setSpeechRate(0.47);
    await _tts.setSpeechVolume(1.0);
    await _tts.setSpeechPitch(0.98);
    _tts.setStartHandler(() {
      _speaking = true;
      _status = 'SPEAKING';
      notifyListeners();
    });
    _tts.setCompletionHandler(() {
      _speaking = false;
      _status = _handsFree ? 'WAITING FOR TAG' : 'READY';
      notifyListeners();
      if (_handsFree) {
        Future<void>.delayed(
          const Duration(milliseconds: 350),
          startListening,
        );
      }
    });
    _tts.setCancelHandler(() {
      _speaking = false;
      _status = _handsFree ? 'WAITING FOR TAG' : 'READY';
      notifyListeners();
    });
    _tts.setErrorHandler((_) {
      _speaking = false;
      _status = 'READY';
      notifyListeners();
    });

    _initialized = available;
    _status = available ? 'READY' : 'VOICE UNAVAILABLE';
    notifyListeners();
  }

  Future<void> startListening() async {
    await initialize();
    if (!_initialized || _listening || _thinking || _speaking) return;

    _transcript = '';
    _soundLevel = 0;
    _listening = true;
    _status = _handsFree ? 'WAITING FOR TAG' : 'LISTENING';
    notifyListeners();

    await _speech.listen(
      onResult: _onSpeechResult,
      onSoundLevelChange: (level) {
        _soundLevel = level;
        notifyListeners();
      },
      listenOptions: SpeechListenOptions(
        partialResults: true,
        onDevice: false,
        listenMode: ListenMode.dictation,
        autoPunctuation: true,
        pauseFor: const Duration(seconds: 2),
        listenFor: const Duration(seconds: 20),
      ),
    );
  }

  Future<void> stopListening() async {
    if (!_listening) return;
    _handsFree = false;
    await _speech.stop();
    _listening = false;
    _status = 'READY';
    notifyListeners();
    await _submitTranscript();
  }

  Future<void> toggleListening() async {
    if (_listening) {
      await stopListening();
    } else {
      _handsFree = false;
      await startListening();
    }
  }

  Future<void> toggleHandsFree() async {
    _handsFree = !_handsFree;
    notifyListeners();
    if (_handsFree) {
      _status = 'WAITING FOR TAG';
      notifyListeners();
      await startListening();
    } else {
      await _speech.stop();
      _listening = false;
      _status = 'READY';
      notifyListeners();
    }
  }

  Future<void> speakLastReply() async {
    if (_lastReply.isNotEmpty) {
      await _tts.stop();
      await _tts.speak(_lastReply);
    }
  }

  Future<void> cancelSpeech() async {
    await _speech.stop();
    await _tts.stop();
    _listening = false;
    _thinking = false;
    _speaking = false;
    _handsFree = false;
    _status = 'READY';
    notifyListeners();
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    final recognized = result.recognizedWords.trim();
    _transcript = recognized;
    notifyListeners();

    if (!result.finalResult || _submitting) return;

    _listening = false;
    if (_handsFree && !_containsWakeWord(recognized)) {
      _transcript = '';
      _status = 'WAITING FOR TAG';
      notifyListeners();
      Future<void>.delayed(const Duration(milliseconds: 250), startListening);
      return;
    }

    _transcript = _stripWakeWord(recognized);
    _status = 'THINKING';
    notifyListeners();
    _submitTranscript();
  }

  void _onSpeechStatus(String status) {
    if (status != 'done' || !_listening) return;

    _listening = false;
    final text = _transcript.trim();
    if (text.isEmpty) {
      if (_handsFree) {
        _status = 'WAITING FOR TAG';
        notifyListeners();
        Future<void>.delayed(const Duration(milliseconds: 250), startListening);
      } else {
        _status = 'READY';
        notifyListeners();
      }
      return;
    }

    if (_handsFree && !_containsWakeWord(text)) {
      _transcript = '';
      _status = 'WAITING FOR TAG';
      notifyListeners();
      Future<void>.delayed(const Duration(milliseconds: 250), startListening);
      return;
    }

    _transcript = _stripWakeWord(text);
    _status = 'THINKING';
    notifyListeners();
    _submitTranscript();
  }

  bool _containsWakeWord(String text) {
    final normalized = text.toLowerCase().replaceAll(RegExp(r'[^a-z0-9 ]'), ' ');
    return normalized.contains('hey tag') ||
        normalized.contains('ok tag') ||
        normalized.contains('hi tag') ||
        RegExp(r'\btag\b').hasMatch(normalized);
  }

  String _stripWakeWord(String text) {
    return text
        .replaceFirst(RegExp(r'(?i)^\s*(hey|ok|hi)?\s*tag[, ]*'), '')
        .trim();
  }

  Future<void> _submitTranscript() async {
    final text = _transcript.trim();
    if (text.isEmpty || _submitting) {
      if (_handsFree && text.isEmpty) {
        Future<void>.delayed(const Duration(milliseconds: 250), startListening);
      }
      return;
    }

    _submitting = true;
    _thinking = true;
    _status = 'THINKING';
    notifyListeners();

    try {
      final reply = await chat.sendMessage(text);
      _lastReply = (reply ?? '').trim();
      _thinking = false;
      notifyListeners();

      if (_lastReply.isNotEmpty) {
        await _tts.stop();
        _status = 'SPEAKING';
        notifyListeners();
        await _tts.speak(_lastReply);
      } else {
        _status = _handsFree ? 'WAITING FOR TAG' : 'READY';
        notifyListeners();
        if (_handsFree) {
          Future<void>.delayed(const Duration(milliseconds: 350), startListening);
        }
      }
    } catch (_) {
      _thinking = false;
      _status = 'GATEWAY OFFLINE';
      notifyListeners();
      if (_handsFree) {
        Future<void>.delayed(const Duration(seconds: 2), startListening);
      }
    } finally {
      _submitting = false;
    }
  }

  @override
  void dispose() {
    _speech.stop();
    _tts.stop();
    super.dispose();
  }
}
