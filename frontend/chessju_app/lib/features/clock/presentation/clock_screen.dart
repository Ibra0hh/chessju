import 'dart:async';

import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/clock/data/clock_models.dart';
import 'package:chessju_app/features/clock/data/clock_repository.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ClockScreen extends ConsumerStatefulWidget {
  const ClockScreen({super.key});

  @override
  ConsumerState<ClockScreen> createState() => _ClockScreenState();
}

class _ClockScreenState extends ConsumerState<ClockScreen> {
  ClockPreset? _selectedPreset = clockPresets[4];
  ClockSession? _session;
  PaginatedResponse<ClockEvent>? _events;
  Timer? _ticker;
  DateTime? _lastTickAt;
  bool _submitting = false;
  bool _soundEnabled = true;
  bool _fullScreenPlaceholder = false;
  String _clockTheme = 'teal';
  String? _message;

  final _baseMinutesController = TextEditingController(text: '5');
  final _baseSecondsController = TextEditingController(text: '0');
  final _incrementController = TextEditingController(text: '0');

  @override
  void dispose() {
    _ticker?.cancel();
    _baseMinutesController.dispose();
    _baseSecondsController.dispose();
    _incrementController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Chess Clock',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ),
            if (_session != null)
              OutlinedButton.icon(
                onPressed: _submitting ? null : _loadEvents,
                icon: const Icon(Icons.history),
                label: const Text('Events'),
              ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'The timer runs locally for responsiveness. ChessJU stores setup and action snapshots only.',
        ),
        if (_message != null) ...[
          const SizedBox(height: 12),
          Text(_message!, style: TextStyle(color: _messageColor(context))),
        ],
        const SizedBox(height: 16),
        if (_session == null)
          ClockSetupPanel(
            selectedPreset: _selectedPreset,
            baseMinutesController: _baseMinutesController,
            baseSecondsController: _baseSecondsController,
            incrementController: _incrementController,
            submitting: _submitting,
            onPresetSelected: _selectPreset,
            onCreate: _createSession,
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 980;
              final timer = ClockTimerPanel(
                session: _session!,
                clockTheme: _clockTheme,
                soundEnabled: _soundEnabled,
                fullScreenPlaceholder: _fullScreenPlaceholder,
                submitting: _submitting,
                onStart: _start,
                onPause: _pause,
                onResume: _resume,
                onSwitchTurn: _switchTurn,
                onFlag: _flag,
                onComplete: _complete,
                onReset: _reset,
                onCancel: _cancel,
                onAdjust: _adjust,
                onSoundChanged: (value) => setState(() {
                  _soundEnabled = value;
                }),
                onFullScreenChanged: (value) => setState(() {
                  _fullScreenPlaceholder = value;
                }),
                onThemeChanged: (value) => setState(() {
                  _clockTheme = value;
                }),
              );
              final history = EventHistoryPanel(events: _events);

              if (wide) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 2, child: timer),
                    const SizedBox(width: 16),
                    SizedBox(width: 360, child: history),
                  ],
                );
              }
              return Column(
                children: [timer, const SizedBox(height: 16), history],
              );
            },
          ),
      ],
    );
  }

  void _selectPreset(ClockPreset? preset) {
    setState(() {
      _selectedPreset = preset;
      if (preset != null) {
        _baseMinutesController.text = (preset.baseSeconds ~/ 60).toString();
        _baseSecondsController.text = (preset.baseSeconds % 60).toString();
        _incrementController.text = preset.incrementSeconds.toString();
      }
    });
  }

  Future<void> _createSession() async {
    final parsed = _parsedSetup();
    if (parsed == null) {
      return;
    }
    await _submit(() async {
      final session = await ref
          .read(clockRepositoryProvider)
          .createSession(
            baseSeconds: parsed.baseSeconds,
            incrementSeconds: parsed.incrementSeconds,
          );
      _syncSession(session);
      await _loadEvents();
      _message = 'Clock session created.';
    });
  }

  Future<void> _start() async {
    final session = _session;
    if (session == null) {
      return;
    }
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .start(
            session: session,
            whiteRemainingMs: session.whiteRemainingMs,
            blackRemainingMs: session.blackRemainingMs,
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _pause() async {
    final session = _session;
    if (session == null) {
      return;
    }
    final snapshot = _snapshotNow(session);
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .pause(
            session: session,
            whiteRemainingMs: snapshot.white,
            blackRemainingMs: snapshot.black,
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _resume() async {
    final session = _session;
    if (session == null) {
      return;
    }
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .resume(
            session: session,
            whiteRemainingMs: session.whiteRemainingMs,
            blackRemainingMs: session.blackRemainingMs,
            activeColor: session.activeColor == 'none'
                ? 'white'
                : session.activeColor,
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _switchTurn() async {
    final session = _session;
    if (session == null ||
        !session.isRunning ||
        session.activeColor == 'none') {
      return;
    }
    final snapshot = _snapshotNow(session);
    final incrementMs = session.incrementSeconds * 1000;
    final nextActive = session.activeColor == 'white' ? 'black' : 'white';
    final white = session.activeColor == 'white'
        ? snapshot.white + incrementMs
        : snapshot.white;
    final black = session.activeColor == 'black'
        ? snapshot.black + incrementMs
        : snapshot.black;

    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .switchTurn(
            session: session,
            whiteRemainingMs: white,
            blackRemainingMs: black,
            activeColor: nextActive,
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _flag() async {
    final session = _session;
    if (session == null) {
      return;
    }
    final snapshot = _snapshotNow(session);
    final flaggedColor = snapshot.white <= 0
        ? 'white'
        : snapshot.black <= 0
        ? 'black'
        : session.activeColor;
    if (flaggedColor == 'none') {
      setState(() {
        _message = 'Start the clock before flagging a player.';
      });
      return;
    }
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .flag(
            session: session,
            whiteRemainingMs: flaggedColor == 'white' ? 0 : snapshot.white,
            blackRemainingMs: flaggedColor == 'black' ? 0 : snapshot.black,
            flaggedColor: flaggedColor,
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _complete() async {
    final session = _session;
    if (session == null) {
      return;
    }
    final snapshot = _snapshotNow(session);
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .complete(
            session: session,
            whiteRemainingMs: snapshot.white,
            blackRemainingMs: snapshot.black,
            result: 'manual',
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _reset() async {
    final session = _session;
    if (session == null) {
      return;
    }
    await _submit(() async {
      final updated = await ref.read(clockRepositoryProvider).reset(session);
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _cancel() async {
    final session = _session;
    if (session == null) {
      return;
    }
    final snapshot = _snapshotNow(session);
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .cancel(
            session: session,
            whiteRemainingMs: snapshot.white,
            blackRemainingMs: snapshot.black,
            reason: 'Cancelled from Flutter clock UI',
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _adjust(int whiteDeltaMs, int blackDeltaMs) async {
    final session = _session;
    if (session == null) {
      return;
    }
    final snapshot = _snapshotNow(session);
    final white = (snapshot.white + whiteDeltaMs).clamp(0, 24 * 60 * 60 * 1000);
    final black = (snapshot.black + blackDeltaMs).clamp(0, 24 * 60 * 60 * 1000);
    await _submit(() async {
      final updated = await ref
          .read(clockRepositoryProvider)
          .adjust(
            session: session,
            whiteRemainingMs: white,
            blackRemainingMs: black,
            reason: 'Manual time adjustment from Flutter',
          );
      _syncSession(updated);
      await _loadEvents();
    });
  }

  Future<void> _loadEvents() async {
    final session = _session;
    if (session == null) {
      return;
    }
    final events = await ref
        .read(clockRepositoryProvider)
        .getEvents(session.id);
    if (mounted) {
      setState(() {
        _events = events;
      });
    }
  }

  Future<void> _submit(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _message = null;
    });

    try {
      await action();
    } on ApiException catch (exception) {
      _message = exception.error.message;
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  void _syncSession(ClockSession session) {
    setState(() {
      _session = session;
      _lastTickAt = DateTime.now();
    });
    _configureTicker();
  }

  void _configureTicker() {
    _ticker?.cancel();
    final session = _session;
    if (session == null ||
        !session.isRunning ||
        session.activeColor == 'none') {
      return;
    }
    _ticker = Timer.periodic(const Duration(milliseconds: 200), (_) {
      final current = _session;
      if (current == null || !current.isRunning) {
        return;
      }
      final now = DateTime.now();
      final elapsed = now.difference(_lastTickAt ?? now).inMilliseconds;
      _lastTickAt = now;
      if (elapsed <= 0) {
        return;
      }
      final white = current.activeColor == 'white'
          ? current.whiteRemainingMs - elapsed
          : current.whiteRemainingMs;
      final black = current.activeColor == 'black'
          ? current.blackRemainingMs - elapsed
          : current.blackRemainingMs;

      setState(() {
        _session = current.copyWith(
          whiteRemainingMs: white < 0 ? 0 : white,
          blackRemainingMs: black < 0 ? 0 : black,
        );
      });
    });
  }

  _ClockSnapshot _snapshotNow(ClockSession session) {
    final now = DateTime.now();
    final elapsed = session.isRunning
        ? now.difference(_lastTickAt ?? now).inMilliseconds
        : 0;
    final white = session.activeColor == 'white'
        ? session.whiteRemainingMs - elapsed
        : session.whiteRemainingMs;
    final black = session.activeColor == 'black'
        ? session.blackRemainingMs - elapsed
        : session.blackRemainingMs;
    return _ClockSnapshot(white < 0 ? 0 : white, black < 0 ? 0 : black);
  }

  _ClockSetup? _parsedSetup() {
    final minutes = int.tryParse(_baseMinutesController.text.trim()) ?? 0;
    final seconds = int.tryParse(_baseSecondsController.text.trim()) ?? 0;
    final increment = int.tryParse(_incrementController.text.trim()) ?? 0;
    final baseSeconds = minutes * 60 + seconds;
    final baseError = validateBaseSeconds(baseSeconds);
    final incrementError = validateIncrementSeconds(increment);
    if (baseError != null || incrementError != null) {
      setState(() {
        _message = baseError ?? incrementError;
      });
      return null;
    }
    return _ClockSetup(baseSeconds, increment);
  }

  Color _messageColor(BuildContext context) {
    if (_message?.toLowerCase().contains('created') ?? false) {
      return Theme.of(context).colorScheme.primary;
    }
    return Theme.of(context).colorScheme.error;
  }
}

class ClockSetupPanel extends StatelessWidget {
  const ClockSetupPanel({
    super.key,
    required this.selectedPreset,
    required this.baseMinutesController,
    required this.baseSecondsController,
    required this.incrementController,
    required this.submitting,
    required this.onPresetSelected,
    required this.onCreate,
  });

  final ClockPreset? selectedPreset;
  final TextEditingController baseMinutesController;
  final TextEditingController baseSecondsController;
  final TextEditingController incrementController;
  final bool submitting;
  final ValueChanged<ClockPreset?> onPresetSelected;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Time controls',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final preset in clockPresets)
                  ChoiceChip(
                    label: Text(preset.label),
                    selected: selectedPreset == preset,
                    onSelected: (_) => onPresetSelected(preset),
                  ),
                ChoiceChip(
                  label: const Text('Custom'),
                  selected: selectedPreset == null,
                  onSelected: (_) => onPresetSelected(null),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: baseMinutesController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Base minutes',
                      prefixIcon: Icon(Icons.timer_outlined),
                    ),
                    onChanged: (_) => onPresetSelected(null),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: baseSecondsController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Seconds'),
                    onChanged: (_) => onPresetSelected(null),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: incrementController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Increment',
                      suffixText: 'sec',
                    ),
                    onChanged: (_) => onPresetSelected(null),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            PrimaryButton(
              label: 'Create casual clock',
              icon: Icons.play_circle_outline,
              loading: submitting,
              onPressed: onCreate,
            ),
          ],
        ),
      ),
    );
  }
}

class ClockTimerPanel extends StatelessWidget {
  const ClockTimerPanel({
    super.key,
    required this.session,
    required this.clockTheme,
    required this.soundEnabled,
    required this.fullScreenPlaceholder,
    required this.submitting,
    required this.onStart,
    required this.onPause,
    required this.onResume,
    required this.onSwitchTurn,
    required this.onFlag,
    required this.onComplete,
    required this.onReset,
    required this.onCancel,
    required this.onAdjust,
    required this.onSoundChanged,
    required this.onFullScreenChanged,
    required this.onThemeChanged,
  });

  final ClockSession session;
  final String clockTheme;
  final bool soundEnabled;
  final bool fullScreenPlaceholder;
  final bool submitting;
  final VoidCallback onStart;
  final VoidCallback onPause;
  final VoidCallback onResume;
  final VoidCallback onSwitchTurn;
  final VoidCallback onFlag;
  final VoidCallback onComplete;
  final VoidCallback onReset;
  final VoidCallback onCancel;
  final void Function(int whiteDeltaMs, int blackDeltaMs) onAdjust;
  final ValueChanged<bool> onSoundChanged;
  final ValueChanged<bool> onFullScreenChanged;
  final ValueChanged<String> onThemeChanged;

  @override
  Widget build(BuildContext context) {
    final activeColor = _activeThemeColor(context);
    final mobile = MediaQuery.sizeOf(context).width < 700;
    final timers = [
      Expanded(
        child: _PlayerTimerPanel(
          label: 'Player One / White',
          remainingMs: session.whiteRemainingMs,
          active: session.activeColor == 'white' && session.isRunning,
          flagged:
              session.result == 'white_flagged' ||
              session.whiteRemainingMs <= 0,
          activeColor: activeColor,
          onAddMinute: () => onAdjust(60 * 1000, 0),
          onSubtractMinute: () => onAdjust(-60 * 1000, 0),
        ),
      ),
      Expanded(
        child: _PlayerTimerPanel(
          label: 'Player Two / Black',
          remainingMs: session.blackRemainingMs,
          active: session.activeColor == 'black' && session.isRunning,
          flagged:
              session.result == 'black_flagged' ||
              session.blackRemainingMs <= 0,
          activeColor: activeColor,
          onAddMinute: () => onAdjust(0, 60 * 1000),
          onSubtractMinute: () => onAdjust(0, -60 * 1000),
        ),
      ),
    ];

    return Column(
      children: [
        if (mobile)
          Column(children: [timers[0], _ControlPanel(this), timers[1]])
        else
          Column(
            children: [
              Row(children: [timers[0], const SizedBox(width: 12), timers[1]]),
              const SizedBox(height: 12),
              _ControlPanel(this),
            ],
          ),
        const SizedBox(height: 16),
        _ClockSettings(
          selectedTheme: clockTheme,
          soundEnabled: soundEnabled,
          fullScreenPlaceholder: fullScreenPlaceholder,
          onThemeChanged: onThemeChanged,
          onSoundChanged: onSoundChanged,
          onFullScreenChanged: onFullScreenChanged,
        ),
      ],
    );
  }

  Color _activeThemeColor(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return switch (clockTheme) {
      'blue' => Colors.blue.shade600,
      'amber' => Colors.amber.shade700,
      'rose' => const Color(0xFFE11D48),
      _ => scheme.primary,
    };
  }
}

class _PlayerTimerPanel extends StatelessWidget {
  const _PlayerTimerPanel({
    required this.label,
    required this.remainingMs,
    required this.active,
    required this.flagged,
    required this.activeColor,
    required this.onAddMinute,
    required this.onSubtractMinute,
  });

  final String label;
  final int remainingMs;
  final bool active;
  final bool flagged;
  final Color activeColor;
  final VoidCallback onAddMinute;
  final VoidCallback onSubtractMinute;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final background = flagged
        ? scheme.errorContainer
        : active
        ? activeColor
        : scheme.surfaceContainerHighest;
    final foreground = flagged
        ? scheme.onErrorContainer
        : active
        ? Colors.white
        : scheme.onSurfaceVariant;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        constraints: const BoxConstraints(minHeight: 230),
        color: background,
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: foreground),
            ),
            const SizedBox(height: 16),
            FittedBox(
              child: Text(
                formatClockTime(remainingMs),
                style: Theme.of(context).textTheme.displayLarge?.copyWith(
                  color: foreground,
                  fontWeight: FontWeight.w800,
                  fontSize: 72,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              alignment: WrapAlignment.center,
              children: [
                IconButton.filledTonal(
                  tooltip: 'Subtract one minute',
                  onPressed: onSubtractMinute,
                  icon: const Icon(Icons.remove),
                ),
                IconButton.filledTonal(
                  tooltip: 'Add one minute',
                  onPressed: onAddMinute,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ControlPanel extends StatelessWidget {
  const _ControlPanel(this.panel);

  final ClockTimerPanel panel;

  @override
  Widget build(BuildContext context) {
    final session = panel.session;
    final canStart = session.isSetup || session.isPaused;
    final canPause = session.isRunning;
    final canResume = session.isPaused;
    final canSwitch = session.isRunning && session.activeColor != 'none';
    final ended = session.isEnded;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                StatusChip(session.status),
                if (session.activeColor != 'none')
                  StatusChip('${session.activeColor} to move'),
                if (session.result != null) StatusChip(session.result!),
                StatusChip(
                  '${session.baseSeconds ~/ 60}+${session.incrementSeconds}',
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                FilledButton.icon(
                  onPressed: panel.submitting || !canStart || ended
                      ? null
                      : panel.onStart,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting || !canPause
                      ? null
                      : panel.onPause,
                  icon: const Icon(Icons.pause),
                  label: const Text('Pause'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting || !canResume
                      ? null
                      : panel.onResume,
                  icon: const Icon(Icons.play_circle_outline),
                  label: const Text('Resume'),
                ),
                FilledButton.tonalIcon(
                  onPressed: panel.submitting || !canSwitch
                      ? null
                      : panel.onSwitchTurn,
                  icon: const Icon(Icons.swap_vert),
                  label: const Text('Switch'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting || ended ? null : panel.onFlag,
                  icon: const Icon(Icons.flag_outlined),
                  label: const Text('Flag'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting || ended
                      ? null
                      : panel.onComplete,
                  icon: const Icon(Icons.check_circle_outline),
                  label: const Text('Complete'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting ? null : panel.onReset,
                  icon: const Icon(Icons.restart_alt),
                  label: const Text('Reset'),
                ),
                OutlinedButton.icon(
                  onPressed: panel.submitting || ended ? null : panel.onCancel,
                  icon: const Icon(Icons.close),
                  label: const Text('Cancel'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ClockSettings extends StatelessWidget {
  const _ClockSettings({
    required this.selectedTheme,
    required this.soundEnabled,
    required this.fullScreenPlaceholder,
    required this.onThemeChanged,
    required this.onSoundChanged,
    required this.onFullScreenChanged,
  });

  final String selectedTheme;
  final bool soundEnabled;
  final bool fullScreenPlaceholder;
  final ValueChanged<String> onThemeChanged;
  final ValueChanged<bool> onSoundChanged;
  final ValueChanged<bool> onFullScreenChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Clock settings',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                for (final option in const ['teal', 'blue', 'amber', 'rose'])
                  ChoiceChip(
                    label: Text(option),
                    selected: selectedTheme == option,
                    onSelected: (_) => onThemeChanged(option),
                  ),
              ],
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: soundEnabled,
              onChanged: onSoundChanged,
              title: const Text('Sound enabled'),
              subtitle: const Text('Placeholder until audio cues are added.'),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: fullScreenPlaceholder,
              onChanged: onFullScreenChanged,
              title: const Text('Fullscreen mode'),
              subtitle: const Text(
                'Placeholder for platform-specific fullscreen.',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class EventHistoryPanel extends StatelessWidget {
  const EventHistoryPanel({super.key, required this.events});

  final PaginatedResponse<ClockEvent>? events;

  @override
  Widget build(BuildContext context) {
    final items = events?.items ?? const <ClockEvent>[];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Event history',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            if (items.isEmpty)
              const EmptyView('No clock events loaded yet.')
            else
              for (final event in items.reversed)
                ContentCard(
                  title: event.eventType.replaceAll('_', ' '),
                  subtitle:
                      '${event.activeColor} | W ${formatClockTime(event.whiteRemainingMs)} | B ${formatClockTime(event.blackRemainingMs)}',
                  trailing: Text(event.serverTimestamp),
                  leading: const Icon(Icons.bolt_outlined),
                ),
          ],
        ),
      ),
    );
  }
}

class _ClockSetup {
  const _ClockSetup(this.baseSeconds, this.incrementSeconds);

  final int baseSeconds;
  final int incrementSeconds;
}

class _ClockSnapshot {
  const _ClockSnapshot(this.white, this.black);

  final int white;
  final int black;
}
