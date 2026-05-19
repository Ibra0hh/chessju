import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class TournamentDetailScreen extends ConsumerStatefulWidget {
  const TournamentDetailScreen({super.key, required this.slug});

  final String slug;

  @override
  ConsumerState<TournamentDetailScreen> createState() =>
      _TournamentDetailScreenState();
}

class _TournamentDetailScreenState
    extends ConsumerState<TournamentDetailScreen> {
  bool _submitting = false;
  String? _message;

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(tournamentDetailProvider(widget.slug));
    final rounds = ref.watch(tournamentRoundsProvider(widget.slug));
    final standings = ref.watch(tournamentStandingsProvider(widget.slug));

    return AsyncValueView(
      value: detail,
      onRetry: () => ref.invalidate(tournamentDetailProvider(widget.slug)),
      data: (tournament) => RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(tournamentDetailProvider(widget.slug));
          ref.invalidate(tournamentRoundsProvider(widget.slug));
          ref.invalidate(tournamentStandingsProvider(widget.slug));
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              tournament.title,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                StatusChip(tournament.status),
                StatusChip(tournament.format),
                if (tournament.myRegistration != null)
                  StatusChip(tournament.myRegistration!.status),
              ],
            ),
            if (tournament.description != null) ...[
              const SizedBox(height: 16),
              Text(tournament.description!),
            ],
            const SizedBox(height: 16),
            _InfoGrid(tournament: tournament),
            const SizedBox(height: 16),
            if (_message != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_message!),
              ),
            _RegistrationAction(
              tournament: tournament,
              loading: _submitting,
              onRegister: () => _register(tournament),
              onCancel: () => _cancelRegistration(tournament),
            ),
            const SizedBox(height: 24),
            Text('Rounds', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            rounds.when(
              data: (data) => data.items.isEmpty
                  ? const EmptyView('No published rounds yet.')
                  : Column(
                      children: [
                        for (final round in data.items)
                          ContentCard(
                            title: 'Round ${round.roundNumber}',
                            subtitle:
                                '${round.status}${round.startsAt == null ? '' : ' | ${round.startsAt}'}',
                            leading: const Icon(Icons.account_tree_outlined),
                          ),
                      ],
                    ),
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => const Text('Rounds unavailable.'),
            ),
            const SizedBox(height: 24),
            Text('Standings', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            standings.when(
              data: (rows) => rows.isEmpty
                  ? const EmptyView('No standings yet.')
                  : Column(
                      children: [
                        for (final row in rows)
                          ContentCard(
                            title: '#${row.rank} ${row.username}',
                            subtitle:
                                '${row.points} pts | W ${row.wins} D ${row.draws} L ${row.losses}',
                            trailing: Text('${row.gamesPlayed} games'),
                          ),
                      ],
                    ),
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => const Text('Standings unavailable.'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _register(TournamentDetail tournament) async {
    await _submitAction(() async {
      await ref
          .read(contentRepositoryProvider)
          .registerForTournament(tournament.id);
      _message = 'Registration updated.';
    });
  }

  Future<void> _cancelRegistration(TournamentDetail tournament) async {
    await _submitAction(() async {
      await ref
          .read(contentRepositoryProvider)
          .cancelTournamentRegistration(tournament.id);
      _message = 'Registration cancelled.';
    });
  }

  Future<void> _submitAction(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _message = null;
    });

    try {
      await action();
      ref.invalidate(tournamentDetailProvider(widget.slug));
      ref.invalidate(tournamentListProvider);
      ref.invalidate(homeProvider);
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
}

class _InfoGrid extends StatelessWidget {
  const _InfoGrid({required this.tournament});

  final TournamentDetail tournament;

  @override
  Widget build(BuildContext context) {
    final timeControl = tournament.timeControl;
    final rows = [
      ('Starts', tournament.startsAt),
      if (tournament.endsAt != null) ('Ends', tournament.endsAt!),
      ('Location', tournament.location ?? 'TBD'),
      ('Approved', tournament.approvedCount.toString()),
      ('Waitlisted', tournament.waitlistedCount.toString()),
      if (tournament.maxPlayers != null)
        ('Max players', tournament.maxPlayers.toString()),
      if (tournament.spotsRemaining != null)
        ('Spots', tournament.spotsRemaining.toString()),
      if (timeControl != null)
        (
          'Time control',
          '${timeControl.name} (${timeControl.baseSeconds}+${timeControl.incrementSeconds})',
        ),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 24,
          runSpacing: 16,
          children: [
            for (final row in rows)
              SizedBox(
                width: 220,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      row.$1,
                      style: Theme.of(context).textTheme.labelMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(row.$2),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _RegistrationAction extends StatelessWidget {
  const _RegistrationAction({
    required this.tournament,
    required this.loading,
    required this.onRegister,
    required this.onCancel,
  });

  final TournamentDetail tournament;
  final bool loading;
  final VoidCallback onRegister;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final registration = tournament.myRegistration;
    final canRegister =
        tournament.status == 'registration_open' && registration == null;
    final canCancel =
        registration != null &&
        registration.status != 'cancelled' &&
        registration.status != 'rejected' &&
        tournament.status != 'completed' &&
        tournament.status != 'cancelled';

    if (canRegister) {
      return PrimaryButton(
        label: 'Register',
        icon: Icons.how_to_reg,
        loading: loading,
        onPressed: onRegister,
      );
    }
    if (canCancel) {
      return OutlinedButton.icon(
        onPressed: loading ? null : onCancel,
        icon: const Icon(Icons.close),
        label: const Text('Cancel registration'),
      );
    }
    return Text(
      registration == null
          ? 'Registration is not currently open.'
          : 'Registration status: ${registration.status}',
    );
  }
}
