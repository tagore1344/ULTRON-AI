// mobile/ultron_mobile/lib/features/chat/chat_controller.dart
import 'package:flutter/material.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/features/chat/chat_message.dart';

class ChatController extends ChangeNotifier {
  final ApiClient apiClient;

  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _conversationId;

  ChatController({required this.apiClient});

  List<ChatMessage> get messages => _messages;
  bool get isLoading => _isLoading;
  String? get conversationId => _conversationId;

  /// Sends a message to TAG and returns the assistant reply for voice/UI clients.
  Future<String?> sendMessage(String text) async {
    if (text.trim().isEmpty) return null;

    _addMessage(ChatMessage(
      text: text.trim(),
      isUser: true,
      timestamp: DateTime.now(),
    ));

    _isLoading = true;
    notifyListeners();

    try {
      final response = await apiClient.post("/chat", {
        "message": text.trim(),
        "conversation_id": _conversationId,
      });

      _isLoading = false;

      final bool success = response["success"] ?? false;
      if (success) {
        _conversationId = response["conversation_id"];
        final String aiReply = (response["response"] ?? '').toString();
        _addMessage(ChatMessage(
          text: aiReply,
          isUser: false,
          timestamp: DateTime.now(),
        ));
        return aiReply;
      }

      const fallback = "TAG Core was unable to complete reasoning.";
      _addErrorResponse(fallback);
      return fallback;
    } catch (e) {
      _isLoading = false;
      const fallback = "TAG is currently offline.";
      _addErrorResponse(fallback);
      throw ApiException("VOICE_GATEWAY_OFFLINE", "$fallback $e");
    }
  }

  void _addMessage(ChatMessage msg) {
    _messages.add(msg);
    notifyListeners();
  }

  void _addErrorResponse(String errorText) {
    _messages.add(ChatMessage(
      text: errorText,
      isUser: false,
      timestamp: DateTime.now(),
    ));
    notifyListeners();
  }

  void clearMessages() {
    _messages.clear();
    _conversationId = null;
    notifyListeners();
  }
}
