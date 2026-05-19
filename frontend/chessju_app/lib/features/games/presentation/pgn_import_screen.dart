import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/games/data/games_repository.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class PgnImportScreen extends ConsumerStatefulWidget {
  const PgnImportScreen({super.key});

  @override
  ConsumerState<PgnImportScreen> createState() => _PgnImportScreenState();
}

class _PgnImportScreenState extends ConsumerState<PgnImportScreen> {
  final _formKey = GlobalKey<FormState>();
  final _controller = TextEditingController();
  bool _submitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Import PGN', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text(
          'Paste one PGN game. ChessJU will validate it and create replay data.',
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    key: const ValueKey('pgn-paste-field'),
                    controller: _controller,
                    minLines: 10,
                    maxLines: 18,
                    decoration: const InputDecoration(
                      labelText: 'PGN text',
                      alignLabelWithHint: true,
                    ),
                    validator: validatePgnText,
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _errorMessage!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  PrimaryButton(
                    label: 'Import game',
                    icon: Icons.upload_file_outlined,
                    loading: _submitting,
                    onPressed: _submit,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const ContentCard(
          title: 'File upload',
          subtitle:
              'PGN file upload is supported by the backend and will be added to the Flutter UI after file picker behavior is finalized for each platform.',
          leading: Icon(Icons.attach_file),
        ),
      ],
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    try {
      final game = await ref
          .read(gamesRepositoryProvider)
          .pastePgn(_controller.text.trim());
      if (!mounted) {
        return;
      }
      ref.invalidate(gameListProvider(null));
      context.go('/games/${game.id}');
    } on ApiException catch (exception) {
      setState(() {
        _errorMessage = exception.error.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }
}

String? validatePgnText(String? value) {
  if (value == null || value.trim().isEmpty) {
    return 'Paste a PGN game first';
  }
  return null;
}
