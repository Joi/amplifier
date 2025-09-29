# Amplifier

## Install

Prereq:

- Install uv w/ python 3.11, node, claude-code

In your project directory:

```bash
uv init
uv add amplifier
uvx amplifier init # copies .amplifier directory
source .amplifier/bin/activate

amplifier --help
amplifier mode list
amplifier mode set <name>
amplifier mode unset <name>
amplifier update
amplifier remove
```

## Customization

```bash
amplifier mode clone <old> <new> # old can be name, path, git-uri
amplifier mode freeze <name> # Copies official into custom
```

## Talk to the assistant

![alt text](make-the-assistant-able-to-run-amplifier-cmds.png)

### Examples

> I'd like a new mode based on the python-coder mode. Freeze it though.
