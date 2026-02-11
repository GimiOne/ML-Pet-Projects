import 'package:flutter/material.dart';

void main() {
  runApp(const TodoApp());
}

class TodoApp extends StatelessWidget {
  const TodoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Todo App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const TodoScreen(),
    );
  }
}

class TodoScreen extends StatefulWidget {
  const TodoScreen({super.key});

  @override
  State<TodoScreen> createState() => _TodoScreenState();
}

class _TodoScreenState extends State<TodoScreen> {
  // Список задач
  final List<TodoItem> _todos = [];

  // Контроллер для текстового поля
  final TextEditingController _textController = TextEditingController();

  // Список для отслеживания, какие задачи редактируются
  final Set<int> _editingIndexes = {};

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  // Добавление новой задачи (CREATE)
  void _addTodo() {
    if (_textController.text.trim().isEmpty) return;

    setState(() {
      _todos.add(TodoItem(
        title: _textController.text.trim(),
        createdAt: DateTime.now(),
      ));
      _textController.clear();
    });
  }

  // Удаление задачи (DELETE)
  void _deleteTodo(int index) {
    setState(() {
      _todos.removeAt(index);
    });
  }

  // Начать редактирование задачи
  void _startEditing(int index, String currentTitle) {
    setState(() {
      _editingIndexes.add(index);
    });
    _textController.text = currentTitle;
  }

  // Сохранить редактирование (UPDATE)
  void _saveEdit(int index) {
    if (_textController.text.trim().isEmpty) return;

    setState(() {
      _todos[index].title = _textController.text.trim();
      _editingIndexes.remove(index);
      _textController.clear();
    });
  }

  // Отменить редактирование
  void _cancelEdit(int index) {
    setState(() {
      _editingIndexes.remove(index);
      _textController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Todo List'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          // Текстовое поле для ввода задач
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    decoration: InputDecoration(
                      hintText: 'Введите новую задачу',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      filled: true,
                      fillColor: Colors.grey[100],
                    ),
                    onSubmitted: (_) => _addTodo(),
                  ),
                ),
                const SizedBox(width: 12),
                IconButton(
                  onPressed: _addTodo,
                  icon: const Icon(Icons.add_circle),
                  iconSize: 40,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ],
            ),
          ),

          // Список задач используя ListView.builder
          Expanded(
            child: _todos.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.task_alt,
                          size: 80,
                          color: Colors.grey,
                        ),
                        SizedBox(height: 16),
                        Text(
                          'Нет задач',
                          style: TextStyle(
                            fontSize: 20,
                            color: Colors.grey,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Добавьте первую задачу!',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _todos.length,
                    itemBuilder: (context, index) {
                      final todo = _todos[index];
                      final isEditing = _editingIndexes.contains(index);

                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        elevation: 2,
                        child: ListTile(
                          // РЕДАКТИРОВАНИЕ (UPDATE) - режим редактирования
                          title: isEditing
                              ? Row(
                                  children: [
                                    Expanded(
                                      child: TextField(
                                        controller: _textController,
                                        decoration: InputDecoration(
                                          hintText: 'Редактировать задачу',
                                          border: OutlineInputBorder(
                                            borderRadius:
                                                BorderRadius.circular(8),
                                          ),
                                          contentPadding:
                                              const EdgeInsets.symmetric(
                                            horizontal: 12,
                                            vertical: 8,
                                          ),
                                        ),
                                        autofocus: true,
                                      ),
                                    ),
                                    IconButton(
                                      onPressed: () => _saveEdit(index),
                                      icon: const Icon(Icons.check),
                                      color: Colors.green,
                                    ),
                                    IconButton(
                                      onPressed: () => _cancelEdit(index),
                                      icon: const Icon(Icons.close),
                                      color: Colors.red,
                                    ),
                                  ],
                                )
                              : Text(
                                  todo.title,
                                  style: const TextStyle(fontSize: 16),
                                ),

                          // Кнопки действий (DELETE, UPDATE)
                          trailing: isEditing
                              ? null
                              : Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    // Кнопка редактирования
                                    IconButton(
                                      onPressed: () => _startEditing(
                                          index, todo.title),
                                      icon: const Icon(Icons.edit),
                                      color: Colors.blue,
                                    ),
                                    // Кнопка удаления
                                    IconButton(
                                      onPressed: () => _deleteTodo(index),
                                      icon: const Icon(Icons.delete),
                                      color: Colors.red,
                                    ),
                                  ],
                                ),

                          // Отображение времени создания
                          subtitle: isEditing
                              ? null
                              : Text(
                                  'Создано: ${_formatDate(todo.createdAt)}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.grey[600],
                                  ),
                                ),
                        ),
                      );
                    },
                  ),
          ),

          // Статистика
          if (_todos.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Column(
                    children: [
                      Text(
                        '${_todos.length}',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Text('Всего задач'),
                    ],
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // Форматирование даты
  String _formatDate(DateTime date) {
    return '${date.day.toString().padLeft(2, '0')}.'
        '${date.month.toString().padLeft(2, '0')}.'
        '${date.year} '
        '${date.hour.toString().padLeft(2, '0')}:'
        '${date.minute.toString().padLeft(2, '0')}';
  }
}

// Модель задачи
class TodoItem {
  String title;
  final DateTime createdAt;

  TodoItem({
    required this.title,
    required this.createdAt,
  });
}
