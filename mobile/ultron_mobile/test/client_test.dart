// mobile/ultron_mobile/test/client_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:ultron_mobile/core/models/event.dart';
import 'package:ultron_mobile/core/models/device.dart';

void main() {
  group('ULTRON Model Parsing Unit Tests', () {
    test('Verify WsEvent parses correctly from WebSocket JSON envelopes', () {
      final jsonPayload = {
        "event": "CONNECTION_ESTABLISHED",
        "event_id": "evt_abc123",
        "timestamp": "2026-08-11T12:00:00Z",
        "device_id": "android_123",
        "data": {
          "message": "Handshake successful"
        }
      };

      final event = WsEvent.fromJson(jsonPayload);
      
      assert(event.event == "CONNECTION_ESTABLISHED");
      assert(event.eventId == "evt_abc123");
      assert(event.timestamp == "2026-08-11T12:00:00Z");
      assert(event.deviceId == "android_123");
      assert(event.data["message"] == "Handshake successful");
    });

    test('Verify Device parses successfully from registry database payloads', () {
      final jsonPayload = {
        "device_id": "android_981aef",
        "device_name": "Tag's Android",
        "device_type": "android",
        "permissions": ["chat", "system_status"],
        "paired_at": "2026-08-11T11:00:00Z",
        "last_seen": "2026-08-11T11:55:00Z",
        "revoked": false
      };

      final device = Device.fromJson(jsonPayload);

      assert(device.deviceId == "android_981aef");
      assert(device.deviceName == "Tag's Android");
      assert(device.deviceType == "android");
      assert(device.permissions.contains("chat"));
      assert(device.permissions.contains("system_status"));
      assert(device.revoked == false);
    });
  });
}
