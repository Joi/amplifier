#!/usr/bin/env python3
"""
Amplifier CLI
"""

import json
import os
import shutil
from datetime import UTC
from pathlib import Path
from typing import Any

import click
import yaml

from amplifier.directory_fetcher import fetch_directory
from amplifier.directory_source import parse_source

# Constants for mode management
COLLECTIONS = ["agents", "commands", "contexts", "tools"]


def get_mode_paths():
    """Get paths for mode management relative to current working directory."""
    project_path = Path.cwd()
    amplifier_path = project_path / ".amplifier"
    amplifier_directory_path = amplifier_path / "directory"
    return project_path, amplifier_path, amplifier_directory_path


def list_modes() -> list[str]:
    """List available modes."""
    _, _, amplifier_directory_path = get_mode_paths()
    modes_dir = amplifier_directory_path / "modes"
    if not modes_dir.exists():
        return []
    modes = [d.name for d in modes_dir.iterdir() if d.is_dir()]
    modes = [m for m in modes if (modes_dir / m / "amplifier.yaml").exists()]
    return modes


def state_from_file() -> dict[str, Any]:
    """Read state from .amplifier/state.json."""
    _, amplifier_path, _ = get_mode_paths()
    state: dict[str, Any] = {"mode": None}

    state_file = amplifier_path / "state.json"
    if not state_file.exists():
        amplifier_path.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f)
        return state

    with open(state_file) as f:
        content = f.read().strip()
        if not content:
            return state
        state = json.loads(content)

    return state


def state_to_file(state: dict[str, Any]) -> None:
    """Write state to .amplifier/state.json."""
    _, amplifier_path, _ = get_mode_paths()
    state_file = amplifier_path / "state.json"
    amplifier_path.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f)


def get_mode_manifest(mode: str) -> dict[str, Any] | None:
    """Get the manifest for a specific mode."""
    _, _, amplifier_directory_path = get_mode_paths()
    mode_file = amplifier_directory_path / "modes" / mode / "amplifier.yaml"
    if not mode_file.exists():
        return None

    with open(mode_file) as f:
        manifest = yaml.safe_load(f)

    return manifest


def get_mode() -> str | None:
    """Get the current active mode."""
    state = state_from_file()
    return state.get("mode", None)


def _target_path(collection: str) -> Path:
    """Get the target path for a collection."""
    project_path, _, _ = get_mode_paths()
    if collection in ["agents", "commands", "tools"]:
        return project_path / ".claude" / collection
    if collection == "contexts":
        return project_path / "ai_context"
    raise ValueError(f"Unknown collection: {collection}")


def dirty_files() -> list[Path]:
    """Check for files that would be overwritten by mode setup."""
    dirt = []
    for collection in COLLECTIONS:
        target_path = _target_path(collection)
        if target_path.exists():
            dirt.append(target_path)
    return dirt


def overlay_claude_settings(manifest: dict[str, Any]) -> None:
    """Apply mode settings to Claude configuration."""
    project_path, _, _ = get_mode_paths()
    claude_settings = {}
    claude_settings_file = project_path / ".claude" / "settings.json"

    if claude_settings_file.exists():
        claude_settings = json.loads(claude_settings_file.read_text())

    if "permissions" not in claude_settings:
        claude_settings["permissions"] = {}

    # Merge some settings
    if "allow" not in claude_settings["permissions"]:
        claude_settings["permissions"]["allow"] = []
    claude_settings["permissions"]["allow"].extend(manifest.get("allow", []))

    if "deny" not in claude_settings["permissions"]:
        claude_settings["permissions"]["deny"] = []
    claude_settings["permissions"]["deny"].extend(manifest.get("deny", []))

    # Overwrite some settings
    if "defaultClaudeMode" in manifest:
        claude_settings["permissions"]["defaultMode"] = manifest.get("defaultClaudeMode")

    if "hooks" in manifest:
        claude_settings["hooks"] = manifest.get("hooks")

    if "mcp" in manifest:
        claude_settings["enabledMcpjsonServers"] = manifest.get("mcp", [])

    claude_settings_file.parent.mkdir(parents=True, exist_ok=True)
    claude_settings_file.write_text(json.dumps(claude_settings, indent=2))


def remove_claude_settings(manifest: dict[str, Any]) -> None:
    """Remove mode settings from Claude configuration."""
    project_path, _, _ = get_mode_paths()
    claude_settings_file = project_path / ".claude" / "settings.json"

    if not claude_settings_file.exists():
        return

    claude_settings = json.loads(claude_settings_file.read_text())

    if "permissions" in claude_settings:
        # Remove specific allow/deny items
        if "allow" in manifest:
            for item in manifest.get("allow", []):
                if item in claude_settings["permissions"].get("allow", []):
                    claude_settings["permissions"]["allow"].remove(item)

        if "deny" in manifest:
            for item in manifest.get("deny", []):
                if item in claude_settings["permissions"].get("deny", []):
                    claude_settings["permissions"]["deny"].remove(item)

        # Reset some settings
        if "defaultMode" in claude_settings["permissions"]:
            del claude_settings["permissions"]["defaultMode"]

    if "hooks" in claude_settings:
        del claude_settings["hooks"]

    if "enabledMcpjsonServers" in claude_settings:
        del claude_settings["enabledMcpjsonServers"]

    claude_settings_file.write_text(json.dumps(claude_settings, indent=2))


def set_mode(mode: str) -> None:
    """Set the current mode."""
    manifest = get_mode_manifest(mode)
    if manifest is None:
        raise ValueError(f"Mode '{mode}' does not exist.")

    state = state_from_file()
    state["manifest"] = manifest
    state["mode"] = ".transitional"
    state_to_file(state)

    dirt = dirty_files()
    if dirt:
        dirt_list = "\n".join([str(d) for d in dirt])
        raise Exception(
            f"The following directories already exist and may contain user data:\n{dirt_list}\nPlease back up and remove these directories before setting a new mode."
        )

    _, _, amplifier_directory_path = get_mode_paths()
    for collection in COLLECTIONS:
        source_path = amplifier_directory_path / collection
        target_path = _target_path(collection)
        for item in manifest.get(collection, []):
            src = source_path / item
            dst = target_path / item
            if not src.exists():
                raise Exception(f"Source path `{src}` does not exist.")
            if dst.exists():
                click.echo(f"Warning: Target path `{dst}` already exists, skipping...")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src)

    overlay_claude_settings(manifest)

    state["mode"] = mode
    state_to_file(state)


def unset_mode() -> None:
    """Unset the current mode."""
    project_path, _, _ = get_mode_paths()
    tool_cache = project_path / ".claude" / "tools" / "__pycache__"
    if tool_cache.exists():
        shutil.rmtree(tool_cache)

    for collection in COLLECTIONS:
        target_path = _target_path(collection)
        if not target_path.exists():
            continue
        for item in target_path.iterdir():
            if item.is_symlink():
                item.unlink()
        if not any(target_path.iterdir()):
            target_path.rmdir()

    state = state_from_file()
    remove_claude_settings(state.get("manifest", {}))
    state["mode"] = None
    state["manifest"] = {}
    state_to_file(state)


@click.command()
@click.option(
    "--target",
    "-t",
    type=click.Path(),
    default=".",
    help="Target directory to copy .amplifier to (defaults to current directory)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing .amplifier directory if it exists",
)
def init(target: str, force: bool) -> None:
    """Copy the .amplifier directory to a target project directory."""

    target_path = Path(target).resolve()
    target_amplifier_dir = target_path / ".amplifier"

    # Check if target directory exists
    if not target_path.exists():
        raise click.ClickException(f"Target directory {target_path} does not exist")

    if not target_path.is_dir():
        raise click.ClickException(f"Target {target_path} is not a directory")

    # Check if .amplifier already exists
    if target_amplifier_dir.exists():
        if not force:
            raise click.ClickException(
                f".amplifier directory already exists at {target_amplifier_dir}. Use --force to overwrite."
            )
        click.echo(f"Removing existing .amplifier directory at {target_amplifier_dir}")
        shutil.rmtree(target_amplifier_dir)

    target_amplifier_dir.mkdir(parents=True, exist_ok=True)

    # Create amplifier.yaml
    amplifier_yaml = target_amplifier_dir / "config.yaml"
    if amplifier_yaml.exists() and not force:
        raise click.ClickException(f"config.yaml already exists at {amplifier_yaml}. Use --force to overwrite.")
    from amplifier.config.config import AmplifierConfig

    default_config = AmplifierConfig.default_config()
    with open(amplifier_yaml, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"✅ Created configuration at {amplifier_yaml}")

    # Fetch the directory content
    original_cwd = Path.cwd()
    try:
        # Change to target directory for fetch operation
        os.chdir(target_path)

        click.echo("📦 Fetching directory content...")

        source = parse_source(default_config["directory"])
        target_directory = target_amplifier_dir / "directory"

        fetch_directory(source, target_directory)

        click.echo(f"✅ Successfully initialized amplifier project at {target_path}")

    except Exception as e:
        click.echo(f"⚠️  Warning: Failed to fetch directory content: {e}", err=True)
        click.echo("You can manually fetch it later with: amplifier fetch-directory")

    finally:
        # Always restore original working directory
        os.chdir(original_cwd)


@click.group(invoke_without_command=True)
@click.pass_context
def mode(ctx):
    """Mode management commands."""
    if ctx.invoked_subcommand is None:
        # No subcommand - show current mode
        current_mode = get_mode()
        if current_mode is None:
            click.echo("No mode set.")
        else:
            click.echo(current_mode)


@mode.command()
def list():
    """List available modes."""
    modes = list_modes()
    for mode_name in modes:
        click.echo(mode_name)


@mode.command()
@click.argument("mode_name", type=str)
def set(mode_name: str):
    """Set the current mode."""
    # Validate mode exists
    available_modes = list_modes()
    if mode_name not in available_modes:
        click.echo(f"Error: Invalid mode '{mode_name}'", err=True)
        click.echo(f"Available modes: {', '.join(available_modes)}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

    try:
        set_mode(mode_name)
    except Exception as e:
        click.echo(f"Error setting mode: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

    click.echo(f"Mode set to: {mode_name}")


@mode.command()
def unset():
    """Unset the current mode."""
    unset_mode()
    click.echo("Mode unset.")


@click.command(name="fetch-directory")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing directory if it exists",
)
def fetch_directory_cmd(force: bool) -> None:
    """Fetch the directory specified in .amplifier/config.yaml."""
    from amplifier.directory_fetcher import fetch_directory as do_fetch
    from amplifier.directory_source import parse_source

    # Get paths
    project_path = Path.cwd()
    amplifier_path = project_path / ".amplifier"
    config_path = amplifier_path / "config.yaml"
    directory_path = amplifier_path / "directory"

    # Check if config exists
    if not config_path.exists():
        raise click.ClickException(f"Config file not found at {config_path}. Run 'amplifier init' first.")

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not config or "directory" not in config:
        raise click.ClickException(
            "No 'directory' entry found in config.yaml. Expected format: directory: git+username/repo/path"
        )

    # Check if directory already exists
    if directory_path.exists() and not force:
        raise click.ClickException(f"Directory already exists at {directory_path}. Use --force to overwrite.")

    # Parse source
    try:
        source_info = parse_source(config["directory"])
    except ValueError as e:
        raise click.ClickException(f"Invalid directory source: {e}")

    # Fetch the directory
    try:
        click.echo(f"Fetching directory from {config['directory']}...")
        do_fetch(source_info, directory_path)
        click.echo(f"Successfully fetched directory to {directory_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to fetch directory: {e}")


@click.group()
def main() -> None:
    """Amplifier CLI - Tools for AI-powered productivity."""
    pass


# Transcript commands
@click.group(name="transcript")
def transcript_cmd() -> None:
    """Manage conversation transcripts."""
    pass


@transcript_cmd.command(name="list")
@click.option("--last", type=int, help="Show last N transcripts")
@click.option("--json", is_flag=True, help="Output as JSON")
def transcript_list(last: int | None, json: bool) -> None:
    """List available conversation transcripts."""
    from amplifier.transcript import TranscriptManager

    manager = TranscriptManager()

    if json:
        click.echo(manager.list_transcripts_json(last_n=last))
    else:
        transcripts = manager.list_transcripts(last_n=last)
        if not transcripts:
            click.echo("No transcripts found")
        else:
            for t in transcripts:
                # Extract session ID
                import re
                from datetime import datetime

                match = re.search(r"compact_\d+_\d+_([a-f0-9-]+)\.txt", t.name)
                session_id = match.group(1) if match else "unknown"

                mtime = datetime.fromtimestamp(t.stat().st_mtime, tz=UTC)
                size_kb = t.stat().st_size / 1024
                click.echo(f"{session_id[:8]}... | {mtime.strftime('%Y-%m-%d %H:%M')} | {size_kb:.1f}KB | {t.name}")


@transcript_cmd.command(name="load")
@click.argument("session_id")
def transcript_load(session_id: str) -> None:
    """Load and output a specific transcript."""
    from amplifier.transcript import TranscriptManager

    manager = TranscriptManager()
    content = manager.load_transcript_content(session_id)

    if content:
        click.echo(content)
    else:
        click.echo(f"Error: Transcript not found for '{session_id}'", err=True)
        raise click.ClickException("Transcript not found")


@transcript_cmd.command(name="search")
@click.argument("term")
@click.option("--max", "max_results", type=int, default=10, help="Maximum results")
def transcript_search(term: str, max_results: int) -> None:
    """Search transcripts for a term."""
    from amplifier.transcript import TranscriptManager

    manager = TranscriptManager()
    results = manager.search_transcripts(term, max_results=max_results)

    if results:
        click.echo(results)
    else:
        click.echo(f"No matches found for '{term}'")


@transcript_cmd.command(name="restore")
@click.option("--session-id", help="Session ID to restore (default: current/latest)")
def transcript_restore(session_id: str | None) -> None:
    """Restore entire conversation lineage."""
    from amplifier.transcript import TranscriptManager

    manager = TranscriptManager()
    content = manager.restore_conversation_lineage(session_id=session_id)

    if content:
        click.echo(content)
    else:
        click.echo("Error: No transcripts found to restore", err=True)
        raise click.ClickException("No transcripts found")


@transcript_cmd.command(name="export")
@click.option("--session-id", help="Session ID to export (default: current)")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "markdown"]), default="text", help="Export format"
)
def transcript_export(session_id: str | None, output_format: str) -> None:
    """Export transcript to file."""
    from amplifier.transcript import TranscriptManager

    manager = TranscriptManager()
    output_file = manager.export_transcript(session_id=session_id, output_format=output_format)

    if output_file:
        click.echo(f"Exported to: {output_file}")
    else:
        click.echo("Error: Failed to export transcript", err=True)
        raise click.ClickException("Export failed")


@click.group(name="worktree")
def worktree_cmd() -> None:
    """Manage git worktrees for parallel development."""
    pass


@worktree_cmd.command(name="create")
@click.argument("branch_name")
@click.option("--adopt-remote", is_flag=True, help="Create from remote branch")
@click.option("--eval", "eval_mode", is_flag=True, help="Output for shell evaluation")
def worktree_create(branch_name: str, adopt_remote: bool, eval_mode: bool) -> None:
    """Create a new worktree for a branch."""
    from amplifier.worktree import copy_data_directory
    from amplifier.worktree import create_worktree
    from amplifier.worktree import setup_worktree_venv

    # Create the worktree
    worktree_path = create_worktree(branch_name, adopt_remote, eval_mode)

    # Copy .data directory if it exists
    data_dir = Path.cwd() / ".data"
    if data_dir.exists():
        target_data_dir = worktree_path / ".data"
        copy_data_directory(data_dir, target_data_dir, eval_mode)

    # Set up virtual environment
    venv_created = setup_worktree_venv(worktree_path, eval_mode)

    # Output based on mode
    if eval_mode:
        if venv_created:
            print(f"cd {worktree_path} && source .venv/bin/activate && echo '\\n✓ Switched to worktree'")
        else:
            print(f"cd {worktree_path} && echo '\\n✓ Switched to worktree (run make install to set up)'")
    else:
        print("\\n✓ Worktree created successfully!")
        print(f"  📁 Location: {worktree_path}")
        if venv_created:
            print("  🐍 Virtual environment: Ready")
        else:
            print("  ⚠️  Virtual environment: Setup required")

        print("\\n" + "─" * 60)
        print("To switch to your new worktree, run:")
        print("─" * 60)
        print(f"\\ncd {worktree_path}")
        if venv_created:
            print("source .venv/bin/activate")
        else:
            print("make install  # Set up virtual environment")
            print("source .venv/bin/activate")


@worktree_cmd.command(name="remove")
@click.argument("branch_name")
@click.option("--force", is_flag=True, help="Force removal even with uncommitted changes")
def worktree_remove(branch_name: str, force: bool) -> None:
    """Remove a worktree and optionally its branch."""
    from amplifier.worktree import remove_worktree

    remove_worktree(branch_name, force)


@worktree_cmd.command(name="list")
def worktree_list() -> None:
    """List all git worktrees."""
    from amplifier.worktree import list_worktrees

    worktrees = list_worktrees()

    if not worktrees:
        click.echo("No worktrees found.")
        return

    click.echo("Git worktrees:")
    for wt in worktrees:
        branch = wt.get("branch", "detached")
        click.echo(f"  {wt['path']}")
        click.echo(f"    Branch: {branch}")
        click.echo(f"    Commit: {wt.get('commit', 'unknown')[:8]}")


@worktree_cmd.command(name="stash")
@click.argument("feature_name")
def worktree_stash(feature_name: str) -> None:
    """Hide a worktree from git tracking without deleting it."""
    from amplifier.worktree import WorktreeManager

    manager = WorktreeManager()
    manager.stash_by_name(feature_name)


@worktree_cmd.command(name="unstash")
@click.argument("feature_name")
def worktree_unstash(feature_name: str) -> None:
    """Restore a stashed worktree back to git tracking."""
    from amplifier.worktree import WorktreeManager

    manager = WorktreeManager()
    manager.unstash_by_name(feature_name)


@worktree_cmd.command(name="adopt")
@click.argument("branch_name")
@click.option("--name", "worktree_name", help="Custom worktree directory name")
def worktree_adopt(branch_name: str, worktree_name: str | None) -> None:
    """Create local worktree from remote branch."""
    from amplifier.worktree import WorktreeManager

    manager = WorktreeManager()
    manager.adopt(branch_name, worktree_name)


@worktree_cmd.command(name="list-stashed")
def worktree_list_stashed() -> None:
    """List all stashed worktrees."""
    from amplifier.worktree import WorktreeManager

    manager = WorktreeManager()
    stashed = manager.list_stashed()

    if not stashed:
        click.echo("No stashed worktrees.")
        return

    click.echo("Stashed worktrees:")
    for entry in stashed:
        click.echo(f"  {entry['path']}")
        click.echo(f"    Branch: {entry.get('branch', 'unknown')}")


main.add_command(init)
main.add_command(mode)
main.add_command(fetch_directory_cmd)
main.add_command(transcript_cmd)
main.add_command(worktree_cmd)


if __name__ == "__main__":
    main()
