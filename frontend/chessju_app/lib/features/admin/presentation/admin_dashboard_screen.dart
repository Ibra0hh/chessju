import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/admin/data/admin_models.dart';
import 'package:chessju_app/features/admin/data/admin_repository.dart';
import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

enum AdminSection {
  overview(
    'Overview',
    '/admin',
    Icons.admin_panel_settings_outlined,
    'Admin identity and operational shortcuts',
  ),
  news('News', '/admin/news', Icons.article_outlined, 'Manage club articles'),
  announcements(
    'Announcements',
    '/admin/announcements',
    Icons.campaign_outlined,
    'Manage home-screen notices',
  ),
  timeControls(
    'Time Controls',
    '/admin/time-controls',
    Icons.timer_outlined,
    'Create and update chess time controls',
  ),
  tournaments(
    'Tournaments',
    '/admin/tournaments',
    Icons.emoji_events_outlined,
    'Manage tournaments, rounds, pairings, and results',
  ),
  leaderboard(
    'Leaderboard',
    '/admin/leaderboard',
    Icons.leaderboard_outlined,
    'Manage seasons and recompute snapshots',
  ),
  auditLogs(
    'Audit Logs',
    '/admin/audit-logs',
    Icons.manage_search_outlined,
    'Review admin mutations',
  ),
  observability(
    'Lists',
    '/admin/lists',
    Icons.dataset_outlined,
    'Read-only admin operational lists',
  );

  const AdminSection(this.label, this.path, this.icon, this.description);

  final String label;
  final String path;
  final IconData icon;
  final String description;
}

class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key, this.section = AdminSection.overview});

  final AdminSection section;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(authControllerProvider).user;
    if (currentUser?.isAdmin != true) {
      return const _ForbiddenAdminView();
    }

    final identity = ref.watch(adminIdentityProvider);
    return AsyncValueView(
      value: identity,
      onRetry: () => ref.invalidate(adminIdentityProvider),
      data: (admin) => LayoutBuilder(
        builder: (context, constraints) {
          final wide = constraints.maxWidth >= 980;
          final content = _AdminSectionBody(section: section, admin: admin);
          if (!wide) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _AdminHeader(admin: admin),
                const SizedBox(height: 16),
                if (section == AdminSection.overview)
                  AdminOverviewContent(
                    admin: admin,
                    onOpen: (target) => context.go(target.path),
                  )
                else ...[
                  _MobileSectionPicker(selected: section),
                  const SizedBox(height: 16),
                  content,
                ],
              ],
            );
          }

          return Row(
            children: [
              SizedBox(
                width: 280,
                child: _AdminSideNav(selected: section, admin: admin),
              ),
              const VerticalDivider(width: 1),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(24),
                  children: [content],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class AdminOverviewContent extends StatelessWidget {
  const AdminOverviewContent({
    super.key,
    required this.admin,
    required this.onOpen,
  });

  final AdminIdentity admin;
  final ValueChanged<AdminSection> onOpen;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Admin Dashboard',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 8),
        Text(
          '${admin.fullName} | @${admin.username} | ${admin.roles.join(', ')}',
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final section in AdminSection.values)
              if (section != AdminSection.overview)
                SizedBox(
                  width: 260,
                  child: Card(
                    child: ListTile(
                      leading: Icon(section.icon),
                      title: Text(section.label),
                      subtitle: Text(section.description),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => onOpen(section),
                    ),
                  ),
                ),
          ],
        ),
      ],
    );
  }
}

class _AdminSectionBody extends StatelessWidget {
  const _AdminSectionBody({required this.section, required this.admin});

  final AdminSection section;
  final AdminIdentity admin;

  @override
  Widget build(BuildContext context) {
    return switch (section) {
      AdminSection.overview => AdminOverviewContent(
        admin: admin,
        onOpen: (target) => context.go(target.path),
      ),
      AdminSection.news => const _AdminNewsSection(),
      AdminSection.announcements => const _AdminAnnouncementsSection(),
      AdminSection.timeControls => const _AdminTimeControlsSection(),
      AdminSection.tournaments => const _AdminTournamentsSection(),
      AdminSection.leaderboard => const _AdminLeaderboardSection(),
      AdminSection.auditLogs => const _AdminAuditLogsSection(),
      AdminSection.observability => const _AdminObservabilitySection(),
    };
  }
}

class AdminTournamentDetailScreen extends ConsumerWidget {
  const AdminTournamentDetailScreen({super.key, required this.tournamentId});

  final String tournamentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(authControllerProvider).user;
    if (currentUser?.isAdmin != true) {
      return const _ForbiddenAdminView();
    }

    final identity = ref.watch(adminIdentityProvider);
    return AsyncValueView(
      value: identity,
      onRetry: () => ref.invalidate(adminIdentityProvider),
      data: (_) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          OutlinedButton.icon(
            onPressed: () => context.go('/admin/tournaments'),
            icon: const Icon(Icons.arrow_back),
            label: const Text('Back to tournaments'),
          ),
          const SizedBox(height: 16),
          _TournamentManager(tournamentId: tournamentId),
        ],
      ),
    );
  }
}

class _AdminHeader extends StatelessWidget {
  const _AdminHeader({required this.admin});

  final AdminIdentity admin;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.admin_panel_settings_outlined),
        title: Text(admin.fullName),
        subtitle: Text('${admin.email} | ${admin.roles.join(', ')}'),
      ),
    );
  }
}

class _AdminSideNav extends StatelessWidget {
  const _AdminSideNav({required this.selected, required this.admin});

  final AdminSection selected;
  final AdminIdentity admin;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _AdminHeader(admin: admin),
        const SizedBox(height: 16),
        for (final section in AdminSection.values)
          ListTile(
            selected: section == selected,
            leading: Icon(section.icon),
            title: Text(section.label),
            subtitle: Text(section.description),
            onTap: () => context.go(section.path),
          ),
      ],
    );
  }
}

class _MobileSectionPicker extends StatelessWidget {
  const _MobileSectionPicker({required this.selected});

  final AdminSection selected;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<AdminSection>(
      initialValue: selected,
      decoration: const InputDecoration(labelText: 'Admin section'),
      items: [
        for (final section in AdminSection.values)
          DropdownMenuItem(value: section, child: Text(section.label)),
      ],
      onChanged: (section) {
        if (section != null) {
          context.go(section.path);
        }
      },
    );
  }
}

class _ForbiddenAdminView extends StatelessWidget {
  const _ForbiddenAdminView();

  @override
  Widget build(BuildContext context) {
    return const ErrorView(
      message: 'Admin access is required for this screen.',
    );
  }
}

class _AdminNewsSection extends ConsumerStatefulWidget {
  const _AdminNewsSection();

  @override
  ConsumerState<_AdminNewsSection> createState() => _AdminNewsSectionState();
}

class _AdminNewsSectionState extends ConsumerState<_AdminNewsSection> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final news = ref.watch(adminNewsProvider);
    return _SectionFrame(
      title: 'News',
      description:
          'Create drafts, edit article text, publish, archive, and delete articles.',
      action: FilledButton.icon(
        onPressed: _createArticle,
        icon: const Icon(Icons.add),
        label: const Text('New article'),
      ),
      message: _message,
      child: AsyncValueView(
        value: news,
        onRetry: () => ref.invalidate(adminNewsProvider),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No admin articles yet.')
            : Column(
                children: [
                  for (final article in data.items)
                    ContentCard(
                      title: article.title,
                      subtitle:
                          '${article.status} | /${article.slug} | Updated ${article.updatedAt}',
                      leading: const Icon(Icons.article_outlined),
                      trailing: _PopupActions(
                        actions: const {
                          'edit': 'Edit',
                          'publish': 'Publish',
                          'archive': 'Archive',
                          'delete': 'Delete',
                        },
                        onSelected: (action) => _articleAction(action, article),
                      ),
                    ),
                ],
              ),
      ),
    );
  }

  Future<void> _createArticle() async {
    final values = await _showFieldDialog(
      context,
      title: 'Create article',
      fields: const [
        AdminFormField('title', 'Title', required: true),
        AdminFormField('slug', 'Slug optional'),
        AdminFormField('summary', 'Summary', maxLines: 2),
        AdminFormField(
          'body_markdown',
          'Body markdown',
          required: true,
          maxLines: 8,
        ),
      ],
    );
    if (values == null) {
      return;
    }
    await _run(() => ref.read(adminRepositoryProvider).createArticle(values));
  }

  Future<void> _articleAction(String action, AdminArticle article) async {
    switch (action) {
      case 'edit':
        final values = await _showFieldDialog(
          context,
          title: 'Edit article',
          fields: [
            AdminFormField(
              'title',
              'Title',
              initial: article.title,
              required: true,
            ),
            AdminFormField('slug', 'Slug optional', initial: article.slug),
            AdminFormField(
              'summary',
              'Summary',
              initial: article.summary,
              maxLines: 2,
            ),
            AdminFormField(
              'body_markdown',
              'Body markdown',
              initial: article.bodyMarkdown,
              required: true,
              maxLines: 8,
            ),
          ],
        );
        if (values != null) {
          await _run(
            () => ref
                .read(adminRepositoryProvider)
                .updateArticle(article.id, values),
          );
        }
        break;
      case 'publish':
      case 'archive':
        await _run(
          () => ref
              .read(adminRepositoryProvider)
              .articleAction(article.id, action),
        );
        break;
      case 'delete':
        if (await _confirm(context, 'Delete article?')) {
          await _run(
            () => ref.read(adminRepositoryProvider).deleteArticle(article.id),
          );
        }
        break;
    }
  }

  Future<void> _run(Future<Object?> Function() action) async {
    try {
      await action();
      ref.invalidate(adminNewsProvider);
      setState(() => _message = 'News updated.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _AdminAnnouncementsSection extends ConsumerStatefulWidget {
  const _AdminAnnouncementsSection();

  @override
  ConsumerState<_AdminAnnouncementsSection> createState() =>
      _AdminAnnouncementsSectionState();
}

class _AdminAnnouncementsSectionState
    extends ConsumerState<_AdminAnnouncementsSection> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final announcements = ref.watch(adminAnnouncementsProvider);
    return _SectionFrame(
      title: 'Announcements',
      description:
          'Manage home-screen announcements for members, admins, or tournament players.',
      action: FilledButton.icon(
        onPressed: _createAnnouncement,
        icon: const Icon(Icons.add),
        label: const Text('New announcement'),
      ),
      message: _message,
      child: AsyncValueView(
        value: announcements,
        onRetry: () => ref.invalidate(adminAnnouncementsProvider),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No announcements yet.')
            : Column(
                children: [
                  for (final announcement in data.items)
                    ContentCard(
                      title: announcement.title,
                      subtitle:
                          '${announcement.status} | ${announcement.priority} | ${announcement.target}',
                      leading: const Icon(Icons.campaign_outlined),
                      trailing: _PopupActions(
                        actions: const {
                          'edit': 'Edit',
                          'publish': 'Publish',
                          'archive': 'Archive',
                          'delete': 'Delete',
                        },
                        onSelected: (action) =>
                            _announcementAction(action, announcement),
                      ),
                    ),
                ],
              ),
      ),
    );
  }

  Future<void> _createAnnouncement() async {
    final values = await _showFieldDialog(
      context,
      title: 'Create announcement',
      fields: const [
        AdminFormField('title', 'Title', required: true),
        AdminFormField('message', 'Message', required: true, maxLines: 4),
        AdminFormField(
          'target',
          'Target',
          initial: 'all',
          options: ['all', 'members', 'admins', 'tournament_players'],
        ),
        AdminFormField(
          'priority',
          'Priority',
          initial: 'normal',
          options: ['normal', 'important', 'urgent'],
        ),
        AdminFormField(
          'status',
          'Status',
          initial: 'published',
          options: ['draft', 'published', 'archived'],
        ),
        AdminFormField('expires_at', 'Expires at ISO optional'),
      ],
    );
    if (values != null) {
      await _run(
        () => ref.read(adminRepositoryProvider).createAnnouncement(values),
      );
    }
  }

  Future<void> _announcementAction(
    String action,
    AdminAnnouncement announcement,
  ) async {
    switch (action) {
      case 'edit':
        final values = await _showFieldDialog(
          context,
          title: 'Edit announcement',
          fields: [
            AdminFormField(
              'title',
              'Title',
              initial: announcement.title,
              required: true,
            ),
            AdminFormField(
              'message',
              'Message',
              initial: announcement.message,
              required: true,
              maxLines: 4,
            ),
            AdminFormField(
              'target',
              'Target',
              initial: announcement.target,
              options: const ['all', 'members', 'admins', 'tournament_players'],
            ),
            AdminFormField(
              'priority',
              'Priority',
              initial: announcement.priority,
              options: const ['normal', 'important', 'urgent'],
            ),
            AdminFormField(
              'expires_at',
              'Expires at ISO optional',
              initial: announcement.expiresAt,
            ),
          ],
        );
        if (values != null) {
          await _run(
            () => ref
                .read(adminRepositoryProvider)
                .updateAnnouncement(announcement.id, values),
          );
        }
        break;
      case 'publish':
      case 'archive':
        await _run(
          () => ref
              .read(adminRepositoryProvider)
              .announcementAction(announcement.id, action),
        );
        break;
      case 'delete':
        if (await _confirm(context, 'Delete announcement?')) {
          await _run(
            () => ref
                .read(adminRepositoryProvider)
                .deleteAnnouncement(announcement.id),
          );
        }
        break;
    }
  }

  Future<void> _run(Future<Object?> Function() action) async {
    try {
      await action();
      ref.invalidate(adminAnnouncementsProvider);
      setState(() => _message = 'Announcements updated.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _AdminTimeControlsSection extends ConsumerStatefulWidget {
  const _AdminTimeControlsSection();

  @override
  ConsumerState<_AdminTimeControlsSection> createState() =>
      _AdminTimeControlsSectionState();
}

class _AdminTimeControlsSectionState
    extends ConsumerState<_AdminTimeControlsSection> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final controls = ref.watch(adminTimeControlsProvider);
    return _SectionFrame(
      title: 'Time Controls',
      description: 'Create reusable tournament clock presets.',
      action: FilledButton.icon(
        onPressed: _createTimeControl,
        icon: const Icon(Icons.add),
        label: const Text('New time control'),
      ),
      message: _message,
      child: AsyncValueView(
        value: controls,
        onRetry: () => ref.invalidate(adminTimeControlsProvider),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No time controls yet.')
            : Column(
                children: [
                  for (final control in data.items)
                    ContentCard(
                      title: control.name,
                      subtitle:
                          '${control.type} | ${control.baseSeconds}+${control.incrementSeconds} delay ${control.delaySeconds}',
                      leading: const Icon(Icons.timer_outlined),
                      trailing: IconButton(
                        tooltip: 'Edit',
                        onPressed: () => _editTimeControl(control),
                        icon: const Icon(Icons.edit_outlined),
                      ),
                    ),
                ],
              ),
      ),
    );
  }

  Future<void> _createTimeControl() async {
    final values = await _timeControlDialog();
    if (values != null) {
      await _run(
        () => ref.read(adminRepositoryProvider).createTimeControl(values),
      );
    }
  }

  Future<void> _editTimeControl(AdminTimeControl control) async {
    final values = await _timeControlDialog(control);
    if (values != null) {
      await _run(
        () => ref
            .read(adminRepositoryProvider)
            .updateTimeControl(control.id, values),
      );
    }
  }

  Future<Map<String, Object?>?> _timeControlDialog([
    AdminTimeControl? control,
  ]) async {
    final values = await _showFieldDialog(
      context,
      title: control == null ? 'Create time control' : 'Edit time control',
      fields: [
        AdminFormField('name', 'Name', initial: control?.name, required: true),
        AdminFormField(
          'base_seconds',
          'Base seconds',
          initial: control?.baseSeconds.toString() ?? '300',
          required: true,
        ),
        AdminFormField(
          'increment_seconds',
          'Increment seconds',
          initial: control?.incrementSeconds.toString() ?? '0',
        ),
        AdminFormField(
          'delay_seconds',
          'Delay seconds',
          initial: control?.delaySeconds.toString() ?? '0',
        ),
        AdminFormField(
          'type',
          'Type',
          initial: control?.type ?? 'rapid',
          options: const ['bullet', 'blitz', 'rapid', 'classical', 'custom'],
        ),
      ],
    );
    if (values == null) {
      return null;
    }
    return {
      ...values,
      'base_seconds': int.tryParse(values['base_seconds']?.toString() ?? ''),
      'increment_seconds':
          int.tryParse(values['increment_seconds']?.toString() ?? '0') ?? 0,
      'delay_seconds':
          int.tryParse(values['delay_seconds']?.toString() ?? '0') ?? 0,
    };
  }

  Future<void> _run(Future<Object?> Function() action) async {
    try {
      await action();
      ref.invalidate(adminTimeControlsProvider);
      setState(() => _message = 'Time controls updated.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _AdminTournamentsSection extends ConsumerStatefulWidget {
  const _AdminTournamentsSection();

  @override
  ConsumerState<_AdminTournamentsSection> createState() =>
      _AdminTournamentsSectionState();
}

class _AdminTournamentsSectionState
    extends ConsumerState<_AdminTournamentsSection> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final tournaments = ref.watch(adminTournamentsProvider);
    return _SectionFrame(
      title: 'Tournaments',
      description:
          'Manage tournament lifecycle, registrations, rounds, pairings, and results.',
      action: FilledButton.icon(
        onPressed: _createTournament,
        icon: const Icon(Icons.add),
        label: const Text('New tournament'),
      ),
      message: _message,
      child: AsyncValueView(
        value: tournaments,
        onRetry: () => ref.invalidate(adminTournamentsProvider),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No tournaments yet.')
            : Column(
                children: [
                  for (final tournament in data.items)
                    ContentCard(
                      title: tournament.title,
                      subtitle:
                          '${tournament.status} | ${tournament.format} | ${tournament.startsAt}',
                      leading: const Icon(Icons.emoji_events_outlined),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () =>
                          context.go('/admin/tournaments/${tournament.id}'),
                    ),
                ],
              ),
      ),
    );
  }

  Future<void> _createTournament() async {
    final values = await _tournamentDialog(context);
    if (values == null) {
      return;
    }
    try {
      await ref.read(adminRepositoryProvider).createTournament(values);
      ref.invalidate(adminTournamentsProvider);
      setState(() => _message = 'Tournament created.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _TournamentManager extends ConsumerStatefulWidget {
  const _TournamentManager({required this.tournamentId});

  final String tournamentId;

  @override
  ConsumerState<_TournamentManager> createState() => _TournamentManagerState();
}

class _TournamentManagerState extends ConsumerState<_TournamentManager> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final tournament = ref.watch(
      adminTournamentDetailProvider(widget.tournamentId),
    );
    final registrations = ref.watch(
      adminTournamentRegistrationsProvider(widget.tournamentId),
    );
    final rounds = ref.watch(adminRoundsProvider(widget.tournamentId));
    final standings = ref.watch(
      adminTournamentStandingsProvider(widget.tournamentId),
    );

    return AsyncValueView(
      value: tournament,
      onRetry: () =>
          ref.invalidate(adminTournamentDetailProvider(widget.tournamentId)),
      data: (item) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(item.title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              StatusChip(item.status),
              StatusChip(item.format),
              if (item.deletedAt != null) const StatusChip('deleted'),
            ],
          ),
          const SizedBox(height: 12),
          Text(item.description ?? 'No description.'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                onPressed: () => _editTournament(item),
                icon: const Icon(Icons.edit_outlined),
                label: const Text('Edit'),
              ),
              OutlinedButton(
                onPressed: () => _tournamentAction('publish'),
                child: const Text('Publish'),
              ),
              OutlinedButton(
                onPressed: () => _tournamentAction('open-registration'),
                child: const Text('Open registration'),
              ),
              OutlinedButton(
                onPressed: () => _tournamentAction('close-registration'),
                child: const Text('Close registration'),
              ),
              OutlinedButton(
                onPressed: () => _tournamentAction('cancel'),
                child: const Text('Cancel'),
              ),
              OutlinedButton(
                onPressed: () async {
                  if (await _confirm(context, 'Soft-delete this tournament?')) {
                    await _run(
                      () => ref
                          .read(adminRepositoryProvider)
                          .deleteTournament(item.id),
                    );
                  }
                },
                child: const Text('Delete'),
              ),
            ],
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!),
          ],
          const SizedBox(height: 24),
          _RegistrationsPanel(
            registrations: registrations,
            tournamentId: widget.tournamentId,
            onMessage: (message) => setState(() => _message = message),
          ),
          const SizedBox(height: 24),
          _RoundsPanel(
            tournamentId: widget.tournamentId,
            rounds: rounds,
            onMessage: (message) => setState(() => _message = message),
          ),
          const SizedBox(height: 24),
          _StandingsPanel(standings: standings),
        ],
      ),
    );
  }

  Future<void> _editTournament(AdminTournament item) async {
    final values = await _tournamentDialog(context, item);
    if (values != null) {
      await _run(
        () =>
            ref.read(adminRepositoryProvider).updateTournament(item.id, values),
      );
    }
  }

  Future<void> _tournamentAction(String action) async {
    await _run(
      () => ref
          .read(adminRepositoryProvider)
          .tournamentAction(widget.tournamentId, action),
    );
  }

  Future<void> _run(Future<Object?> Function() action) async {
    try {
      await action();
      ref.invalidate(adminTournamentDetailProvider(widget.tournamentId));
      ref.invalidate(adminTournamentsProvider);
      setState(() => _message = 'Tournament updated.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _RegistrationsPanel extends ConsumerWidget {
  const _RegistrationsPanel({
    required this.registrations,
    required this.tournamentId,
    required this.onMessage,
  });

  final AsyncValue<dynamic> registrations;
  final String tournamentId;
  final ValueChanged<String> onMessage;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Registrations',
      child: AsyncValueView(
        value: registrations,
        onRetry: () =>
            ref.invalidate(adminTournamentRegistrationsProvider(tournamentId)),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No registrations yet.')
            : Column(
                children: [
                  for (final registration in data.items)
                    ContentCard(
                      title: registration.userId,
                      subtitle:
                          '${registration.status} | seed ${registration.seedRating ?? '-'}',
                      leading: const Icon(Icons.how_to_reg_outlined),
                      trailing: _PopupActions(
                        actions: const {
                          'approved': 'Approve',
                          'waitlisted': 'Waitlist',
                          'rejected': 'Reject',
                          'cancelled': 'Cancel',
                        },
                        onSelected: (status) async {
                          try {
                            await ref
                                .read(adminRepositoryProvider)
                                .updateRegistration(registration.id, {
                                  'status': status,
                                });
                            ref.invalidate(
                              adminTournamentRegistrationsProvider(
                                tournamentId,
                              ),
                            );
                            onMessage('Registration updated.');
                          } on ApiException catch (exception) {
                            onMessage(exception.error.message);
                          }
                        },
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

class _RoundsPanel extends ConsumerWidget {
  const _RoundsPanel({
    required this.tournamentId,
    required this.rounds,
    required this.onMessage,
  });

  final String tournamentId;
  final AsyncValue<dynamic> rounds;
  final ValueChanged<String> onMessage;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Rounds / Pairings / Results',
      action: OutlinedButton.icon(
        onPressed: () => _createRound(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Create round'),
      ),
      child: AsyncValueView(
        value: rounds,
        onRetry: () => ref.invalidate(adminRoundsProvider(tournamentId)),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No rounds yet.')
            : Column(
                children: [
                  for (final round in data.items)
                    _RoundTile(
                      round: round,
                      tournamentId: tournamentId,
                      onMessage: onMessage,
                    ),
                ],
              ),
      ),
    );
  }

  Future<void> _createRound(BuildContext context, WidgetRef ref) async {
    final values = await _showFieldDialog(
      context,
      title: 'Create round',
      fields: const [
        AdminFormField('round_number', 'Round number optional'),
        AdminFormField('title', 'Title optional'),
        AdminFormField('starts_at', 'Starts at ISO optional'),
      ],
    );
    if (values == null) {
      return;
    }
    final payload = {
      ...values,
      if ((values['round_number'] ?? '').toString().trim().isNotEmpty)
        'round_number': int.tryParse(values['round_number']!),
    };
    try {
      await ref
          .read(adminRepositoryProvider)
          .createRound(tournamentId, payload);
      ref.invalidate(adminRoundsProvider(tournamentId));
      onMessage('Round created.');
    } on ApiException catch (exception) {
      onMessage(exception.error.message);
    }
  }
}

class _RoundTile extends ConsumerWidget {
  const _RoundTile({
    required this.round,
    required this.tournamentId,
    required this.onMessage,
  });

  final AdminRound round;
  final String tournamentId;
  final ValueChanged<String> onMessage;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pairings = ref.watch(adminPairingsProvider(round.id));
    return Card(
      child: ExpansionTile(
        leading: const Icon(Icons.account_tree_outlined),
        title: Text('Round ${round.roundNumber}'),
        subtitle: Text(
          '${round.status}${round.title == null ? '' : ' | ${round.title}'}',
        ),
        childrenPadding: const EdgeInsets.all(12),
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final action in ['publish', 'start', 'complete', 'cancel'])
                OutlinedButton(
                  onPressed: () => _roundAction(ref, action),
                  child: Text(action),
                ),
              OutlinedButton.icon(
                onPressed: () => _createPairing(context, ref),
                icon: const Icon(Icons.add),
                label: const Text('Pairing'),
              ),
              FilledButton.icon(
                onPressed: () => _generatePairings(context, ref),
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Generate'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          AsyncValueView(
            value: pairings,
            onRetry: () => ref.invalidate(adminPairingsProvider(round.id)),
            data: (data) => data.items.isEmpty
                ? const EmptyView('No pairings yet.')
                : Column(
                    children: [
                      for (final pairing in data.items)
                        ContentCard(
                          title: 'Board ${pairing.boardNumber}',
                          subtitle:
                              '${pairing.whiteUser?.displayName ?? 'BYE'} vs ${pairing.blackUser?.displayName ?? 'BYE'} | ${resultLabelFor(pairing.result)}',
                          leading: const Icon(Icons.sports_esports_outlined),
                          trailing: _PopupActions(
                            actions: const {
                              'result': 'Submit result',
                              'cancel': 'Cancel pairing',
                            },
                            onSelected: (action) =>
                                _pairingAction(context, ref, action, pairing),
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Future<void> _roundAction(WidgetRef ref, String action) async {
    try {
      await ref.read(adminRepositoryProvider).roundAction(round.id, action);
      ref.invalidate(adminRoundsProvider(tournamentId));
      onMessage('Round updated.');
    } on ApiException catch (exception) {
      onMessage(exception.error.message);
    }
  }

  Future<void> _createPairing(BuildContext context, WidgetRef ref) async {
    final values = await _showFieldDialog(
      context,
      title: 'Create manual pairing',
      fields: const [
        AdminFormField('board_number', 'Board number optional'),
        AdminFormField('white_user_id', 'White user ID'),
        AdminFormField('black_user_id', 'Black user ID'),
        AdminFormField(
          'result',
          'Result',
          initial: 'pending',
          options: [
            'pending',
            'white_win',
            'black_win',
            'draw',
            'white_forfeit',
            'black_forfeit',
            'double_forfeit',
            'bye',
          ],
        ),
      ],
    );
    if (values == null) {
      return;
    }
    final payload = {
      ...values,
      if ((values['board_number'] ?? '').toString().trim().isNotEmpty)
        'board_number': int.tryParse(values['board_number']!),
    };
    try {
      await ref.read(adminRepositoryProvider).createPairing(round.id, payload);
      ref.invalidate(adminPairingsProvider(round.id));
      onMessage('Pairing created.');
    } on ApiException catch (exception) {
      onMessage(exception.error.message);
    }
  }

  Future<void> _generatePairings(BuildContext context, WidgetRef ref) async {
    final values = await _showFieldDialog(
      context,
      title: 'Generate pairings',
      fields: const [
        AdminFormField(
          'method',
          'Method',
          initial: 'Swiss',
          options: ['Swiss', 'Round Robin'],
        ),
        AdminFormField(
          'overwrite_existing',
          'Overwrite existing pending pairings',
          initial: 'false',
          options: ['false', 'true'],
        ),
      ],
    );
    if (values == null) {
      return;
    }
    try {
      final response = await ref
          .read(adminRepositoryProvider)
          .generatePairings(
            round.id,
            method: pairingGenerationMethodValue(values['method'] ?? 'Swiss'),
            overwriteExisting: values['overwrite_existing'] == 'true',
          );
      ref.invalidate(adminPairingsProvider(round.id));
      ref.invalidate(adminTournamentStandingsProvider(tournamentId));
      onMessage('Generated ${response.items.length} pairings.');
    } on ApiException catch (exception) {
      onMessage(exception.error.message);
    }
  }

  Future<void> _pairingAction(
    BuildContext context,
    WidgetRef ref,
    String action,
    AdminPairing pairing,
  ) async {
    try {
      if (action == 'cancel') {
        await ref.read(adminRepositoryProvider).cancelPairing(pairing.id);
      } else {
        final values = await _showFieldDialog(
          context,
          title: 'Submit result',
          fields: [
            AdminFormField(
              'result',
              'Result',
              initial: pairing.result,
              options: const [
                'pending',
                'white_win',
                'black_win',
                'draw',
                'white_forfeit',
                'black_forfeit',
                'double_forfeit',
                'bye',
              ],
            ),
          ],
        );
        if (values == null) {
          return;
        }
        await ref
            .read(adminRepositoryProvider)
            .submitResult(pairing.id, values['result']!);
      }
      ref.invalidate(adminPairingsProvider(round.id));
      ref.invalidate(adminTournamentStandingsProvider(tournamentId));
      onMessage('Pairing updated.');
    } on ApiException catch (exception) {
      onMessage(exception.error.message);
    }
  }
}

class _StandingsPanel extends StatelessWidget {
  const _StandingsPanel({required this.standings});

  final AsyncValue<dynamic> standings;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Standings',
      child: standings.when(
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
    );
  }
}

class _AdminLeaderboardSection extends ConsumerStatefulWidget {
  const _AdminLeaderboardSection();

  @override
  ConsumerState<_AdminLeaderboardSection> createState() =>
      _AdminLeaderboardSectionState();
}

class _AdminLeaderboardSectionState
    extends ConsumerState<_AdminLeaderboardSection> {
  String? _message;

  @override
  Widget build(BuildContext context) {
    final seasons = ref.watch(adminSeasonsProvider);
    final leaderboard = ref.watch(adminLeaderboardProvider);
    return _SectionFrame(
      title: 'Leaderboard',
      description:
          'Create seasons, activate one season, and recompute leaderboard snapshots.',
      action: Wrap(
        spacing: 8,
        children: [
          FilledButton.icon(
            onPressed: _createSeason,
            icon: const Icon(Icons.add),
            label: const Text('New season'),
          ),
          OutlinedButton.icon(
            onPressed: () => _recompute(null),
            icon: const Icon(Icons.refresh),
            label: const Text('Recompute all-time'),
          ),
        ],
      ),
      message: _message,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Panel(
            title: 'Seasons',
            child: AsyncValueView(
              value: seasons,
              onRetry: () => ref.invalidate(adminSeasonsProvider),
              data: (data) => data.items.isEmpty
                  ? const EmptyView('No seasons yet.')
                  : Column(
                      children: [
                        for (final season in data.items)
                          ContentCard(
                            title: season.name,
                            subtitle:
                                '${season.startsAt}${season.endsAt == null ? '' : ' - ${season.endsAt}'}',
                            leading: Icon(
                              season.active
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_unchecked,
                            ),
                            trailing: Wrap(
                              spacing: 8,
                              children: [
                                OutlinedButton(
                                  onPressed: () => _activateSeason(season.id),
                                  child: const Text('Activate'),
                                ),
                                OutlinedButton(
                                  onPressed: () => _recompute(season.id),
                                  child: const Text('Recompute'),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 16),
          _Panel(
            title: 'Rows',
            child: AsyncValueView(
              value: leaderboard,
              onRetry: () => ref.invalidate(adminLeaderboardProvider),
              data: (data) => data.rows.isEmpty
                  ? const EmptyView('No leaderboard snapshot yet.')
                  : Column(
                      children: [
                        for (final row in data.rows)
                          ContentCard(
                            title: '#${row.rank} ${row.username}',
                            subtitle:
                                '${row.points} pts | ${row.rating} rating | W ${row.wins} D ${row.draws} L ${row.losses}',
                          ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createSeason() async {
    final values = await _showFieldDialog(
      context,
      title: 'Create season',
      fields: const [
        AdminFormField('name', 'Name', required: true),
        AdminFormField('starts_at', 'Starts at ISO', required: true),
        AdminFormField('ends_at', 'Ends at ISO optional'),
      ],
    );
    if (values == null) {
      return;
    }
    await _run(() => ref.read(adminRepositoryProvider).createSeason(values));
  }

  Future<void> _activateSeason(String id) async {
    await _run(() => ref.read(adminRepositoryProvider).activateSeason(id));
  }

  Future<void> _recompute(String? seasonId) async {
    await _run(
      () => ref
          .read(adminRepositoryProvider)
          .recomputeLeaderboard(seasonId: seasonId),
    );
  }

  Future<void> _run(Future<Object?> Function() action) async {
    try {
      await action();
      ref.invalidate(adminSeasonsProvider);
      ref.invalidate(adminLeaderboardProvider);
      setState(() => _message = 'Leaderboard updated.');
    } on ApiException catch (exception) {
      setState(() => _message = exception.error.message);
    }
  }
}

class _AdminAuditLogsSection extends ConsumerWidget {
  const _AdminAuditLogsSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logs = ref.watch(adminAuditLogsProvider);
    return _SectionFrame(
      title: 'Audit Logs',
      description:
          'Recent admin mutations. Payload summaries are intentionally compact.',
      child: AsyncValueView(
        value: logs,
        onRetry: () => ref.invalidate(adminAuditLogsProvider),
        data: (data) => data.items.isEmpty
            ? const EmptyView('No audit logs yet.')
            : Column(
                children: [
                  for (final log in data.items)
                    ContentCard(
                      title: log.action,
                      subtitle:
                          '${log.entityType} ${log.entityId ?? ''} | admin ${log.adminId} | ${log.createdAt}',
                      leading: const Icon(Icons.manage_search_outlined),
                      trailing: Text(
                        'before ${log.before?.length ?? 0}\nafter ${log.after?.length ?? 0}',
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

class _AdminObservabilitySection extends StatelessWidget {
  const _AdminObservabilitySection();

  @override
  Widget build(BuildContext context) {
    return const _SectionFrame(
      title: 'Admin Lists',
      description:
          'Read-only operational lists for games, analysis jobs, Chess.com sync jobs, and notifications.',
      child: Column(
        children: [
          _RawListPanel(title: 'Games', providerName: 'games'),
          SizedBox(height: 16),
          _RawListPanel(title: 'Analysis Jobs', providerName: 'analysis'),
          SizedBox(height: 16),
          _RawListPanel(title: 'Chess.com Sync Jobs', providerName: 'chesscom'),
          SizedBox(height: 16),
          _RawListPanel(title: 'Notifications', providerName: 'notifications'),
        ],
      ),
    );
  }
}

class _RawListPanel extends ConsumerWidget {
  const _RawListPanel({required this.title, required this.providerName});

  final String title;
  final String providerName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = switch (providerName) {
      'analysis' => adminAnalysisJobsProvider,
      'chesscom' => adminChessComSyncJobsProvider,
      'notifications' => adminNotificationsProvider,
      _ => adminGamesProvider,
    };
    final items = ref.watch(provider);
    return _Panel(
      title: title,
      child: AsyncValueView(
        value: items,
        onRetry: () => ref.invalidate(provider),
        data: (data) => data.items.isEmpty
            ? EmptyView('No $title rows yet.')
            : Column(
                children: [
                  for (final item in data.items.take(10))
                    ContentCard(
                      title: item.title,
                      subtitle: item.subtitle,
                      leading: const Icon(Icons.dataset_outlined),
                    ),
                ],
              ),
      ),
    );
  }
}

class _SectionFrame extends StatelessWidget {
  const _SectionFrame({
    required this.title,
    required this.description,
    required this.child,
    this.action,
    this.message,
  });

  final String title;
  final String description;
  final Widget child;
  final Widget? action;
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              width: 520,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(description),
                ],
              ),
            ),
            ?action,
          ],
        ),
        if (message != null) ...[const SizedBox(height: 12), Text(message!)],
        const SizedBox(height: 16),
        child,
      ],
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.action});

  final String title;
  final Widget child;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                ?action,
              ],
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

class _PopupActions extends StatelessWidget {
  const _PopupActions({required this.actions, required this.onSelected});

  final Map<String, String> actions;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      onSelected: onSelected,
      itemBuilder: (context) => [
        for (final entry in actions.entries)
          PopupMenuItem(value: entry.key, child: Text(entry.value)),
      ],
    );
  }
}

class AdminFormField {
  const AdminFormField(
    this.key,
    this.label, {
    this.initial,
    this.required = false,
    this.maxLines = 1,
    this.options,
  });

  final String key;
  final String label;
  final String? initial;
  final bool required;
  final int maxLines;
  final List<String>? options;
}

Future<Map<String, String>?> _showFieldDialog(
  BuildContext context, {
  required String title,
  required List<AdminFormField> fields,
}) async {
  final formKey = GlobalKey<FormState>();
  final controllers = {
    for (final field in fields)
      if (field.options == null)
        field.key: TextEditingController(text: field.initial ?? ''),
  };
  final values = {
    for (final field in fields)
      if (field.options != null)
        field.key: field.initial ?? field.options!.first,
  };

  final result = await showDialog<Map<String, String>>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Form(
        key: formKey,
        child: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final field in fields) ...[
                  if (field.options == null)
                    TextFormField(
                      controller: controllers[field.key],
                      maxLines: field.maxLines,
                      decoration: InputDecoration(labelText: field.label),
                      validator: field.required
                          ? (value) => validateRequiredText(value, field.label)
                          : null,
                    )
                  else
                    DropdownButtonFormField<String>(
                      initialValue: values[field.key],
                      decoration: InputDecoration(labelText: field.label),
                      items: [
                        for (final option in field.options!)
                          DropdownMenuItem(value: option, child: Text(option)),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          values[field.key] = value;
                        }
                      },
                    ),
                  const SizedBox(height: 12),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (formKey.currentState?.validate() != true) {
              return;
            }
            Navigator.of(context).pop({
              for (final field in fields)
                field.key: field.options == null
                    ? controllers[field.key]!.text.trim()
                    : values[field.key] ?? '',
            });
          },
          child: const Text('Save'),
        ),
      ],
    ),
  );

  for (final controller in controllers.values) {
    controller.dispose();
  }
  return result;
}

Future<bool> _confirm(BuildContext context, String message) async {
  return await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Confirm'),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Confirm'),
            ),
          ],
        ),
      ) ??
      false;
}

Future<Map<String, Object?>?> _tournamentDialog(
  BuildContext context, [
  AdminTournament? tournament,
]) async {
  final startsDefault =
      tournament?.startsAt ??
      DateTime.now().add(const Duration(days: 7)).toUtc().toIso8601String();
  final values = await _showFieldDialog(
    context,
    title: tournament == null ? 'Create tournament' : 'Edit tournament',
    fields: [
      AdminFormField(
        'title',
        'Title',
        initial: tournament?.title,
        required: true,
      ),
      AdminFormField('slug', 'Slug optional', initial: tournament?.slug),
      AdminFormField(
        'description',
        'Description',
        initial: tournament?.description,
        maxLines: 4,
      ),
      AdminFormField(
        'format',
        'Format',
        initial: tournament?.format ?? 'swiss',
        options: const ['swiss', 'round_robin', 'knockout', 'arena', 'manual'],
      ),
      if (tournament == null)
        const AdminFormField(
          'status',
          'Status',
          initial: 'draft',
          options: [
            'draft',
            'published',
            'registration_open',
            'registration_closed',
          ],
        ),
      AdminFormField(
        'time_control_id',
        'Time control ID optional',
        initial: tournament?.timeControl?.id,
      ),
      AdminFormField(
        'max_players',
        'Max players optional',
        initial: tournament?.maxPlayers?.toString(),
      ),
      AdminFormField(
        'starts_at',
        'Starts at ISO',
        initial: startsDefault,
        required: true,
      ),
      AdminFormField(
        'ends_at',
        'Ends at ISO optional',
        initial: tournament?.endsAt,
      ),
      AdminFormField(
        'registration_open_at',
        'Registration opens ISO optional',
        initial: tournament?.registrationOpenAt,
      ),
      AdminFormField(
        'registration_close_at',
        'Registration closes ISO optional',
        initial: tournament?.registrationCloseAt,
      ),
      AdminFormField(
        'location',
        'Location optional',
        initial: tournament?.location,
      ),
    ],
  );
  if (values == null) {
    return null;
  }
  return {
    ...values,
    if ((values['max_players'] ?? '').trim().isNotEmpty)
      'max_players': int.tryParse(values['max_players']!),
  };
}
