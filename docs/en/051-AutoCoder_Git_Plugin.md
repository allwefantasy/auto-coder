# Git Helper Plugin User Guide

The Git Helper plugin is one of AutoCoder's built-in plugins, serving as a teaching example demonstrating how core plugin functionality is implemented. At the same time, the Git Helper plugin also provides some practical features to help developers manage Git repositories more conveniently.

Below is a detailed guide to using the Git Helper plugin.

## Plugin Loading and Unloading

```bash
# View loaded plugins
coding@auto-coder.chat:~$ /plugins
Loaded Plugins:

# List available plugins
coding@auto-coder.chat:~$ /plugins /list
Available Plugins:
- GitHelperPlugin (git_helper): Git helper plugin providing Git commands and status
...

# Load Git Helper plugin
coding@auto-coder.chat:~$ /plugins /load git_helper
Plugin 'git_helper' (v0.1.0) loaded successfully

# Verify load status
coding@auto-coder.chat:~$ /plugins
Loaded Plugins:
- git_helper (v0.1.0): Git helper plugin providing Git commands and status

# Unload plugin - if you need to unload the plugin, use the following command. 
# After unloading, the plugin will not be available the next time you enter auto-coder-chat
coding@auto-coder.chat:~$ /plugins /unload git_helper
Plugin 'git_helper' unloaded successfully
```

## Core Command List

```bash
coding@auto-coder.chat:~$ /git/status       # Show repository status
coding@auto-coder.chat:~$ /git/commit "fix login bug"  # Commit all changes
coding@auto-coder.chat:~$ /git/branch       # Display branch list
coding@auto-coder.chat:~$ /git/checkout main  # Switch to main branch
coding@auto-coder.chat:~$ /git/diff         # Show current differences
coding@auto-coder.chat:~$ /git/log          # Show concise commit history (default last 10)
coding@auto-coder.chat:~$ /git/pull         # Pull remote updates
coding@auto-coder.chat:~$ /git/push         # Push local commits
coding@auto-coder.chat:~$ /git/reset hard   # Hard reset to latest commit
```

## Intelligent Completion Demo

```bash
# Press space to trigger completions when entering commands
coding@auto-coder.chat:~$ /git/reset[space]
hard    soft    mixed

coding@auto-coder.chat:~$ /git/checkout[space]
main    dev     feature/login

```

## Usage Examples

### Typical Workflow
```bash
coding@auto-coder.chat:~$ /git/status
On branch main
Changes not staged for commit:
  modified:   src/main.py

coding@auto-coder.chat:~$ /git/commit Optimize user authentication logic
[main a1b2c3d] Optimize user authentication logic
 1 file changed, 3 insertions(+)

coding@auto-coder.chat:~$ /git/push
Enumerating objects: 5, done.
Writing objects: 100% (3/3), 401 bytes | 401.00 KiB/s, done.
```

### Branch Management
```bash
coding@auto-coder.chat:~$ /git/branch --all
* main
  remotes/origin/HEAD -> origin/main
  remotes/origin/dev

coding@auto-coder.chat:~$ /git/checkout -b feature/search
Switched to a new branch 'feature/search'

coding@auto-coder.chat:~$ /git/push --set-upstream origin feature/search
Branch 'feature/search' set up to track remote branch 'feature/search' from 'origin'.
```

## Advanced Usage

### Custom Log Format
```bash
# Note: Complex format strings may need adjusted quote handling, please adjust based on actual situation or use terminal command line
coding@auto-coder.chat:~$ /git/log --graph --oneline
* a1b2c3d (HEAD -> main) Optimize user authentication logic
* d4e5f6a (origin/dev) Fix page layout issues

# Or use simple preset format options
coding@auto-coder.chat:~$ /git/log --pretty=oneline --abbrev-commit
a1b2c3d Optimize user authentication logic
d4e5f6a Fix page layout issues
```

### Diff Comparison
```bash
coding@auto-coder.chat:~$ /git/diff HEAD~1
diff --git a/src/main.py b/src/main.py
index 5d9e6b7..a1b2c3d 100644
--- a/src/main.py
+++ b/src/main.py
@@ -12,6 +12,7 @@ def authenticate(username, password):
     # Add two-factor authentication
     if user:
         send_verification_code(user.phone)
+        log_auth_attempt(username)
     return user
```

## Important Notes

1. Automatically executes `git add .` before committing
2. Consider committing or stashing important changes before using `/git/reset`
3. Standard git parameters are supported, such as `/git/log -n 20 --graph`
4. Enter `/git/command --help` to view more detailed help for Git commands 