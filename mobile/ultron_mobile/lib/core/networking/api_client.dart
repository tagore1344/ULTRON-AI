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
    final Map<String, String> headers = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };

    final token = await storage.loadToken();
    if (token != null && token.isNotEmpty) {
      headers["Authorization"] = "Bearer $token";
    }
    return headers;
  }

  /// REST GET Request helper
  Future<dynamic> get(String path) async {
    final url = Uri.parse("${config.restBaseUrl}$path");
    final headers = await _headers();

    try {
      final response = await _client.get(url, headers: headers).timeout(const Duration(seconds: 10));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  /// REST POST Request helper
  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final url = Uri.parse("${config.restBaseUrl}$path");
    final headers = await _headers();
    final jsonBody = json.encode(body);

    try {
      final response = await _client.post(url, headers: headers, body: jsonBody).timeout(const Duration(seconds: 10));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  /// REST DELETE Request helper
  Future<dynamic> delete(String path) async {
    final url = Uri.parse("${config.restBaseUrl}$path");
    final headers = await _headers();

    try {
      final response = await _client.delete(url, headers: headers).timeout(const Duration(seconds: 10));
      return _processResponse(response);
    } catch (e) {
      throw _handleNetworkError(e);
    }
  }

  dynamic _processResponse(http.Response response) {
    final statusCode = response.statusCode;
    final bodyString = response.body;

    Map<String, dynamic> body = {};
    if (bodyString.isNotEmpty) {
      try {
        body = json.decode(bodyString);
      } catch (_) {}
    }

    if (statusCode >= 200 && statusCode < 300) {
      return body;
    }

    // Process structured backend errors safely without disclosure of raw trace paths
    final errorObj = body["error"] ?? {};
    final errorCode = errorObj["code"] ?? "HTTP_ERROR";
    final errorMessage = errorObj["message"] ?? "Server returned error code: $statusCode";

    if (statusCode == 401) {
      throw UnauthorizedException(errorCode, errorMessage);
    } else if (statusCode == 403) {
      throw ForbiddenException(errorCode, errorMessage);
    } else {
      throw ApiException(errorCode, errorMessage);
    }
  }

  Exception _handleNetworkError(dynamic e) {
    if (e is SocketException) {
      return NetworkOfflineException("NETWORK_OFFLINE", "Cannot connect to ULTRON laptop. Verify same Wi-Fi connection.");
    }
    return ApiException("GATEWAY_ANOMALY", "Communication failed: $e");
  }

  void dispose() {
    _client.close();
  }
}

// Custom Exception Models
class ApiException implements Exception {
  final String code;
  final String message;
  ApiException(this.code, this.message);
  @override
  String toString() => "[$code] $message";
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
