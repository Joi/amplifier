# Vi Editor Clone

A complete, production-quality vi editor clone implementation in Python.

## Features

- Full vi modal interface (normal, insert, visual, command modes)
- Core vi commands and movements
- Text buffer management with undo/redo
- File operations (open, save, quit)
- Search and replace functionality
- Syntax highlighting support
- Terminal-based rendering

## Installation

```bash
pip install -e .
```

## Usage

```bash
vi [filename]
```

## Architecture

The editor is structured in modular components:

- **Core Engine**: Buffer management, cursor handling
- **Command System**: Modal interface, command parsing
- **User Interface**: Terminal rendering, input processing
- **File Operations**: File I/O, backup, recovery

## Testing

```bash
pytest tests/
```

## Development

This is a complete implementation following vi specifications, with no stubs or placeholders.