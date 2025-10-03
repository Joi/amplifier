# /mode - Natural Language Mode Management

Unified command for all mode operations. I'll analyze your request and execute the appropriate `amplifier` command.

Read @amplifier-context/AMPLIFIER_CLI.md

## Operation

- Analyze the input in `$ARGUMENTS` to find out what the user wants to do w.r.t. amplifier mode management.
- When intent cannot be determined, figure out what additional information you need from the user and ask them for it.
- Select which amplifier commands are necessary to accomplish the user's intent. The commands available are:
  ```
  uv run amplifier mode create <mode-name>
  uv run amplifier mode list
  uv run amplifier mode
  uv run amplifier mode freeze
  uv run directory refresh --force
  ```
-  Properly format the commands to be executed.
- Execute the commands.
- Tell the user what was accomplished.

---

Now I'll analyze "$ARGUMENTS" and execute the appropriate mode operations.
