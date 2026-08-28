// mobile/ultron_mobile/test/proposal_model_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:ultron_mobile/core/models/proposal.dart';

void main() {
  test('CognitiveProposal parses gateway proposal payloads', () {
    final proposal = CognitiveProposal.fromJson({
      'proposal_id': 'prop_abc123',
      'title': 'Source change: voice_id.py',
      'reason': 'voice_id.py lacks dynamic thresholding',
      'component': 'voice_id.py',
      'risk_class': 'HIGH_RISK',
      'expected_impact': '0.02',
      'proposed_action': 'Authorize diff through the signed release pipeline.',
      'status': 'PENDING_REVIEW',
      'created_at': '2026-08-28T12:00:00Z',
      'payload': {'change_proposal': {'file': 'voice_id.py'}},
    });

    expect(proposal.proposalId, 'prop_abc123');
    expect(proposal.risk, ProposalRisk.highRisk);
    expect(proposal.isPending, isTrue);
    expect(proposal.payload['change_proposal']['file'], 'voice_id.py');
    expect(proposal.risk.label, 'HIGH_RISK');
  });

  test('risk classification maps all gateway classes', () {
    expect(proposalRiskFromString('SAFE'), ProposalRisk.safe);
    expect(proposalRiskFromString('CONFIRMATION_REQUIRED'),
        ProposalRisk.confirmationRequired);
    expect(proposalRiskFromString('HIGH_RISK'), ProposalRisk.highRisk);
    expect(proposalRiskFromString('GARBAGE'), ProposalRisk.unknown);
    expect(proposalRiskFromString(null), ProposalRisk.unknown);
  });

  test('resolved proposals are no longer pending', () {
    final proposal = CognitiveProposal.fromJson({
      'proposal_id': 'prop_xyz',
      'title': 't',
      'reason': 'r',
      'component': 'c',
      'risk_class': 'SAFE',
      'expected_impact': 'i',
      'proposed_action': 'a',
      'status': 'APPLIED',
      'created_at': '2026-08-28T12:00:00Z',
    });
    expect(proposal.isPending, isFalse);
    expect(proposal.risk, ProposalRisk.safe);
  });
}
