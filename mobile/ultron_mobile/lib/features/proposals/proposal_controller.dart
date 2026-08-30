// mobile/ultron_mobile/lib/features/proposals/proposal_controller.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:ultron_mobile/core/models/event.dart';
import 'package:ultron_mobile/core/models/proposal.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/core/networking/websocket_service.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;

enum ProposalLoadState { loading, ready, error }

/// Tracks cognitive change-proposals from the gateway and live WS updates.
///
/// Graceful degradation: if the socket drops, the controller re-fetches the
/// full ledger from REST when the connection controller reports reconnect.
class ProposalController extends ChangeNotifier {
  final ApiClient apiClient;
  final WebSocketService wsService;
  final ultron.ConnectionController connection;
  StreamSubscription<WsEvent>? _wsSub;

  ProposalLoadState loadState = ProposalLoadState.loading;
  List<CognitiveProposal> proposals = [];
  String? lastExecutionDetail;
  String? errorMessage;

  bool _disposed = false;
  ultron.ConnectionState _lastKnownState = ultron.ConnectionState.disconnected;

  ProposalController({
    required this.apiClient,
    required this.wsService,
    required this.connection,
  }) {
    _wsSub = wsService.eventStream.listen(_onWsEvent);
    // ChangeNotifier exposes no stream; bridge listener callbacks manually.
    connection.addListener(_onConnectionTick);
    _lastKnownState = connection.state;
    refresh();
  }

  void _onConnectionTick() {
    final state = connection.state;
    if (state != _lastKnownState) {
      _lastKnownState = state;
      // After a reconnect, REST re-fetch heals any missed WS events.
      if (state == ultron.ConnectionState.connected) {
        refresh();
      }
    }
  }

  void _onWsEvent(WsEvent event) {
    switch (event.event) {
      case 'PROPOSAL_CREATED':
        final raw = event.data['proposal'];
        if (raw is Map) {
          _upsert(CognitiveProposal.fromJson(Map<String, dynamic>.from(raw)));
        }
        break;
      case 'PROPOSAL_RESOLVED':
        _markResolved(event.data['proposal_id'], event.data['status']);
        break;
      case 'PROPOSAL_EXECUTION_RESULT':
        lastExecutionDetail =
            "${event.data['success'] == true ? 'APPLIED' : 'FAILED'}: ${event.data['detail'] ?? ''}";
        refresh();
        break;
      case 'PROPOSAL_EXPIRED':
        _markResolved(event.data['proposal_id'], 'EXPIRED');
        break;
    }
  }

  void _upsert(CognitiveProposal proposal) {
    final index = proposals.indexWhere((p) => p.proposalId == proposal.proposalId);
    if (index >= 0) {
      proposals[index] = proposal;
    } else {
      proposals.insert(0, proposal);
    }
    _notify();
  }

  void _markResolved(dynamic pid, dynamic status) {
    if (pid is! String || status is! String) return;
    final index = proposals.indexWhere((p) => p.proposalId == pid);
    if (index >= 0) {
      final old = proposals[index];
      proposals[index] = CognitiveProposal(
        proposalId: old.proposalId,
        title: old.title,
        reason: old.reason,
        component: old.component,
        risk: old.risk,
        expectedImpact: old.expectedImpact,
        proposedAction: old.proposedAction,
        status: status,
        createdAt: old.createdAt,
        resolvedAt: old.resolvedAt,
        resolvedBy: old.resolvedBy,
        resolutionNote: old.resolutionNote,
        payload: old.payload,
      );
      _notify();
    }
  }

  /// Pulls the authoritative proposal ledger from the gateway.
  Future<void> refresh() async {
    loadState = ProposalLoadState.loading;
    _notify();

    try {
      final response = await apiClient.get("/cognitive/proposals");
      final list = response['proposals'] as List<dynamic>? ?? [];
      proposals = list
          .whereType<Map>()
          .map((raw) => CognitiveProposal.fromJson(Map<String, dynamic>.from(raw)))
          .toList();
      loadState = ProposalLoadState.ready;
      errorMessage = null;
    } catch (e) {
      loadState = ProposalLoadState.error;
      errorMessage = e.toString();
    }
    _notify();
  }

  /// Submits an approval. Returns the execution outcome message for the HUD.
  Future<String> approve(String proposalId) async {
    final response = await apiClient.post(
      "/cognitive/proposals/$proposalId/decision",
      {"decision": "approved"},
    );
    await refresh();
    final execution = response['execution'];
    if (execution is Map) {
      final success = execution['success'] == true;
      return success
          ? "Applied: ${execution['detail'] ?? ''}"
          : "Blocked: ${execution['detail'] ?? execution['status'] ?? 'unknown'}";
    }
    return "Resolved";
  }

  /// Submits a rejection.
  Future<void> reject(String proposalId) async {
    await apiClient.post(
      "/cognitive/proposals/$proposalId/decision",
      {"decision": "rejected"},
    );
    await refresh();
  }

  /// Cancels a still-pending proposal.
  Future<void> cancel(String proposalId) async {
    await apiClient.post("/cognitive/proposals/$proposalId/cancel", {});
    await refresh();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    connection.removeListener(_onConnectionTick);
    _wsSub?.cancel();
    super.dispose();
  }
}