# Test what vim does with p command
# In vim:
# - Start with "hello world"
# - Position cursor on 'o' (position 4)
# - Yank "TEXT"
# - Paste with p
# - Check cursor position

# The result should be "helloTEXT world"
# Question: where does cursor end up?

# From vim documentation:
# p - Put the text after the cursor. The cursor is left on the LAST character of the inserted text.
# So if we paste "TEXT", cursor should be on the last 'T' at position 8

# But our test expects position 9 (the space after TEXT)
# This might be a test bug, or maybe there's a special case?

print("Vim behavior for 'p' command:")
print("- Cursor should be on LAST character of pasted text")
print("- For 'TEXT' pasted after position 4: cursor should be at position 8 (last 'T')")
print("- Test expects position 9 (space after 'TEXT')")
print("")
print("This seems like the test expectation might be wrong, OR")
print("the test is testing a different scenario than standard vim 'p' command")
