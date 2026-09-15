import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/chat/chat_controller.dart';
import 'package:ultron_mobile/features/chat/chat_screen.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart';
import 'package:ultron_mobile/features/voice/voice_controller.dart';

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({super.key});

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _orbController;

  @override
  void initState() {
    super.initState();
    _orbController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VoiceController>().initialize();
    });
  }

  @override
  void dispose() {
    _orbController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<VoiceController>(
      builder: (context, voice, _) {
        final gateway = context.watch<ConnectionController>();
        final active = voice.listening || voice.thinking || voice.speaking;
        final hasTranscript = voice.transcript.trim().isNotEmpty;
        final hasReply = voice.lastReply.trim().isNotEmpty;

        return Scaffold(
          backgroundColor: UltronTheme.obsidianBackground,
          body: SafeArea(
            child: Stack(
              children: [
                Positioned.fill(child: CustomPaint(painter: _StarfieldPainter())),
                SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'TAG',
                                  style: TextStyle(
                                    fontFamily: 'Consolas',
                                    fontSize: 30,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 5,
                                    color: UltronTheme.cyanAccent,
                                  ),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'PERSONAL AI',
                                  style: TextStyle(
                                    fontFamily: 'Consolas',
                                    fontSize: 10,
                                    letterSpacing: 2.3,
                                    color: UltronTheme.cleanGrey,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          _ConnectionChip(connected: gateway.isConnected),
                        ],
                      ),
                      const SizedBox(height: 24),
                      Text(
                        voice.status,
                        style: TextStyle(
                          fontFamily: 'Consolas',
                          fontSize: 11,
                          letterSpacing: 2.4,
                          fontWeight: FontWeight.w700,
                          color: active ? UltronTheme.cyanAccent : UltronTheme.cleanGrey,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        height: 330,
                        child: AnimatedBuilder(
                          animation: _orbController,
                          builder: (context, child) => _TagOrb(
                            phase: _orbController.value,
                            active: active,
                            soundLevel: voice.soundLevel,
                            onTap: voice.toggleListening,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 220),
                        child: hasTranscript
                            ? Container(
                                key: const ValueKey('transcript'),
                                width: double.infinity,
                                padding: const EdgeInsets.all(18),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.045),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: UltronTheme.cyanAccent.withOpacity(0.18)),
                                ),
                                child: Text(
                                  voice.transcript,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 18, height: 1.35, color: Colors.white),
                                ),
                              )
                            : const SizedBox(
                                key: ValueKey('hint'),
                                height: 54,
                                child: Center(
                                  child: Text(
                                    'Tap the orb and speak to TAG',
                                    style: TextStyle(color: UltronTheme.cleanGrey, fontSize: 14),
                                  ),
                                ),
                              ),
                      ),
                      const SizedBox(height: 18),
                      if (hasReply)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
                          decoration: BoxDecoration(
                            color: UltronTheme.spaceSurface.withOpacity(0.82),
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(color: UltronTheme.neonGreen.withOpacity(0.15)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'TAG',
                                style: TextStyle(
                                  color: UltronTheme.neonGreen,
                                  fontFamily: 'Consolas',
                                  fontSize: 10,
                                  letterSpacing: 2,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(voice.lastReply, style: const TextStyle(color: Colors.white, fontSize: 16, height: 1.4)),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  OutlinedButton.icon(
                                    onPressed: voice.speakLastReply,
                                    icon: const Icon(Icons.volume_up_outlined, size: 18),
                                    label: const Text('REPLAY'),
                                  ),
                                  const SizedBox(width: 8),
                                  OutlinedButton.icon(
                                    onPressed: voice.cancelSpeech,
                                    icon: const Icon(Icons.stop_rounded, size: 18),
                                    label: const Text('STOP'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      const SizedBox(height: 18),
                      Row(
                        children: [
                          Expanded(
                            child: _QuickAction(
                              icon: Icons.graphic_eq_rounded,
                              label: voice.handsFree ? 'HANDS-FREE ON' : 'HANDS-FREE',
                              active: voice.handsFree,
                              onTap: voice.toggleHandsFree,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _QuickAction(
                              icon: Icons.forum_outlined,
                              label: 'CHAT',
                              onTap: () => Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => const ChatScreen()),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _QuickAction(
                              icon: Icons.stop_circle_outlined,
                              label: 'STOP',
                              onTap: voice.cancelSpeech,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'TAG Mobile routes reasoning through your paired gateway.\nVoice input and playback stay on the device.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: UltronTheme.cleanGrey, fontSize: 11, height: 1.45),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ConnectionChip extends StatelessWidget {
  final bool connected;
  const _ConnectionChip({required this.connected});

  @override
  Widget build(BuildContext context) {
    final color = connected ? UltronTheme.neonGreen : UltronTheme.amberWarning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(shape: BoxShape.circle, color: color, boxShadow: [BoxShadow(color: color.withOpacity(0.45), blurRadius: 8)]),
          ),
          const SizedBox(width: 7),
          Text(
            connected ? 'LINKED' : 'OFFLINE',
            style: TextStyle(fontFamily: 'Consolas', fontSize: 9, color: color, fontWeight: FontWeight.bold, letterSpacing: 1.4),
          ),
        ],
      ),
    );
  }
}

class _TagOrb extends StatelessWidget {
  final double phase;
  final bool active;
  final double soundLevel;
  final VoidCallback onTap;

  const _TagOrb({required this.phase, required this.active, required this.soundLevel, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final pulse = active ? 1 + (math.sin(phase * math.pi * 2) + 1) * 0.035 : 1.0;
    final level = (soundLevel.clamp(-2.0, 12.0) + 2) / 14;
    final outer = 210 * pulse + level * 26;
    final inner = outer * 0.72;

    return Center(
      child: GestureDetector(
        onTap: onTap,
        child: SizedBox(
          width: 300,
          height: 300,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: outer,
                height: outer,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      UltronTheme.cyanAccent.withOpacity(active ? 0.20 : 0.08),
                      UltronTheme.cyanAccent.withOpacity(0.02),
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.58, 1.0],
                  ),
                ),
              ),
              Container(
                width: inner,
                height: inner,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: UltronTheme.cyanAccent.withOpacity(active ? 0.60 : 0.22), width: 1.5),
                  boxShadow: [BoxShadow(color: UltronTheme.cyanAccent.withOpacity(active ? 0.18 : 0.06), blurRadius: 35, spreadRadius: 4)],
                ),
              ),
              Container(
                width: 142,
                height: 142,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const RadialGradient(
                    colors: [Color(0xFFB8F6FF), UltronTheme.cyanAccent, Color(0xFF035C79)],
                    stops: [0.0, 0.44, 1.0],
                  ),
                  boxShadow: [BoxShadow(color: UltronTheme.cyanAccent.withOpacity(0.35), blurRadius: 42, spreadRadius: 6)],
                ),
                child: Center(child: Icon(active ? Icons.graphic_eq_rounded : Icons.mic_none_rounded, size: 54, color: UltronTheme.obsidianBackground)),
              ),
              ...List.generate(4, (index) {
                final angle = phase * math.pi * 2 + index * math.pi / 2;
                const radius = 112.0;
                return Transform.translate(
                  offset: Offset(math.cos(angle) * radius, math.sin(angle) * radius),
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: UltronTheme.cyanAccent.withOpacity(active ? 0.75 : 0.28),
                      boxShadow: [BoxShadow(color: UltronTheme.cyanAccent.withOpacity(0.35), blurRadius: 10)],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _QuickAction({required this.icon, required this.label, required this.onTap, this.active = false});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: active ? UltronTheme.cyanAccent.withOpacity(0.10) : Colors.white.withOpacity(0.035),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: active ? UltronTheme.cyanAccent.withOpacity(0.40) : Colors.white.withOpacity(0.06)),
        ),
        child: Column(
          children: [
            Icon(icon, color: active ? UltronTheme.cyanAccent : Colors.white70, size: 21),
            const SizedBox(height: 7),
            Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'Consolas',
                fontSize: 8.5,
                letterSpacing: 1.0,
                color: active ? UltronTheme.cyanAccent : UltronTheme.cleanGrey,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StarfieldPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withOpacity(0.025);
    final points = <Offset>[
      Offset(size.width * 0.14, size.height * 0.18),
      Offset(size.width * 0.82, size.height * 0.10),
      Offset(size.width * 0.68, size.height * 0.37),
      Offset(size.width * 0.24, size.height * 0.52),
      Offset(size.width * 0.90, size.height * 0.72),
      Offset(size.width * 0.12, size.height * 0.84),
    ];
    for (final point in points) {
      canvas.drawCircle(point, 1.2, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
