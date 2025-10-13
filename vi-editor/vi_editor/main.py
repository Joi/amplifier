"""Main entry point for vi editor."""

import argparse
import sys

from vi_editor.editor import Editor


def main():
    """Main entry point for the vi editor."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Vi Editor Clone")
    parser.add_argument("file", nargs="?", help="File to edit")
    parser.add_argument("-r", "--recover", action="store_true", help="Recover file from swap")
    parser.add_argument("-R", "--readonly", action="store_true", help="Open file in read-only mode")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")

    args = parser.parse_args()

    # Handle version flag
    if args.version:
        print("Vi Editor Clone v0.1.0")
        print("A complete vi implementation in Python")
        sys.exit(0)

    # Create editor instance
    editor = Editor()

    # Handle recovery mode
    if args.recover and args.file:
        # TODO: Implement recovery
        pass

    # Handle read-only mode
    if args.readonly:
        editor.state.set_config("readonly", True)

    # Open file if specified
    if args.file:
        editor.open_file(args.file)

    # Run the editor
    try:
        editor.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
