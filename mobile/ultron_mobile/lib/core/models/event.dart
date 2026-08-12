// mobile/ultron_mobile/lib/core/models/event.dart

class WsEvent {
  final String event;
  final String eventId;
  final String timestamp;
  final String? deviceId;
  final String? commandId;
  final String? requestId;
  final Map<String, dynamic> data;

  WsEvent({
    required this.event,
    required this.eventId,
    required this.timestamp,
    this.deviceId,
    this.commandId,
    this.requestId,
    required this.data,
  });

  factory WsEvent.fromJson(Map<String, dynamic> json) {
    return WsEvent(
      event: json['event'] ?? '',
      eventId: json['event_id'] ?? '',
      timestamp: json['timestamp'] ?? '',
      deviceId: json['device_id'],
      commandId: json['command_id'],
      requestId: json['request_id'],
      data: Map<String, dynamic>.from(json['data'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'event': event,
      'event_id': eventId,
      'timestamp': timestamp,
      'device_id': deviceId,
      'command_id': commandId,
      'request_id': requestId,
      'data': data,
    };
  }
}
