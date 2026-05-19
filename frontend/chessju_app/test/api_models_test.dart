import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/admin/data/admin_models.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';
import 'package:chessju_app/features/clock/data/clock_models.dart';
import 'package:chessju_app/features/games/data/game_models.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('ApiError parses backend error envelope', () {
    final error = ApiError.fromJson({
      'error': {
        'code': 'auth.unauthorized',
        'message': 'Authentication required',
        'details': {'hint': 'login'},
        'request_id': 'req-123',
      },
    });

    expect(error.code, 'auth.unauthorized');
    expect(error.message, 'Authentication required');
    expect(error.details['hint'], 'login');
    expect(error.requestId, 'req-123');
  });

  test('Pagination parses legacy list shape', () {
    final pagination = Pagination.fromJson({
      'items': const [1, 2],
      'limit': 20,
      'offset': 0,
      'total': 42,
    });

    expect(pagination.limit, 20);
    expect(pagination.offset, 0);
    expect(pagination.count, 2);
    expect(pagination.total, 42);
  });

  test('HomeContent parses backend home response', () {
    final home = HomeContent.fromJson({
      'announcements': [
        {
          'id': 'a1',
          'title': 'Round starts',
          'message': 'Round 1 starts at 5 PM',
          'priority': 'important',
        },
      ],
      'latest_news': [
        {'id': 'n1', 'title': 'ChessJU launch', 'slug': 'launch'},
      ],
      'upcoming_tournaments': [
        {
          'id': 't1',
          'title': 'JU Rapid',
          'slug': 'ju-rapid',
          'status': 'registration_open',
          'format': 'swiss',
          'starts_at': '2026-05-20T15:00:00Z',
        },
      ],
      'leaderboard_preview': [
        {
          'rank': 1,
          'user_id': 'u1',
          'username': 'ibrahim',
          'full_name': 'Ibrahim',
          'points': 3,
          'rating': 1200,
        },
      ],
    });

    expect(home.announcements.single.title, 'Round starts');
    expect(home.latestNews.single.slug, 'launch');
    expect(home.upcomingTournaments.single.title, 'JU Rapid');
    expect(home.leaderboardPreview.single.rank, 1);
  });

  test('TournamentDetail parses backend tournament response', () {
    final detail = TournamentDetail.fromJson({
      'id': 't1',
      'title': 'JU Rapid',
      'slug': 'ju-rapid',
      'status': 'registration_open',
      'format': 'swiss',
      'starts_at': '2026-05-20T15:00:00Z',
      'description': 'Weekly rapid tournament',
      'location': 'Student activity center',
      'approved_count': 8,
      'waitlisted_count': 1,
      'max_players': 16,
      'spots_remaining': 8,
      'time_control': {
        'id': 'tc1',
        'name': '10+5',
        'base_seconds': 600,
        'increment_seconds': 5,
        'delay_seconds': 0,
        'type': 'rapid',
      },
      'my_registration': {
        'id': 'r1',
        'tournament_id': 't1',
        'user_id': 'u1',
        'status': 'approved',
        'created_at': '2026-05-19T12:00:00Z',
        'updated_at': '2026-05-19T12:00:00Z',
      },
    });

    expect(detail.title, 'JU Rapid');
    expect(detail.timeControl?.name, '10+5');
    expect(detail.myRegistration?.status, 'approved');
    expect(detail.spotsRemaining, 8);
  });

  test('LeaderboardContent parses leaderboard rows', () {
    final leaderboard = LeaderboardContent.fromJson({
      'season': {
        'id': 's1',
        'name': 'Spring 2026',
        'starts_at': '2026-02-01T00:00:00Z',
        'active': true,
      },
      'generated_at': '2026-05-19T12:00:00Z',
      'rows': [
        {
          'rank': 1,
          'user_id': 'u1',
          'username': 'ibrahim',
          'full_name': 'Ibrahim',
          'points': 4.5,
          'rating': 1210,
          'wins': 4,
          'draws': 1,
          'losses': 0,
          'games_played': 5,
        },
      ],
      'limit': 20,
      'offset': 0,
      'total': 1,
    });

    expect(leaderboard.season?.name, 'Spring 2026');
    expect(leaderboard.rows.single.points, 4.5);
    expect(leaderboard.rows.single.wins, 4);
  });

  test('NotificationItem parses notification response', () {
    final notification = NotificationItem.fromJson({
      'id': 'n1',
      'type': 'message.received',
      'title': 'New message',
      'body': 'You have a new message',
      'read_at': null,
      'created_at': '2026-05-19T12:00:00Z',
    });

    expect(notification.type, 'message.received');
    expect(notification.readAt, isNull);
  });

  test('ClockSession parses sample backend response', () {
    final session = ClockSession.fromJson({
      'id': 'c1',
      'tournament_id': null,
      'pairing_id': null,
      'white_user_id': 'u1',
      'black_user_id': 'u2',
      'base_seconds': 300,
      'increment_seconds': 3,
      'delay_seconds': 0,
      'white_remaining_ms': 300000,
      'black_remaining_ms': 300000,
      'active_color': 'none',
      'status': 'setup',
      'result': null,
      'created_by': 'u1',
      'last_event_at': null,
      'started_at': null,
      'completed_at': null,
      'created_at': '2026-05-19T12:00:00Z',
      'updated_at': '2026-05-19T12:00:00Z',
    });

    expect(session.baseSeconds, 300);
    expect(session.incrementSeconds, 3);
    expect(session.status, 'setup');
    expect(session.isSetup, isTrue);
  });

  test('ClockEvent parses sample backend response', () {
    final event = ClockEvent.fromJson({
      'id': 'e1',
      'clock_session_id': 'c1',
      'event_type': 'switch_turn',
      'actor_user_id': 'u1',
      'white_remaining_ms': 297000,
      'black_remaining_ms': 300000,
      'active_color': 'black',
      'client_timestamp': '2026-05-19T12:00:00Z',
      'server_timestamp': '2026-05-19T12:00:01Z',
      'metadata': {'source': 'test'},
    });

    expect(event.eventType, 'switch_turn');
    expect(event.activeColor, 'black');
    expect(event.metadata['source'], 'test');
  });

  test('Clock time formatting and validation helpers work', () {
    expect(formatClockTime(300000), '5:00');
    expect(formatClockTime(61000), '1:01');
    expect(formatClockTime(0), '0:00');
    expect(validateBaseSeconds(0), isNotNull);
    expect(validateBaseSeconds(60), isNull);
    expect(validateIncrementSeconds(-1), isNotNull);
    expect(validateIncrementSeconds(0), isNull);
  });

  test('FriendRequest model parses sample JSON', () {
    final request = FriendRequest.fromJson({
      'id': 'fr1',
      'sender': {
        'id': 'u1',
        'username': 'white_player',
        'full_name': 'White Player',
      },
      'receiver': {
        'id': 'u2',
        'username': 'black_player',
        'full_name': 'Black Player',
      },
      'status': 'pending',
      'created_at': '2026-05-19T12:00:00Z',
      'responded_at': null,
    });

    expect(request.sender.username, 'white_player');
    expect(request.receiver.fullName, 'Black Player');
    expect(request.status, 'pending');
  });

  test('Friend model parses sample JSON', () {
    final friend = FriendUser.fromJson({
      'id': 'u2',
      'username': 'black_player',
      'full_name': 'Black Player',
      'avatar_file_id': null,
      'friendship_id': 'f1',
      'created_at': '2026-05-19T12:00:00Z',
    });

    expect(friend.id, 'u2');
    expect(friend.friendshipId, 'f1');
    expect(friend.displayName, 'Black Player');
  });

  test('Conversation model parses sample JSON', () {
    final conversation = Conversation.fromJson({
      'id': 'c1',
      'type': 'direct',
      'members': [
        {
          'user': {
            'id': 'u1',
            'username': 'white_player',
            'full_name': 'White Player',
          },
          'role': 'member',
          'joined_at': '2026-05-19T12:00:00Z',
          'left_at': null,
        },
        {
          'user': {
            'id': 'u2',
            'username': 'black_player',
            'full_name': 'Black Player',
          },
          'role': 'member',
          'joined_at': '2026-05-19T12:00:00Z',
          'left_at': null,
        },
      ],
      'last_message': {
        'id': 'm1',
        'conversation_id': 'c1',
        'sender': {
          'id': 'u2',
          'username': 'black_player',
          'full_name': 'Black Player',
        },
        'body': 'Ready for blitz?',
        'message_type': 'text',
        'created_at': '2026-05-19T12:01:00Z',
        'edited_at': null,
        'deleted_at': null,
      },
      'created_at': '2026-05-19T12:00:00Z',
      'updated_at': '2026-05-19T12:01:00Z',
    });

    expect(conversation.members.length, 2);
    expect(conversation.otherMember('u1')?.username, 'black_player');
    expect(conversation.lastMessage?.body, 'Ready for blitz?');
  });

  test(
    'Message model parses sample JSON and validation rejects empty text',
    () {
      final message = Message.fromJson({
        'id': 'm1',
        'conversation_id': 'c1',
        'sender': {
          'id': 'u1',
          'username': 'white_player',
          'full_name': 'White Player',
        },
        'body': 'Good game',
        'message_type': 'text',
        'created_at': '2026-05-19T12:00:00Z',
        'edited_at': null,
        'deleted_at': null,
      });

      expect(message.body, 'Good game');
      expect(message.isDeleted, isFalse);
      expect(validateMessageBody(''), isNotNull);
      expect(validateMessageBody('   '), isNotNull);
      expect(validateMessageBody('Hello'), isNull);
    },
  );

  test('Admin role guard helper allows admins and rejects members', () {
    expect(hasAdminAccessForRoles(['member', 'admin']), isTrue);
    expect(hasAdminAccessForRoles(['super_admin']), isTrue);
    expect(hasAdminAccessForRoles(['member']), isFalse);
  });

  test('Time control model parses sample JSON', () {
    final control = AdminTimeControl.fromJson({
      'id': 'tc1',
      'name': '5+3 Blitz',
      'base_seconds': 300,
      'increment_seconds': 3,
      'delay_seconds': 0,
      'type': 'blitz',
      'created_at': '2026-05-19T12:00:00Z',
      'updated_at': '2026-05-19T12:00:00Z',
    });

    expect(control.name, '5+3 Blitz');
    expect(control.baseSeconds, 300);
    expect(control.type, 'blitz');
  });

  test('Audit log model parses sample JSON', () {
    final log = AdminAuditLog.fromJson({
      'id': 'log1',
      'admin_id': 'admin1',
      'action': 'tournament.created',
      'entity_type': 'tournament',
      'entity_id': 't1',
      'before': null,
      'after': {'status': 'draft'},
      'ip_address': '127.0.0.1',
      'user_agent': 'test',
      'created_at': '2026-05-19T12:00:00Z',
    });

    expect(log.action, 'tournament.created');
    expect(log.after?['status'], 'draft');
    expect(log.entityType, 'tournament');
  });

  test('Result dropdown helper maps values cleanly', () {
    expect(resultLabelFor('white_win'), 'White win');
    expect(resultLabelFor('double_forfeit'), 'Double forfeit');
    expect(resultLabelFor('pending'), 'Pending');
  });

  test('Pairing generation method helper maps labels and values', () {
    expect(pairingGenerationMethodLabel('swiss'), 'Swiss');
    expect(pairingGenerationMethodLabel('round_robin'), 'Round Robin');
    expect(pairingGenerationMethodValue('Swiss'), 'swiss');
    expect(pairingGenerationMethodValue('Round Robin'), 'round_robin');
  });

  test('Admin form validation helpers catch missing fields', () {
    expect(validateRequiredText('', 'Title'), 'Title is required');
    expect(validateRequiredText('ChessJU', 'Title'), isNull);
    expect(validatePositiveIntegerText('0', 'Base seconds'), isNotNull);
    expect(validatePositiveIntegerText('300', 'Base seconds'), isNull);
  });

  test('GameDetail parses backend game detail response', () {
    final game = GameDetail.fromJson({
      'id': 'g1',
      'source': 'pgn_upload',
      'white_name': 'Ibrahim',
      'black_name': 'Guest',
      'result': '1-0',
      'event': 'Casual',
      'site': 'Amman',
      'date': '2026.05.19',
      'round': '1',
      'eco_code': 'C20',
      'opening_name': 'King Pawn Game',
      'time_control': '600',
      'played_at': '2026-05-19T12:00:00Z',
      'created_at': '2026-05-19T12:10:00Z',
      'moves_count': 2,
      'metadata': {'Event': 'Casual', 'Result': '1-0'},
      'initial_fen': standardInitialFen,
      'final_fen':
          'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
      'moves': [
        {
          'id': 'm1',
          'ply_number': 1,
          'move_number': 1,
          'side': 'white',
          'san': 'e4',
          'uci': 'e2e4',
          'fen_before': standardInitialFen,
          'fen_after':
              'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
          'is_check': false,
          'is_checkmate': false,
        },
      ],
    });

    expect(game.whiteName, 'Ibrahim');
    expect(game.ecoCode, 'C20');
    expect(game.metadata['Event'], 'Casual');
    expect(game.moves.single.san, 'e4');
    expect(game.moves.single.uci, 'e2e4');
    expect(game.playableInitialFen, standardInitialFen);
  });

  test('AnalysisJob parses queued/running/completed statuses', () {
    final job = AnalysisJob.fromJson({
      'id': 'j1',
      'game_id': 'g1',
      'status': 'queued',
      'engine_name': 'stockfish',
      'engine_version': null,
      'depth': 10,
      'time_limit_ms': null,
      'created_at': '2026-05-19T12:00:00Z',
      'started_at': null,
      'completed_at': null,
      'error_message': null,
    });

    expect(job.status, 'queued');
    expect(job.isActive, isTrue);
    expect(job.depth, 10);
  });

  test('AnalysisReport parses move evaluations', () {
    final report = AnalysisReport.fromJson({
      'id': 'r1',
      'game_id': 'g1',
      'analysis_job_id': 'j1',
      'white_accuracy': 88.5,
      'black_accuracy': 72,
      'summary': {
        'total_moves': 1,
        'white': {'best': 1},
        'black': {'mistake': 1},
      },
      'final_evaluation': {'type': 'cp', 'value': 35, 'display': '+0.35'},
      'created_at': '2026-05-19T12:00:00Z',
      'moves': [
        {
          'id': 'e1',
          'game_move_id': 'm1',
          'ply_number': 1,
          'move_number': 1,
          'side': 'white',
          'san': 'e4',
          'uci': 'e2e4',
          'evaluation_before': {'type': 'cp', 'value': 20},
          'evaluation_after': {'type': 'cp', 'value': 35, 'display': '+0.35'},
          'best_move_uci': 'e2e4',
          'best_move_san': 'e4',
          'principal_variation': ['e2e4', 'e7e5'],
          'centipawn_loss': 0,
          'classification': 'best',
          'created_at': '2026-05-19T12:00:00Z',
        },
      ],
    });

    expect(report.whiteAccuracy, 88.5);
    expect(report.finalEvaluation?.label, '+0.35');
    expect(report.moves.single.classification, 'best');
    expect(report.moves.single.principalVariation.length, 2);
    expect(analysisClassificationLabel('inaccuracy'), 'Inaccuracy');
  });

  test('MemoryTokenStorage saves and clears tokens', () async {
    final storage = MemoryTokenStorage();
    const tokens = AuthTokens(
      accessToken: 'access',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
    );

    await storage.saveTokens(tokens);
    expect((await storage.readTokens())?.accessToken, 'access');

    await storage.clearTokens();
    expect(await storage.readTokens(), isNull);
  });
}
