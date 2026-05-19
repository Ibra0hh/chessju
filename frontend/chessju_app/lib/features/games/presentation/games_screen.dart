import 'package:flutter/material.dart';

class GamesScreen extends StatelessWidget {
  const GamesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Games', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 16),
        const Card(
          child: ListTile(
            leading: Icon(Icons.grid_on_outlined),
            title: Text('Game library'),
            subtitle: Text(
              'PGN replay and Stockfish analysis screens will build on the existing backend endpoints.',
            ),
          ),
        ),
      ],
    );
  }
}
