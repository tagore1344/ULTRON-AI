// mobile/ultron_mobile/lib/features/chat/chat_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/chat/chat_controller.dart';
import 'package:ultron_mobile/features/chat/chat_message.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();

  // Real Android Speech-to-Text Service Instance (Least Privilege Principle)
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  String _listeningStatus = "Tap Mic to Speak";

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _speech.stop();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _submitMessage(ChatController controller) async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    _textController.clear();
    await controller.sendMessage(text);
    _scrollToBottom();
  }

  /// Real Android local speech recognition using speech_to_text package
  void _triggerVoiceInput(ChatController controller) async {
    if (_isListening) {
      // If currently listening, stop and submit
      _speech.stop();
      setState(() {
        _isListening = false;
      });
      return;
    }

    try {
      // 1. Request microphone and service initialization statefully at runtime
      bool available = await _speech.initialize(
        onStatus: (status) {
          setState(() {
            if (status == "listening") {
              _listeningStatus = "Listening... Speak now";
            } else if (status == "notListening") {
              _isListening = false;
            }
          });
        },
        onError: (errorNotification) {
          setState(() {
            _isListening = false;
            _listeningStatus = "Voice unavailable: ${errorNotification.errorString}";
          });
        },
      );

      if (available) {
        setState(() {
          _isListening = true;
          _listeningStatus = "Initializing microphone...";
        });

        // 2. Begin listening. Translates speech to text locally on device
        _speech.listen(
          onResult: (result) {
            setState(() {
              _textController.text = result.recognizedWords;
            });
          },
          listenFor: const Duration(seconds: 10),
          pauseFor: const Duration(seconds: 3),
          cancelOnError: true,
          partialResults: true,
        );
      } else {
        setState(() {
          _listeningStatus = "Speech recognition is unavailable on this device.";
        });
      }
    } catch (e) {
      setState(() {
        _isListening = false;
        _listeningStatus = "Failed to initialize microphone: $e";
      });
    }
  }

  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Copied to clipboard")),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chatController = Provider.of<ChatController>(context);

    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "ULTRON COMM CHANNEL",
          style: TextStyle(fontFamily: 'Consolas', fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 1.5),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_sweep_outlined, color: UltronTheme.rubyRed),
            onPressed: () => chatController.clearMessages(),
          )
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Message List Area
            Expanded(
              child: chatController.messages.isEmpty
                  ? _buildEmptyState()
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.all(16),
                      itemCount: chatController.messages.length,
                      itemBuilder: (context, index) {
                        final msg = chatController.messages[index];
                        return _buildMessageBubble(msg);
                      },
                    ),
            ),

            if (chatController.isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8.0),
                child: Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(color: UltronTheme.cyanAccent, strokeWidth: 2),
                  ),
                ),
              ),

            // Real Voice Input Status Banner
            if (_isListening || _speech.isListening)
              Container(
                color: UltronTheme.spaceSurface,
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(color: UltronTheme.cyanAccent, strokeWidth: 1.5),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      _listeningStatus,
                      style: const TextStyle(fontFamily: 'Consolas', fontSize: 12, color: UltronTheme.cyanAccent),
                    ),
                  ],
                ),
              ),

            // Input Row Panel
            Container(
              padding: const EdgeInsets.all(16),
              color: UltronTheme.spaceSurface,
              child: Row(
                children: [
                  // Microphone Button
                  IconButton(
                    icon: Icon(
                      _isListening ? Icons.mic : Icons.mic_none,
                      color: _isListening ? UltronTheme.rubyRed : UltronTheme.cyanAccent,
                    ),
                    onPressed: () => _triggerVoiceInput(chatController),
                  ),
                  const SizedBox(width: 8),

                  // Text Field Box
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: const TextStyle(fontFamily: 'Inter', fontSize: 14),
                      decoration: const InputDecoration(
                        hintText: "Transmit secure prompt...",
                        hintStyle: TextStyle(color: UltronTheme.cleanGrey),
                        border: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        enabledBorder: InputBorder.none,
                      ),
                      onSubmitted: (_) => _submitMessage(chatController),
                    ),
                  ),

                  // Send Button
                  IconButton(
                    icon: const Icon(Icons.send_outlined, color: UltronTheme.cyanAccent),
                    onPressed: () => _submitMessage(chatController),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.chat_bubble_outline_rounded, size: 60, color: UltronTheme.cleanGrey.withOpacity(0.4)),
          const SizedBox(height: 16),
          const Text(
            "COMM LINK SECURED",
            style: TextStyle(fontFamily: 'Consolas', fontSize: 14, fontWeight: FontWeight.bold, color: UltronTheme.cyanAccent),
          ),
          const SizedBox(height: 8),
          const Text(
            "All messages travel over encrypted tunnels.",
            style: TextStyle(fontSize: 12, color: UltronTheme.cleanGrey),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage msg) {
    final isUser = msg.isUser;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onLongPress: () => _copyToClipboard(msg.text),
        child: Container(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: isUser ? UltronTheme.spaceSurface : UltronTheme.spaceSurface.withOpacity(0.5),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(12),
              topRight: const Radius.circular(12),
              bottomLeft: isUser ? const Radius.circular(12) : Radius.zero,
              bottomRight: isUser ? Radius.zero : const Radius.circular(12),
            ),
            border: Border.all(
              color: isUser ? UltronTheme.cyanAccent.withOpacity(0.2) : UltronTheme.cleanGrey.withOpacity(0.1),
              width: 0.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isUser ? "YOU" : "ULTRON",
                style: TextStyle(
                  fontFamily: 'Consolas',
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: isUser ? UltronTheme.cyanAccent : UltronTheme.cleanGrey,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                msg.text,
                style: const TextStyle(fontSize: 13, height: 1.4),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
