# Git 助手插件使用指南

Git助手插件是 AutoCoder 内置的插件之一，作为一个插件的教学例子，演示了插件的核心功能如何实现。同时，Git助手插件也提供了一些实用的功能，可以帮助开发者更方便地管理 Git 仓库。

以下是 Git 助手插件的详细使用指南。

## 插件加载与卸载

```bash
# 查看已加载插件
coding@auto-coder.chat:~$ /plugins
Loaded Plugins:

# 列出可用插件
coding@auto-coder.chat:~$ /plugins /list
Available Plugins:
- GitHelperPlugin (git_helper): Git helper plugin providing Git commands and status
...

# 加载Git助手插件
coding@auto-coder.chat:~$ /plugins /load git_helper
Plugin 'git_helper' (v0.1.0) loaded successfully

# 验证加载状态
coding@auto-coder.chat:~$ /plugins
Loaded Plugins:
- git_helper (v0.1.0): Git helper plugin providing Git commands and status

# 卸载插件，如需要卸载插件，请使用以下命令，卸载插件后，下次进入auto-autocoder-chat时插件将无法使用
coding@auto-coder.chat:~$ /plugins /unload git_helper
Plugin 'git_helper' unloaded successfully
```

## 核心命令列表

```bash
coding@auto-coder.chat:~$ /git/status       # 显示仓库状态
coding@auto-coder.chat:~$ /git/commit "fix login bug"  # 提交所有更改
coding@auto-coder.chat:~$ /git/branch       # 显示分支列表
coding@auto-coder.chat:~$ /git/checkout main  # 切换到main分支
coding@auto-coder.chat:~$ /git/diff         # 显示当前差异
coding@auto-coder.chat:~$ /git/log          # 显示精简提交历史（默认最近10条）
coding@auto-coder.chat:~$ /git/pull         # 拉取远程更新
coding@auto-coder.chat:~$ /git/push         # 推送本地提交
coding@auto-coder.chat:~$ /git/reset hard   # 硬重置到最新提交
```

## 智能补全演示

```bash
# 输入命令时按空格键触发补全
coding@auto-coder.chat:~$ /git/reset[空格]
hard    soft    mixed

coding@auto-coder.chat:~$ /git/checkout[空格]
main    dev     feature/login

```

## 使用示例

### 典型工作流程
```bash
coding@auto-coder.chat:~$ /git/status
On branch main
Changes not staged for commit:
  modified:   src/main.py

coding@auto-coder.chat:~$ /git/commit 优化用户认证逻辑
[main a1b2c3d] 优化用户认证逻辑
 1 file changed, 3 insertions(+)

coding@auto-coder.chat:~$ /git/push
Enumerating objects: 5, done.
Writing objects: 100% (3/3), 401 bytes | 401.00 KiB/s, done.
```

### 分支管理
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

## 高级用法

### 自定义日志格式
```bash
# 注意：复杂的格式化字符串可能需要调整引号处理，请根据实际情况调整或用终端命令行执行
coding@auto-coder.chat:~$ /git/log --graph --oneline
* a1b2c3d (HEAD -> main) 优化用户认证逻辑
* d4e5f6a (origin/dev) 修复页面布局问题

# 或使用简单的预设格式选项
coding@auto-coder.chat:~$ /git/log --pretty=oneline --abbrev-commit
a1b2c3d 优化用户认证逻辑
d4e5f6a 修复页面布局问题
```

### 差异对比
```bash
coding@auto-coder.chat:~$ /git/diff HEAD~1
diff --git a/src/main.py b/src/main.py
index 5d9e6b7..a1b2c3d 100644
--- a/src/main.py
+++ b/src/main.py
@@ -12,6 +12,7 @@ def authenticate(username, password):
     # 新增双因素认证
     if user:
         send_verification_code(user.phone)
+        log_auth_attempt(username)
     return user
```

## 注意事项

1. 自动执行 `git add .` 在提交前
2. 使用 `/git/reset` 前建议提交或暂存重要更改
3. 支持标准git参数，如 `/git/log -n 20 --graph`
4. 输入`/git/命令 --help` 可查看Git命令更为详尽的帮助信息


