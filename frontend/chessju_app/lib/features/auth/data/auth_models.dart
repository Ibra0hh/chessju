class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
  });

  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;

  factory AuthTokens.fromJson(Map<String, Object?> json) {
    return AuthTokens(
      accessToken: json['access_token']?.toString() ?? '',
      refreshToken: json['refresh_token']?.toString() ?? '',
      tokenType: json['token_type']?.toString() ?? 'bearer',
      expiresIn: _asInt(json['expires_in']),
    );
  }

  Map<String, String> toStorageJson() {
    return {
      'access_token': accessToken,
      'refresh_token': refreshToken,
      'token_type': tokenType,
      'expires_in': expiresIn.toString(),
    };
  }

  factory AuthTokens.fromStorageJson(Map<String, String> json) {
    return AuthTokens(
      accessToken: json['access_token'] ?? '',
      refreshToken: json['refresh_token'] ?? '',
      tokenType: json['token_type'] ?? 'bearer',
      expiresIn: int.tryParse(json['expires_in'] ?? '') ?? 0,
    );
  }
}

class CurrentUser {
  const CurrentUser({
    required this.id,
    required this.email,
    required this.status,
    required this.roles,
    required this.profile,
    required this.preferences,
  });

  final String id;
  final String email;
  final String status;
  final List<String> roles;
  final UserProfile profile;
  final UserPreferences preferences;

  factory CurrentUser.fromJson(Map<String, Object?> json) {
    return CurrentUser(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      roles: (json['roles'] as List? ?? const [])
          .map((role) => role.toString())
          .toList(),
      profile: UserProfile.fromJson(
        Map<String, Object?>.from(json['profile'] as Map? ?? const {}),
      ),
      preferences: UserPreferences.fromJson(
        Map<String, Object?>.from(json['preferences'] as Map? ?? const {}),
      ),
    );
  }
}

class UserProfile {
  const UserProfile({
    required this.id,
    required this.userId,
    required this.username,
    required this.fullName,
    this.universityId,
    this.avatarFileId,
    this.bio,
    this.chesscomUsername,
  });

  final String id;
  final String userId;
  final String username;
  final String fullName;
  final String? universityId;
  final String? avatarFileId;
  final String? bio;
  final String? chesscomUsername;

  factory UserProfile.fromJson(Map<String, Object?> json) {
    return UserProfile(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      universityId: json['university_id']?.toString(),
      avatarFileId: json['avatar_file_id']?.toString(),
      bio: json['bio']?.toString(),
      chesscomUsername: json['chesscom_username']?.toString(),
    );
  }
}

class UserPreferences {
  const UserPreferences({
    required this.userId,
    required this.appTheme,
    required this.boardTheme,
    required this.accentColor,
    required this.clockSoundEnabled,
    required this.language,
  });

  final String userId;
  final String appTheme;
  final String boardTheme;
  final String accentColor;
  final bool clockSoundEnabled;
  final String language;

  factory UserPreferences.fromJson(Map<String, Object?> json) {
    return UserPreferences(
      userId: json['user_id']?.toString() ?? '',
      appTheme: json['app_theme']?.toString() ?? 'system',
      boardTheme: json['board_theme']?.toString() ?? 'classic',
      accentColor: json['accent_color']?.toString() ?? 'blue',
      clockSoundEnabled: json['clock_sound_enabled'] != false,
      language: json['language']?.toString() ?? 'en',
    );
  }
}

class AuthResponse {
  const AuthResponse({required this.tokens, required this.user});

  final AuthTokens tokens;
  final CurrentUser user;

  factory AuthResponse.fromJson(Map<String, Object?> json) {
    return AuthResponse(
      tokens: AuthTokens.fromJson(
        Map<String, Object?>.from(json['tokens'] as Map? ?? const {}),
      ),
      user: CurrentUser.fromJson(
        Map<String, Object?>.from(json['user'] as Map? ?? const {}),
      ),
    );
  }
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
