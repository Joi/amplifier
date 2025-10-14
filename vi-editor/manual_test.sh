#!/bin/bash

# Manual test script for vi editor
echo "Manual Vi Editor Test"
echo "====================="
echo ""
echo "This will open the vi editor with test.txt"
echo "Try the following:"
echo "  1. Press 'i' to enter insert mode (should show INSERT at bottom)"
echo "  2. Type some text"
echo "  3. Press ESC to exit insert mode"
echo "  4. Type ':wq' and press ENTER to save and quit"
echo ""
echo "Press ENTER to start..."
read

# Clean up any swap files
rm -f .*.swp *.swp

# Create test file
echo "Hello World" > test.txt

# Run the editor
python -m vi_editor.main test.txt

# Check result
echo ""
echo "File content after editing:"
cat test.txt