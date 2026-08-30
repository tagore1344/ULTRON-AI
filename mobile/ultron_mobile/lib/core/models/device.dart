// mobile/ultron_mobile/lib/core/models/device.dart

class Device {
  final String deviceId;
  final String deviceName;
  final String deviceType;
  final List<String> permissions;
  final String pairedAt;
  final String lastSeen;
  final bool revoked;

  Device({
    required this.deviceId,
    required this.deviceName,
    required this.deviceType,
    required this.permissions,
    required this.pairedAt,
    required this.lastSeen,
    required this.revoked,
  });

  factory Device.fromJson(Map<String, dynamic> json) {
    return Device(
      deviceId: json['device_id'] ?? '',
      deviceName: json['device_name'] ?? '',
      deviceType: json['device_type'] ?? '',
      permissions: List<String>.from(json['permissions'] ?? []),
      pairedAt: json['paired_at'] ?? '',
      lastSeen: json['last_seen'] ?? '',
      revoked: json['revoked'] ?? false,
    );
  }
}
