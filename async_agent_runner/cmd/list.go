package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/williamzhu/auto-coder/async_agent_runner/pkg/worktree"
)

// listCmd represents the list command
var listCmd = &cobra.Command{
	Use:   "list",
	Short: "列出所有 worktree",
	Long: `显示所有 git worktree 的状态和信息。

示例:
  ac list                  # 列出所有 worktree
  ac list --only-managed   # 只显示在工作目录中的 worktree`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runList()
	},
}

var onlyManaged bool

func init() {
	rootCmd.AddCommand(listCmd)
	listCmd.Flags().BoolVar(&onlyManaged, "only-managed", false, "只显示在工作目录中的 worktree")
}

func runList() error {
	wtManager := worktree.NewManager(workdir, fromBranch)
	
	worktrees, err := wtManager.ListWorktrees()
	if err != nil {
		return fmt.Errorf("获取 worktree 列表失败: %v", err)
	}

	if len(worktrees) == 0 {
		fmt.Println("没有找到 worktree")
		return nil
	}

	fmt.Printf("找到 %d 个 worktree:\n\n", len(worktrees))
	
	for i, wt := range worktrees {
		// 如果只显示管理的 worktree，过滤掉其他的
		if onlyManaged && !strings.HasPrefix(wt.Path, workdir) {
			continue
		}

		fmt.Printf("%d. 名称: %s\n", i+1, wt.Name)
		fmt.Printf("   路径: %s\n", wt.Path)
		fmt.Printf("   分支: %s\n", wt.Branch)
		
		// 标记是否是我们管理的
		if strings.HasPrefix(wt.Path, workdir) {
			fmt.Printf("   状态: 由 ac 管理\n")
		} else {
			fmt.Printf("   状态: 外部 worktree\n")
		}
		fmt.Println()
	}

	return nil
}