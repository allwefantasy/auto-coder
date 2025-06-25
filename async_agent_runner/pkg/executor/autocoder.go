package executor

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// AutoCoderExecutor 执行 auto-coder.run 命令
type AutoCoderExecutor struct {
	Model       string
	PullRequest bool
	WorkDir     string
}

// NewAutoCoderExecutor 创建新的 auto-coder 执行器
func NewAutoCoderExecutor(model string, pullRequest bool) *AutoCoderExecutor {
	return &AutoCoderExecutor{
		Model:       model,
		PullRequest: pullRequest,
	}
}

// Execute 执行 auto-coder.run 命令
func (e *AutoCoderExecutor) Execute(workDir, tempFileName string) error {
	// 构建 auto-coder.run 命令参数
	var args []string
	args = append(args, "--model", e.Model)
	
	if e.PullRequest {
		args = append(args, "--pr")
	}

	// 创建 cat 命令来读取临时文件
	catCmd := exec.Command("cat", tempFileName)
	catCmd.Dir = workDir

	// 创建 auto-coder.run 命令
	autoCoderCmd := exec.Command("auto-coder.run", args...)
	autoCoderCmd.Dir = workDir
	autoCoderCmd.Stdout = os.Stdout
	autoCoderCmd.Stderr = os.Stderr

	// 连接管道
	pipe, err := catCmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("创建管道失败: %v", err)
	}

	autoCoderCmd.Stdin = pipe

	// 启动 auto-coder.run 命令
	if err := autoCoderCmd.Start(); err != nil {
		return fmt.Errorf("启动 auto-coder.run 失败: %v", err)
	}

	// 运行 cat 命令
	if err := catCmd.Run(); err != nil {
		return fmt.Errorf("执行 cat 命令失败: %v", err)
	}

	// 等待 auto-coder.run 完成
	if err := autoCoderCmd.Wait(); err != nil {
		return fmt.Errorf("auto-coder.run 执行失败: %v", err)
	}

	return nil
}

// CheckAutoCoderAvailable 检查 auto-coder.run 是否可用
func (e *AutoCoderExecutor) CheckAutoCoderAvailable() error {
	_, err := exec.LookPath("auto-coder.run")
	if err != nil {
		return fmt.Errorf("auto-coder.run 未找到，请确保已正确安装")
	}
	return nil
}

// ValidateModel 验证模型参数
func (e *AutoCoderExecutor) ValidateModel() error {
	if e.Model == "" {
		return fmt.Errorf("模型参数不能为空")
	}
	return nil
}

// LogExecution 记录执行信息
func (e *AutoCoderExecutor) LogExecution(workDir, tempFileName string) {
	fmt.Printf("执行目录: %s\n", workDir)
	fmt.Printf("临时文件: %s\n", tempFileName)
	fmt.Printf("使用模型: %s\n", e.Model)
	fmt.Printf("创建 PR: %v\n", e.PullRequest)
	fmt.Printf("完整路径: %s\n", filepath.Join(workDir, tempFileName))
}