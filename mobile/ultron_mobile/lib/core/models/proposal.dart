// mobile/ultron_mobile/lib/core/models/proposal.dart

/// Risk taxonomy — mirrors the gateway command classification exactly.
enum ProposalRisk { safe, confirmationRequired, highRisk, unknown }

ProposalRisk proposalRiskFromString(String? raw) {
  switch (raw) {
    case 'SAFE':
      return ProposalRisk.safe;
    case 'CONFIRMATION_REQUIRED':
      return ProposalRisk.confirmationRequired;
    case 'HIGH_RISK':
      return ProposalRisk.highRisk;
    default:
      return ProposalRisk.unknown;
  }
}

extension ProposalRiskX on ProposalRisk {
  String get label {
    switch (this) {
      case ProposalRisk.safe:
        return 'SAFE';
      case ProposalRisk.confirmationRequired:
        return 'CONFIRM';
      case ProposalRisk.highRisk:
        return 'HIGH_RISK';
      case ProposalRisk.unknown:
        return 'UNKNOWN';
    }
  }
}

/// A cognitive change-proposal surfaced by ULTRON for human review (Phase 9E).
class CognitiveProposal {
  final String proposalId;
  final String title;
  final String reason;
  final String component;
  final ProposalRisk risk;
  final String expectedImpact;
  final String proposedAction;
  final String status;
  final String createdAt;
  final String? resolvedAt;
  final String? resolvedBy;
  final String? resolutionNote;
  final Map<String, dynamic> payload;

  const CognitiveProposal({
    required this.proposalId,
    required this.title,
    required this.reason,
    required this.component,
    required this.risk,
    required this.expectedImpact,
    required this.proposedAction,
    required this.status,
    required this.createdAt,
    this.resolvedAt,
    this.resolvedBy,
    this.resolutionNote,
    required this.payload,
  });

  bool get isPending =>
      status == 'PENDING_REVIEW' || status == 'AWAITING_APPROVAL';

  factory CognitiveProposal.fromJson(Map<String, dynamic> json) {
    return CognitiveProposal(
      proposalId: json['proposal_id'] ?? '',
      title: json['title'] ?? '',
      reason: json['reason'] ?? '',
      component: json['component'] ?? '',
      risk: proposalRiskFromString(json['risk_class']),
      expectedImpact: json['expected_impact'] ?? '',
      proposedAction: json['proposed_action'] ?? '',
      status: json['status'] ?? '',
      createdAt: json['created_at'] ?? '',
      resolvedAt: json['resolved_at'],
      resolvedBy: json['resolved_by'],
      resolutionNote: json['resolution_note'],
      payload: Map<String, dynamic>.from(json['payload'] ?? {}),
    );
  }
}