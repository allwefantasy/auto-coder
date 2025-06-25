package worktree

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Manager 管理 git worktree 操作
type Manager struct {
	BaseDir    string
	WorkDir    string
	FromBranch string
}

// NewManager 创建新的 worktree 管理器
func NewManager(workDir, fromBranch string) *Manager {
	return &Manager{
		WorkDir:    workDir,
		FromBranch: fromBranch,
	}
}

// WorktreeInfo 包含 worktree 信息
type WorktreeInfo struct {
	Name     string
	Path     string
	Branch   string
	TempFile string
}

// CreateWorktree 创建新的 git worktree
func (m *Manager) CreateWorktree(name string) (*WorktreeInfo, error) {
	// 确保工作目录存在
	if err := os.MkdirAll(m.WorkDir, 0755); err != nil {
		return nil, fmt.Errorf("创建工作目录失败: %v", err)
	}

	fullPath := filepath.Join(m.WorkDir, name)
	
	// 检查目录是否已存在
	if _, err := os.Stat(fullPath); err == nil {
		return nil, fmt.Errorf("工作目录已存在: %s", fullPath)
	}

	// 创建 git worktree
	cmd := exec.Command("git", "worktree", "add", fullPath, "-b", name, m.FromBranch)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("创建 git worktree 失败: %v", err)
	}

	return &WorktreeInfo{
		Name:   name,
		Path:   fullPath,
		Branch: name,
	}, nil
}

// CleanupWorktree 清理指定的 worktree
func (m *Manager) CleanupWorktree(info *WorktreeInfo) error {
	// 删除 worktree
	cmd := exec.Command("git", "worktree", "remove", info.Path, "--force")
	if err := cmd.Run(); err != nil {
		// 如果命令失败，尝试手动删除目录
		if err := os.RemoveAll(info.Path); err != nil {
			return fmt.Errorf("清理 worktree 失败: %v", err)
		}
	}

	// 删除分支（如果存在）
	cmd = exec.Command("git", "branch", "-D", info.Branch)
	cmd.Run() // 忽略错误，因为分支可能不存在

	return nil
}

// ListWorktrees 列出所有 worktree
func (m *Manager) ListWorktrees() ([]WorktreeInfo, error) {
	cmd := exec.Command("git", "worktree", "list", "--porcelain")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("获取 worktree 列表失败: %v", err)
	}

	var worktrees []WorktreeInfo
	lines := strings.Split(string(output), "\n")
	
	var current WorktreeInfo
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			if current.Path != "" {
				worktrees = append(worktrees, current)
				current = WorktreeInfo{}
			}
			continue
		}

		if strings.HasPrefix(line, "worktree ") {
			current.Path = strings.TrimPrefix(line, "worktree ")
			current.Name = filepath.Base(current.Path)
		} else if strings.HasPrefix(line, "branch ") {
			current.Branch = strings.TrimPrefix(line, "branch ")
		}
	}

	// 添加最后一个 worktree（如果有）
	if current.Path != "" {
		worktrees = append(worktrees, current)
	}

	return worktrees, nil
}

// CleanupAllWorktrees 清理所有匹配模式的 worktree
func (m *Manager) CleanupAllWorktrees(pattern string) error {
	worktrees, err := m.ListWorktrees()
	if err != nil {
		return err
	}

	for _, wt := range worktrees {
		// 只清理在我们工作目录中的 worktree
		if strings.HasPrefix(wt.Path, m.WorkDir) {
			if pattern == "" || strings.Contains(wt.Name, pattern) {
				fmt.Printf("清理 worktree: %s\n", wt.Name)
				if err := m.CleanupWorktree(&wt); err != nil {
					fmt.Printf("警告: 清理 worktree %s 失败: %v\n", wt.Name, err)
				}
			}
		}
	}

	return nil
}

// WriteContentToWorktree 在 worktree 中写入内容到文件
func (m *Manager) WriteContentToWorktree(info *WorktreeInfo, filename, content string) error {
	filePath := filepath.Join(info.Path, filename)
	
	if err := os.WriteFile(filePath, []byte(content), 0644); err != nil {
		return fmt.Errorf("写入文件失败: %v", err)
	}

	info.TempFile = filename
	return nil
}