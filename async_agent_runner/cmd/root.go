package cmd

import (
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/williamzhu/auto-coder/async_agent_runner/pkg/executor"
	"github.com/williamzhu/auto-coder/async_agent_runner/pkg/markdown"
	"github.com/williamzhu/auto-coder/async_agent_runner/pkg/worktree"
)

var (
	model       string
	fromBranch  string
	pullRequest bool
	workdir     string
	cleanup     bool
	splitMode   string
	delimiter   string
	minLevel    int
	maxLevel    int
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "ac",
	Short: "Auto-coder 异步代理运行器",
	Long: `简化 git worktree 和 auto-coder 操作的启动器。

支持从标准输入读取 markdown 文件，使用智能的 markdown 解析器按标题结构自动分割任务，
为每个任务创建独立的 worktree，并执行 auto-coder.run。

分割模式:
  h1        - 按一级标题 (# 标题) 分割 [默认]
  h2        - 按一、二级标题 (# ## 标题) 分割
  h3        - 按一、二、三级标题 (# ## ### 标题) 分割
  any       - 按指定级别范围的标题分割
  delimiter - 按自定义分隔符分割 (兼容模式)

示例:
  # 按 H1 标题分割
  cat abc.md | ac --model cus/anthropic/claude-sonnet-4 --pr
  
  # 按 H2 标题分割  
  cat abc.md | ac --model xxxx --split h2 --pr
  
  # 使用自定义分隔符 (兼容原有方式)
  cat abc.md | ac --model xxxx --split delimiter --delimiter "===" --pr
  
  # 按指定级别范围分割
  cat abc.md | ac --model xxxx --split any --min-level 2 --max-level 3 --pr`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runAutoCoderAsync()
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute() error {
	return rootCmd.Execute()
}

func init() {
	rootCmd.Flags().StringVar(&model, "model", "", "指定要使用的模型 (必需)")
	rootCmd.Flags().StringVar(&fromBranch, "from", "master", "指定基础分支")
	rootCmd.Flags().BoolVar(&pullRequest, "pr", false, "是否创建 pull request")
	rootCmd.Flags().StringVar(&workdir, "workdir", "../ac_async_agent_workdir", "工作目录")
	rootCmd.Flags().BoolVar(&cleanup, "cleanup", false, "清理所有 worktree 后退出")
	rootCmd.Flags().StringVar(&splitMode, "split", "h1", "分割模式: h1, h2, h3, any, delimiter")
	rootCmd.Flags().StringVar(&delimiter, "delimiter", "===", "自定义分隔符 (当 split=delimiter 时使用)")
	rootCmd.Flags().IntVar(&minLevel, "min-level", 1, "最小标题级别 (当 split=any 时使用)")
	rootCmd.Flags().IntVar(&maxLevel, "max-level", 6, "最大标题级别 (当 split=any 时使用)")
	
	rootCmd.MarkFlagRequired("model")
}

func runAutoCoderAsync() error {
	// 初始化组件
	wtManager := worktree.NewManager(workdir, fromBranch)
	mdProcessor := markdown.NewProcessor()
	
	// 配置 markdown 处理器
	switch splitMode {
	case "h1":
		mdProcessor.SetSplitMode(markdown.SplitByHeading1)
	case "h2":
		mdProcessor.SetSplitMode(markdown.SplitByHeading2)
	case "h3":
		mdProcessor.SetSplitMode(markdown.SplitByHeading3)
	case "any":
		mdProcessor.SetSplitMode(markdown.SplitByAnyHeading)
		mdProcessor.SetHeadingLevelRange(minLevel, maxLevel)
	case "delimiter":
		mdProcessor.SetDelimiter(delimiter)
	default:
		fmt.Printf("警告: 未知的分割模式 '%s'，使用默认的 H1 分割\n", splitMode)
		mdProcessor.SetSplitMode(markdown.SplitByHeading1)
	}
	
	autoCoderExec := executor.NewAutoCoderExecutor(model, pullRequest)

	// 如果只是清理，执行清理后退出
	if cleanup {
		fmt.Println("清理所有 worktree...")
		return wtManager.CleanupAllWorktrees("")
	}

	// 检查 auto-coder.run 是否可用
	if err := autoCoderExec.CheckAutoCoderAvailable(); err != nil {
		return err
	}

	// 验证模型参数
	if err := autoCoderExec.ValidateModel(); err != nil {
		return err
	}

	// 检查是否有标准输入
	stat, err := os.Stdin.Stat()
	if err != nil {
		return fmt.Errorf("检查标准输入失败: %v", err)
	}

	if (stat.Mode() & os.ModeCharDevice) != 0 {
		return fmt.Errorf("没有从标准输入读取到数据，请使用管道输入 markdown 文件")
	}

	// 读取标准输入
	input, err := io.ReadAll(os.Stdin)
	if err != nil {
		return fmt.Errorf("读取标准输入失败: %v", err)
	}

	inputStr := string(input)
	if err := mdProcessor.ValidateContent(inputStr); err != nil {
		return err
	}

	// 处理 markdown 内容
	documents := mdProcessor.ProcessContent(inputStr, "stdin")
	
	// 生成时间戳
	timestamp := time.Now().Format("20060102150405")

	// 处理每个文档
	for _, doc := range documents {
		err := processDocument(doc, timestamp, wtManager, autoCoderExec)
		if err != nil {
			fmt.Printf("处理文档失败: %v\n", err)
			continue
		}
	}

	return nil
}

func processDocument(doc markdown.Document, timestamp string, wtManager *worktree.Manager, autoCoderExec *executor.AutoCoderExecutor) error {
	// 生成工作目录名
	workdirName := generateWorktreeName(doc, timestamp)
	
	fmt.Printf("处理文档: %s\n", getDocumentInfo(doc))
	fmt.Printf("创建 git worktree: %s\n", workdirName)

	// 创建 worktree
	wtInfo, err := wtManager.CreateWorktree(workdirName)
	if err != nil {
		return fmt.Errorf("创建 worktree 失败: %v", err)
	}

	// 写入内容到临时文件
	if err := wtManager.WriteContentToWorktree(wtInfo, doc.TempFileName, doc.Content); err != nil {
		// 清理失败的 worktree
		wtManager.CleanupWorktree(wtInfo)
		return fmt.Errorf("写入内容失败: %v", err)
	}

	// 记录执行信息
	autoCoderExec.LogExecution(wtInfo.Path, doc.TempFileName)
	
	// 执行 auto-coder.run
	fmt.Printf("运行 auto-coder.run...\n")
	if err := autoCoderExec.Execute(wtInfo.Path, doc.TempFileName); err != nil {
		fmt.Printf("警告: auto-coder.run 执行失败: %v\n", err)
		// 不清理 worktree，让用户可以手动检查
		return err
	}

	fmt.Printf("完成处理: %s\n", workdirName)
	return nil
}

func generateWorktreeName(doc markdown.Document, timestamp string) string {
	baseName := "stdin"
	if doc.OriginalFile != "" && doc.OriginalFile != "stdin" {
		baseName = strings.TrimSuffix(doc.OriginalFile, ".md")
	}

	if doc.Index == 0 {
		return fmt.Sprintf("%s_%s", baseName, timestamp)
	}
	
	return fmt.Sprintf("%s_%02d_%s", baseName, doc.Index+1, timestamp)
}

func getDocumentInfo(doc markdown.Document) string {
	contentPreview := doc.Content
	if len(contentPreview) > 100 {
		contentPreview = contentPreview[:100] + "..."
	}
	
	return fmt.Sprintf("文件: %s, 部分: %d, 临时文件: %s, 内容预览: %s", 
		doc.OriginalFile, doc.Index+1, doc.TempFileName, contentPreview)
}