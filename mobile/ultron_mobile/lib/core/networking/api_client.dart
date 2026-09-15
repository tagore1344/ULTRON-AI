// mobile/ultron_mobile/lib/core/networking/api_client.dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:ultron_mobile/core/config/app_config.dart';
import 'package:ultron_mobile/core/storage/secure_storage_service.dart';

class ApiClient {
  final AppConfig config;
  final SecureStorageService storage;
  final http.Client _client;

  ApiClient({required this.config, required this.storage}) : _client = http.Client();

  Future<Map<String, String>> _headers() async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final token = await storage.loadToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<dynamic> get(String path) async {
    final url = Uri.parse('${config.restBaseUrl}$path');
    final headers = await _headers();
    try {
      final response = await _client
          .get(url, headers: headers)
          .timeout(const Duration(seconds: 10));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final url = Uri.parse('${config.restBaseUrl}$path');
    final headers = await _headers();
    try {
      final response = await _client
          .post(url, headers: headers, body: json.encode(body))
          .timeout(const Duration(seconds: 20));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  Future<dynamic> delete(String path) async {
    final url = Uri.parse('${config.restBaseUrl}$path');
    final headers = await _headers();
    try {
      final response = await _client
          .delete(url, headers: headers)
          .timeout(const Duration(seconds: 10));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  dynamic _processResponse(http.Response response) {
    Map<String, dynamic> body = {};
    if (response.body.isNotEmpty) {
      try {
        final decoded = json.decode(response.body);
        if (decoded is Map<String, dynamic>) body = decoded;
      } catch (_) {}
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }

    final errorObj = body['error'];
    final errorMap = errorObj is Map ? Map<String, dynamic>.from(errorObj) : <String, dynamic>{};
    final code = (errorMap['code'] ?? 'HTTP_ERROR').toString();
    final message = (errorMap['message'] ?? 'Server returned error code: ${response.statusCode}').toString();

    if (response.statusCode == 401) throw UnauthorizedException(code, message);
    if (response.statusCode == 403) throw ForbiddenException(code, message);
    throw ApiException(code, message);
  }

  Exception _handleNetworkError(dynamic error) {
    if (error is SocketException) {
      return NetworkOfflineException(
        'NETWORK_OFFLINE',
        'Cannot connect to TAG gateway. Verify the phone and TAG host are reachable.',
      );
    }
    return ApiException('GATEWAY_ANOMALY', 'Communication failed: $error');
  }

  void dispose() => _client.close();
}

class ApiException implements Exception {
  final String code;
  final String message;
  ApiException(this.code, this.message);
  @override
  String toString() => '[$code] $message';
}

class UnauthorizedException extends ApiException {
  UnauthorizedException(super.code, super.message);
}

class ForbiddenException extends ApiException {
  ForbiddenException(super.code, super.message);
}

class NetworkOfflineException extends ApiException {
  NetworkOfflineException(super.code, super.message);
}
