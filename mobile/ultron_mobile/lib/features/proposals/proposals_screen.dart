// mobile/ultron_mobile/lib/features/proposals/proposals_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/core/models/proposal.dart';
import 'package:ultron_mobile/features/proposals/proposal_controller.dart';

class ProposalsScreen extends StatelessWidget {
  const ProposalsScreen({super.key});

  Color _riskColor(ProposalRisk risk) {
    switch (risk) {
      case ProposalRisk.safe:
        return UltronTheme.neonGreen;
      case ProposalRisk.confirmationRequired:
        return UltronTheme.amberWarning;
      case ProposalRisk.highRisk:
        return UltronTheme.rubyRed;
      case ProposalRisk.unknown:
        return UltronTheme.cleanGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      appBar: AppBar(
        backgroundColor: UltronTheme.obsidianBackground,
        elevation: 0,
        title: const Text('REVIEW', style: TextStyle(fontFamily: 'Consolas', letterSpacing: 4)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: UltronTheme.cyanAccent),
            onPressed: () => context.read<ProposalController>().refresh(),
          ),
        ],
      ),
      body: Consumer<ProposalController>(
        builder: (context, controller, child) {
          if (controller.loadState == ProposalLoadState.loading &&
              controller.proposals.isEmpty) {
            return const Center(child: CircularProgressIndicator(color: UltronTheme.cyanAccent));
          }

          if (controller.loadState == ProposalLoadState.error) {
            return _ErrorPane(
              message: controller.errorMessage ?? 'Gateway unreachable.',
              onRetry: () => controller.refresh(),
            );
          }

          if (controller.proposals.isEmpty) {
            return const _EmptyPane();
          }

          return RefreshIndicator(
            color: UltronTheme.cyanAccent,
            onRefresh: () => controller.refresh(),
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: controller.proposals.length,
              itemBuilder: (context, index) {
                final proposal = controller.proposals[index];
                return _ProposalCard(
                  proposal: proposal,
                  riskColor: _riskColor(proposal.risk),
                  onOpen: () => _openDetailSheet(context, proposal),
                );
              },
            ),
          );
        },
      ),
    );
  }

  void _openDetailSheet(BuildContext context, CognitiveProposal proposal) {
    showModalBottomSheet(
      context: context,
      backgroundColor: UltronTheme.spaceSurface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) => _ProposalDetailSheet(proposal: proposal),
    );
  }
}

class _ProposalCard extends StatelessWidget {
  final CognitiveProposal proposal;
  final Color riskColor;
  final VoidCallback onOpen;

  const _ProposalCard({required this.proposal, required this.riskColor, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: UltronTheme.spaceSurface,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: riskColor.withOpacity(0.5), width: 1),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _RiskBadge(label: proposal.risk.label, color: riskColor),
                  const Spacer(),
                  Text(
                    proposal.status,
                    style: TextStyle(
                      fontFamily: 'Consolas',
                      fontSize: 10,
                      color: proposal.isPending ? UltronTheme.amberWarning : UltronTheme.cleanGrey,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                proposal.title,
                style: const TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 4),
              Text(
                'Component: ${proposal.component}',
                style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RiskBadge extends StatelessWidget {
  final String label;
  final Color color;

  const _RiskBadge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color),
      ),
      child: Text(
        label,
        style: TextStyle(fontFamily: 'Consolas', fontSize: 10, fontWeight: FontWeight.bold, color: color),
      ),
    );
  }
}

class _ProposalDetailSheet extends StatefulWidget {
  final CognitiveProposal proposal;

  const _ProposalDetailSheet({required this.proposal});

  @override
  State<_ProposalDetailSheet> createState() => _ProposalDetailSheetState();
}

class _ProposalDetailSheetState extends State<_ProposalDetailSheet> {
  bool _busy = false;
  String? _outcome;

  @override
  Widget build(BuildContext context) {
    final proposal = widget.proposal;
    final riskColor = _colorFor(proposal.risk);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _RiskBadgeStatic(label: proposal.risk.label, color: riskColor),
                const Spacer(),
                Text(proposal.status,
                    style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey)),
              ],
            ),
            const SizedBox(height: 12),
            Text(proposal.title,
                style: const TextStyle(fontFamily: 'Inter', fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 14),
            _DetailRow('WHAT ULTRON WANTS TO CHANGE', proposal.proposedAction),
            _DetailRow('WHY', proposal.reason),
            _DetailRow('AFFECTED COMPONENT', proposal.component),
            _DetailRow('RISK LEVEL', proposal.risk.label),
            _DetailRow('EXPECTED IMPACT', proposal.expectedImpact),
            if (proposal.resolutionNote != null && proposal.resolutionNote!.isNotEmpty)
              _DetailRow('RESOLUTION NOTE', proposal.resolutionNote!),
            const SizedBox(height: 16),
            if (_outcome != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_outcome!,
                    style: const TextStyle(fontFamily: 'Consolas', fontSize: 12, color: UltronTheme.cyanAccent)),
              ),
            if (proposal.isPending && !_busy) ...[
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _decide(context, approve: true),
                      icon: const Icon(Icons.check),
                      label: const Text('APPROVE'),
                      style: ElevatedButton.styleFrom(backgroundColor: UltronTheme.neonGreen),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _decide(context, approve: false),
                      icon: const Icon(Icons.close),
                      label: const Text('REJECT'),
                      style: ElevatedButton.styleFrom(backgroundColor: UltronTheme.rubyRed),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => _cancel(context),
                child: const Text('CANCEL PROPOSAL',
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey)),
              ),
            ],
            if (_busy) const Center(child: CircularProgressIndicator(color: UltronTheme.cyanAccent)),
          ],
        ),
      ),
    );
  }

  Color _colorFor(ProposalRisk risk) {
    switch (risk) {
      case ProposalRisk.safe:
        return UltronTheme.neonGreen;
      case ProposalRisk.confirmationRequired:
        return UltronTheme.amberWarning;
      case ProposalRisk.highRisk:
        return UltronTheme.rubyRed;
      case ProposalRisk.unknown:
        return UltronTheme.cleanGrey;
    }
  }

  Future<void> _decide(BuildContext context, {required bool approve}) async {
    // HIGH_RISK gets an explicit local reinforcement dialog; the gateway still
    // enforces its own live confirmation gate independently of this UI.
    if (approve && widget.proposal.risk == ProposalRisk.highRisk) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: UltronTheme.spaceSurface,
          title: const Text('HIGH RISK OPERATION',
              style: TextStyle(fontFamily: 'Consolas', color: UltronTheme.rubyRed)),
          content: const Text(
            'ULTRON is requesting a high-impact change. The laptop will also '
            'require an additional live confirmation window after this approval.',
            style: TextStyle(fontFamily: 'Inter'),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('ABORT')),
            ElevatedButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('CONTINUE')),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    setState(() => _busy = true);
    try {
      final controller = context.read<ProposalController>();
      if (approve) {
        final outcome = await controller.approve(widget.proposal.proposalId);
        if (mounted) setState(() => _outcome = outcome);
      } else {
        await controller.reject(widget.proposal.proposalId);
        if (mounted) setState(() => _outcome = 'Proposal rejected.');
      }
    } catch (e) {
      if (mounted) setState(() => _outcome = 'Action failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel(BuildContext context) async {
    setState(() => _busy = true);
    try {
      await context.read<ProposalController>().cancel(widget.proposal.proposalId);
      if (mounted) setState(() => _outcome = 'Proposal cancelled.');
    } catch (e) {
      if (mounted) setState(() => _outcome = 'Cancel failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontFamily: 'Consolas', fontSize: 10, color: UltronTheme.cleanGrey)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontFamily: 'Inter', fontSize: 13)),
        ],
      ),
    );
  }
}

class _RiskBadgeStatic extends StatelessWidget {
  final String label;
  final Color color;

  const _RiskBadgeStatic({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color),
      ),
      child: Text(label,
          style: TextStyle(fontFamily: 'Consolas', fontSize: 11, fontWeight: FontWeight.bold, color: color)),
    );
  }
}

class _EmptyPane extends StatelessWidget {
  const _EmptyPane();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.fact_check_outlined, size: 48, color: UltronTheme.cleanGrey),
          SizedBox(height: 12),
          Text('No pending cognitive proposals.',
              style: TextStyle(fontFamily: 'Inter', color: UltronTheme.cleanGrey)),
          SizedBox(height: 4),
          Text('ULTRON will surface change requests here for your review.',
              style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey)),
        ],
      ),
    );
  }
}

class _ErrorPane extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorPane({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 48, color: UltronTheme.amberWarning),
            const SizedBox(height: 12),
            const Text('Could not reach the proposal ledger.',
                style: TextStyle(fontFamily: 'Inter')),
            const SizedBox(height: 4),
            Text(message,
                style: const TextStyle(fontFamily: 'Consolas', fontSize: 10, color: UltronTheme.cleanGrey),
                textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('RETRY')),
          ],
        ),
      ),
    );
  }
}