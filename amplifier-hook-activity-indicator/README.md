# amplifier-hook-activity-indicator

Shows a spinner during long-running Amplifier operations to indicate the system isn't frozen.

## Features

- ⠋ Animated braille spinner
- Shows "thinking..." during LLM requests
- Shows "running <tool>..." during tool execution
- Thread-safe, clears cleanly on completion

## Installation

Add to your bundle:

```yaml
hooks:
  - module: hook-activity-indicator
    source: file:///mnt/c/git/amplifier-hook-activity-indicator
```

Or via git:

```yaml
hooks:
  - module: hook-activity-indicator
    source: git+https://github.com/YOUR_USERNAME/amplifier-hook-activity-indicator@main
```
