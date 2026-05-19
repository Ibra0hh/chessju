class SocialUser {
  const SocialUser({
    required this.id,
    required this.username,
    required this.fullName,
    this.avatarFileId,
  });

  final String id;
  final String username;
  final String fullName;
  final String? avatarFileId;

  String get displayName => fullName.isNotEmpty ? fullName : username;

  factory SocialUser.fromJson(Map<String, Object?> json) {
    return SocialUser(
      id: json['id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      avatarFileId: json['avatar_file_id']?.toString(),
    );
  }
}

class FriendRequest {
  const FriendRequest({
    required this.id,
    required this.sender,
    required this.receiver,
    required this.status,
    required this.createdAt,
    this.respondedAt,
  });

  final String id;
  final SocialUser sender;
  final SocialUser receiver;
  final String status;
  final String createdAt;
  final String? respondedAt;

  factory FriendRequest.fromJson(Map<String, Object?> json) {
    return FriendRequest(
      id: json['id']?.toString() ?? '',
      sender: SocialUser.fromJson(_asMap(json['sender'])),
      receiver: SocialUser.fromJson(_asMap(json['receiver'])),
      status: json['status']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
      respondedAt: json['responded_at']?.toString(),
    );
  }
}

class FriendUser extends SocialUser {
  const FriendUser({
    required super.id,
    required super.username,
    required super.fullName,
    super.avatarFileId,
    required this.friendshipId,
    required this.createdAt,
  });

  final String friendshipId;
  final String createdAt;

  factory FriendUser.fromJson(Map<String, Object?> json) {
    return FriendUser(
      id: json['id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      avatarFileId: json['avatar_file_id']?.toString(),
      friendshipId: json['friendship_id']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

class BlockedUser {
  const BlockedUser({
    required this.id,
    required this.blockedUser,
    required this.createdAt,
  });

  final String id;
  final SocialUser blockedUser;
  final String createdAt;

  factory BlockedUser.fromJson(Map<String, Object?> json) {
    return BlockedUser(
      id: json['id']?.toString() ?? '',
      blockedUser: SocialUser.fromJson(_asMap(json['blocked_user'])),
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

class ConversationMember {
  const ConversationMember({
    required this.user,
    required this.role,
    required this.joinedAt,
    this.leftAt,
  });

  final SocialUser user;
  final String role;
  final String joinedAt;
  final String? leftAt;

  factory ConversationMember.fromJson(Map<String, Object?> json) {
    return ConversationMember(
      user: SocialUser.fromJson(_asMap(json['user'])),
      role: json['role']?.toString() ?? 'member',
      joinedAt: json['joined_at']?.toString() ?? '',
      leftAt: json['left_at']?.toString(),
    );
  }
}

class Message {
  const Message({
    required this.id,
    required this.conversationId,
    required this.sender,
    this.body,
    required this.messageType,
    required this.createdAt,
    this.editedAt,
    this.deletedAt,
  });

  final String id;
  final String conversationId;
  final SocialUser sender;
  final String? body;
  final String messageType;
  final String createdAt;
  final String? editedAt;
  final String? deletedAt;

  bool get isDeleted => deletedAt != null;

  factory Message.fromJson(Map<String, Object?> json) {
    return Message(
      id: json['id']?.toString() ?? '',
      conversationId: json['conversation_id']?.toString() ?? '',
      sender: SocialUser.fromJson(_asMap(json['sender'])),
      body: json['body']?.toString(),
      messageType: json['message_type']?.toString() ?? 'text',
      createdAt: json['created_at']?.toString() ?? '',
      editedAt: json['edited_at']?.toString(),
      deletedAt: json['deleted_at']?.toString(),
    );
  }
}

class Conversation {
  const Conversation({
    required this.id,
    required this.type,
    required this.members,
    this.lastMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String type;
  final List<ConversationMember> members;
  final Message? lastMessage;
  final String createdAt;
  final String updatedAt;

  SocialUser? otherMember(String? currentUserId) {
    for (final member in members) {
      if (member.user.id != currentUserId) {
        return member.user;
      }
    }
    return members.isEmpty ? null : members.first.user;
  }

  factory Conversation.fromJson(Map<String, Object?> json) {
    return Conversation(
      id: json['id']?.toString() ?? '',
      type: json['type']?.toString() ?? 'direct',
      members: _list(json['members'], ConversationMember.fromJson),
      lastMessage: json['last_message'] is Map
          ? Message.fromJson(_asMap(json['last_message']))
          : null,
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }
}

class MarkReadState {
  const MarkReadState({
    required this.conversationId,
    required this.readCount,
    required this.readAt,
  });

  final String conversationId;
  final int readCount;
  final String readAt;

  factory MarkReadState.fromJson(Map<String, Object?> json) {
    return MarkReadState(
      conversationId: json['conversation_id']?.toString() ?? '',
      readCount: _asInt(json['read_count']),
      readAt: json['read_at']?.toString() ?? '',
    );
  }
}

String? validateMessageBody(String? value) {
  final normalized = value?.trim() ?? '';
  if (normalized.isEmpty) {
    return 'Message cannot be empty';
  }
  if (normalized.length > 2000) {
    return 'Message must be 2000 characters or fewer';
  }
  return null;
}

Map<String, Object?> _asMap(Object? value) {
  return Map<String, Object?>.from(value as Map? ?? const {});
}

List<T> _list<T>(Object? value, T Function(Map<String, Object?> json) parse) {
  if (value is! List) {
    return const [];
  }
  return value
      .whereType<Map>()
      .map((item) => parse(Map<String, Object?>.from(item)))
      .toList();
}

int _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
