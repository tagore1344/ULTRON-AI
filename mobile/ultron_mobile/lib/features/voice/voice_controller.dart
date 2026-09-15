import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:ultron_mobile/features/chat/chat_controller.dart';

/// Siri-style voice orchestration for TAG Mobile.
/// Speech recognition is device-native; reasoning remains on the TAG gateway.
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
      onError: (error) {
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
      _status = 'READY';
      notifyListeners();
      if (_handsFree) {
        Future<void>.delayed(const Duration(milliseconds: 350), () => startListening());
      }
    });
    _tts.setCancelHandler(() {
      _speaking = false;
      _status = 'READY';
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
    _status = 'LISTENING';
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
      await startListening();
    } else if (_listening) {
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
    _transcript = result.recognizedWords.trim();
    notifyListeners();

    if (result.finalResult && !_submitting) {
      _listening = false;
      _status = 'THINKING';
      notifyListeners();
      _submitTranscript();
    }
  }

  void _onSpeechStatus(String status) {
    if (status == 'done' && _listening) {
      _listening = false;
      if (!_submitting && _transcript.trim().isNotEmpty) {
        _status = 'THINKING';
        notifyListeners();
        _submitTranscript();
      } else {
        _status = 'READY';
        notifyListeners();
      }
    }
  }

  Future<void> _submitTranscript() async {
    final text = _transcript.trim();
    if (text.isEmpty || _submitting) return;

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
        _status = 'READY';
        notifyListeners();
      }
    } catch (_) {
      _thinking = false;
      _status = 'GATEWAY OFFLINE';
      notifyListeners();
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
