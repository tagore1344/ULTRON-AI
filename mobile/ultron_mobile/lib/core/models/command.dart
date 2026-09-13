// mobile/ultron_mobile/lib/core/models/command.dart

class CommandResult {
  final bool success;
  final String commandId;
  final String status;
  final String? message;
  final dynamic responsePayload;

  CommandResult({
    required this.success,
    required this.commandId,
    required this.status,
    this.message,
    this.responsePayload,
  });

  factory CommandResult.fromJson(Map<String, dynamic> json) {
    final resultObj = json['result'] ?? {};
    final errorObj = json['error'] ?? {};

    return CommandResult(
      success: json['success'] ?? false,
      commandId: json['command_id'] ?? '',
      status: json['status'] ?? 'rejected',
      message: resultObj['message'] ?? errorObj['message'],
      responsePayload: resultObj['response'],
    );
  }
}
