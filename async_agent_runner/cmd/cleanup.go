package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/williamzhu/auto-coder/async_agent_runner/pkg/worktree"
)

// cleanupCmd represents the cleanup command
var cleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "清理 worktree 目录",
	Long: `清理所有在工作目录中的 git worktree。

示例:
  ac cleanup               # 清理所有 worktree
  ac cleanup --pattern abc # 只清理包含 'abc' 的 worktree`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runCleanup()
	},
}

var cleanupPattern string

func init() {
	rootCmd.AddCommand(cleanupCmd)
	cleanupCmd.Flags().StringVar(&cleanupPattern, "pattern", "", "清理匹配模式的 worktree")
}

func runCleanup() error {
	wtManager := worktree.NewManager(workdir, fromBranch)
	
	fmt.Printf("开始清理工作目录: %s\n", workdir)
	if cleanupPattern != "" {
		fmt.Printf("匹配模式: %s\n", cleanupPattern)
	}
	
	err := wtManager.CleanupAllWorktrees(cleanupPattern)
	if err != nil {
		return fmt.Errorf("清理失败: %v", err)
	}
	
	fmt.Println("清理完成")
	return nil
}