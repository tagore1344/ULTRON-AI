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

  /// Send a text message to AIBrain statefully
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // 1. Add user message to local UI list
    _addMessage(ChatMessage(
      text: text.trim(),
      isUser: true,
      timestamp: DateTime.now(),
    ));

    _isLoading = true;
    notifyListeners();

    try {
      // 2. Dispatch to backend AI gateway REST route
      final response = await apiClient.post("/chat", {
        "message": text.trim(),
        "conversation_id": _conversationId,
      });

      _isLoading = false;

      final bool success = response["success"] ?? false;
      if (success) {
        _conversationId = response["conversation_id"];
        final String aiReply = response["response"];

        // 3. Add AI reply to local UI list
        _addMessage(ChatMessage(
          text: aiReply,
          isUser: false,
          timestamp: DateTime.now(),
        ));
      } else {
        _addErrorResponse("ULTRON Core was unable to complete reasoning.");
      }
    } catch (e) {
      _isLoading = false;
      _addErrorResponse("ULTRON is currently offline: ${e.toString()}");
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

  /// Clear messages list locally without affecting server persistent registries
  void clearMessages() {
    _messages.clear();
    _conversationId = null;
    notifyListeners();
  }
}
