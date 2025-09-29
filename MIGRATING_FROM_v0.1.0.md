# Migrating to Amplifier 0.2.0 from 0.1.0

## Big changes

1. This changes the model from "work on projects in amplifier" to "bring amplifier to your projects".
2. Splits "core" amplifier out of configuration by creating an "official directory" of amplifier resources.
3. Also, you can have multiple different "modes" of amplifier. A mode is a set of (.claude) subagents, hooks, commands, tools, and context files that go together. The one we've been using has been added as a "python-coder" mode, but now modes can be custom and community-contributed.
4. Configuration has been migrated from `.env` to `.amplifier/config.yaml`.
5. This introduces an `amplifier` cli that allows initializing amplifier in an existing project directory and selecting which mode you want amplifier to be in.

## Migrating from v0.1.0

- Pull amplifier repo.
- Create backups of your existing amplifier files that will be stomped on my our new modal features. You can reference these to move more things around if you need.
  - ```bash
    mkdir backup
    mv .claude backup/.claude
    mv CLAUDE.md backup/CLAUDE.md
    mv AGENTS.md backup/AGENTS.md
    mv ai_context backup/ai_context
    mv .env backup/.env
    mv .env.example backup/.env.example
    ```
- Make sure uv env is activated: `source .venv/bin/activate`
- Install the amplifier script: `uv pip install -e .`
- Initialize 0.2.0: `amplifier init`. This creates the `.amplifier` directory in your project.
- If you customized any of the config in `.env` update your values in the new config file at `.amplifier/config.yaml`. Note: You can still override config.yaml config with env vars in the form of `AMPLIFIER__NESTED__CONFIG_VALUE` type keys (they map to what is in the config.yaml).
- Until we get the directory into `main`, you won't be able to git it, so until then, update your directory in `.amplifier/config.yaml`  to be the path to the `directory` folder, and then run: `amplifier fetch-directory` to have the directory cached/copied into your `.amplifier` directory.
- Change to python coder mode: `amplifier mode set python-coder`. This will re-create your .claude directory.

## Other things to know.

- worktree and transcript tools have been moved out of the `Makefile` and put in the `amplifier` cli (see `amplifier --help`).
- `tools` have been moved into the directory and, after fetching, can now be called with `uv run python .amplifier/directory/tools/<tool.py>`
