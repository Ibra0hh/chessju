import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final socialRepositoryProvider = Provider<SocialRepository>((ref) {
  return SocialRepository(ref.watch(apiClientProvider));
});

final incomingFriendRequestsProvider =
    FutureProvider.autoDispose<PaginatedResponse<FriendRequest>>((ref) {
      return ref
          .watch(socialRepositoryProvider)
          .listFriendRequests(direction: 'incoming');
    });

final outgoingFriendRequestsProvider =
    FutureProvider.autoDispose<PaginatedResponse<FriendRequest>>((ref) {
      return ref
          .watch(socialRepositoryProvider)
          .listFriendRequests(direction: 'outgoing');
    });

final friendsProvider =
    FutureProvider.autoDispose<PaginatedResponse<FriendUser>>((ref) {
      return ref.watch(socialRepositoryProvider).listFriends();
    });

final blocksProvider =
    FutureProvider.autoDispose<PaginatedResponse<BlockedUser>>((ref) {
      return ref.watch(socialRepositoryProvider).listBlocks();
    });

final conversationsProvider =
    FutureProvider.autoDispose<PaginatedResponse<Conversation>>((ref) {
      return ref.watch(socialRepositoryProvider).listConversations();
    });

final conversationDetailProvider = FutureProvider.autoDispose
    .family<Conversation, String>((ref, id) {
      return ref.watch(socialRepositoryProvider).getConversation(id);
    });

final conversationMessagesProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<Message>, String>((ref, id) {
      return ref.watch(socialRepositoryProvider).listMessages(id);
    });

class SocialRepository {
  const SocialRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<FriendRequest> sendFriendRequest(String receiverId) {
    return _apiClient.post<FriendRequest>(
      '/friends/requests',
      data: {'receiver_id': receiverId},
      parse: (data) => FriendRequest.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<FriendRequest>> listFriendRequests({
    String? direction,
    String status = 'pending',
  }) {
    final query = <String, Object?>{'limit': 50, 'offset': 0, 'status': status};
    if (direction != null) {
      query['direction'] = direction;
    }

    return _apiClient.get<PaginatedResponse<FriendRequest>>(
      '/friends/requests',
      queryParameters: query,
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), FriendRequest.fromJson),
    );
  }

  Future<FriendRequest> acceptFriendRequest(String requestId) {
    return _requestAction(requestId, 'accept');
  }

  Future<FriendRequest> rejectFriendRequest(String requestId) {
    return _requestAction(requestId, 'reject');
  }

  Future<FriendRequest> cancelFriendRequest(String requestId) {
    return _requestAction(requestId, 'cancel');
  }

  Future<PaginatedResponse<FriendUser>> listFriends() {
    return _apiClient.get<PaginatedResponse<FriendUser>>(
      '/friends',
      queryParameters: const {'limit': 50, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), FriendUser.fromJson),
    );
  }

  Future<void> removeFriend(String userId) {
    return _apiClient.delete<void>('/friends/$userId', parse: (_) {});
  }

  Future<BlockedUser> blockUser(String blockedId) {
    return _apiClient.post<BlockedUser>(
      '/blocks',
      data: {'blocked_id': blockedId},
      parse: (data) => BlockedUser.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<BlockedUser>> listBlocks() {
    return _apiClient.get<PaginatedResponse<BlockedUser>>(
      '/blocks',
      queryParameters: const {'limit': 50, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), BlockedUser.fromJson),
    );
  }

  Future<void> unblockUser(String blockedId) {
    return _apiClient.delete<void>('/blocks/$blockedId', parse: (_) {});
  }

  Future<Conversation> createDirectConversation(String userId) {
    return _apiClient.post<Conversation>(
      '/conversations/direct',
      data: {'user_id': userId},
      parse: (data) => Conversation.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<Conversation>> listConversations() {
    return _apiClient.get<PaginatedResponse<Conversation>>(
      '/conversations',
      queryParameters: const {'limit': 50, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), Conversation.fromJson),
    );
  }

  Future<Conversation> getConversation(String conversationId) {
    return _apiClient.get<Conversation>(
      '/conversations/$conversationId',
      parse: (data) => Conversation.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<Message>> listMessages(String conversationId) {
    return _apiClient.get<PaginatedResponse<Message>>(
      '/conversations/$conversationId/messages',
      queryParameters: const {'limit': 100, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), Message.fromJson),
    );
  }

  Future<Message> sendMessage({
    required String conversationId,
    required String body,
  }) {
    return _apiClient.post<Message>(
      '/conversations/$conversationId/messages',
      data: {'body': body},
      parse: (data) => Message.fromJson(_asMap(data)),
    );
  }

  Future<MarkReadState> markRead(String conversationId) {
    return _apiClient.post<MarkReadState>(
      '/conversations/$conversationId/read',
      parse: (data) => MarkReadState.fromJson(_asMap(data)),
    );
  }

  Future<void> deleteMessage(String messageId) {
    return _apiClient.delete<void>('/messages/$messageId', parse: (_) {});
  }

  Future<FriendRequest> _requestAction(String requestId, String action) {
    return _apiClient.post<FriendRequest>(
      '/friends/requests/$requestId/$action',
      parse: (data) => FriendRequest.fromJson(_asMap(data)),
    );
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }
}
