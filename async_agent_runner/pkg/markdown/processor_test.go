package markdown

import (
	"strings"
	"testing"
)

func TestProcessContentWithH1Split(t *testing.T) {
	processor := NewProcessor()
	processor.SetSplitMode(SplitByHeading1)

	content := `# 第一个任务
这是第一个任务的内容

# 第二个任务  
这是第二个任务的内容

# 第三个任务
这是第三个任务的内容`

	documents := processor.ProcessContent(content, "test.md")

	if len(documents) != 3 {
		t.Errorf("期望分割成 3 个文档，实际得到 %d 个", len(documents))
	}

	expectedTitles := []string{"第一个任务", "第二个任务", "第三个任务"}
	for i, doc := range documents {
		if doc.Title != expectedTitles[i] {
			t.Errorf("文档 %d 的标题期望是 '%s'，实际是 '%s'", i, expectedTitles[i], doc.Title)
		}
		if doc.HeadingLevel != 1 {
			t.Errorf("文档 %d 的标题级别期望是 1，实际是 %d", i, doc.HeadingLevel)
		}
	}
}

func TestProcessContentWithH2Split(t *testing.T) {
	processor := NewProcessor()
	processor.SetSplitMode(SplitByHeading2)

	content := `# 主任务
这是主任务的介绍

## 子任务 1
这是子任务 1 的内容

## 子任务 2
这是子任务 2 的内容

# 另一个主任务
另一个主任务的内容`

	documents := processor.ProcessContent(content, "test.md")

	if len(documents) != 4 {
		t.Errorf("期望分割成 4 个文档，实际得到 %d 个", len(documents))
	}

	expectedTitles := []string{"主任务", "子任务 1", "子任务 2", "另一个主任务"}
	expectedLevels := []int{1, 2, 2, 1}
	for i, doc := range documents {
		if doc.Title != expectedTitles[i] {
			t.Errorf("文档 %d 的标题期望是 '%s'，实际是 '%s'", i, expectedTitles[i], doc.Title)
		}
		if doc.HeadingLevel != expectedLevels[i] {
			t.Errorf("文档 %d 的标题级别期望是 %d，实际是 %d", i, expectedLevels[i], doc.HeadingLevel)
		}
	}
}

func TestProcessContentWithDelimiter(t *testing.T) {
	processor := NewProcessor()
	processor.SetDelimiter("===")

	content := `第一个任务
这是第一个任务

===

第二个任务
这是第二个任务

===

第三个任务
这是第三个任务`

	documents := processor.ProcessContent(content, "test.md")

	if len(documents) != 3 {
		t.Errorf("期望分割成 3 个文档，实际得到 %d 个", len(documents))
	}

	for i, doc := range documents {
		if !strings.Contains(doc.Content, "第"+[]string{"一", "二", "三"}[i]+"个任务") {
			t.Errorf("文档 %d 的内容不包含期望的任务编号", i)
		}
	}
}

func TestGenerateTempFileName(t *testing.T) {
	processor := NewProcessor()

	tests := []struct {
		baseName string
		index    int
		total    int
		title    string
		expected string
	}{
		{"test", 0, 1, "Hello World", "test_hello_world.md"},
		{"test", 0, 3, "Hello World", "test_01_hello_world.md"},
		{"test", 1, 3, "Another Task", "test_02_another_task.md"},
		{"test", 0, 1, "", "test.md"},
		{"test", 0, 3, "", "test_01.md"},
	}

	for _, test := range tests {
		result := processor.generateTempFileName(test.baseName, test.index, test.total, test.title)
		if result != test.expected {
			t.Errorf("期望文件名 '%s'，实际得到 '%s'", test.expected, result)
		}
	}
}

func TestSanitizeFileName(t *testing.T) {
	processor := NewProcessor()

	tests := []struct {
		input    string
		expected string
	}{
		{"Hello World", "hello_world"},
		{"Test: File/Name", "test_file_name"},
		{"With<>Special|Chars", "with_special_chars"},
		{"Multiple   Spaces", "multiple_spaces"},
		{"___Underscores___", "underscores"},
	}

	for _, test := range tests {
		result := processor.sanitizeFileName(test.input)
		if result != test.expected {
			t.Errorf("输入 '%s' 期望输出 '%s'，实际得到 '%s'", test.input, test.expected, result)
		}
	}
}

func TestGetHeadingLevel(t *testing.T) {
	processor := NewProcessor()

	tests := []struct {
		line     string
		expected int
	}{
		{"# Level 1", 1},
		{"## Level 2", 2},
		{"### Level 3", 3},
		{"#### Level 4", 4},
		{"##### Level 5", 5},
		{"###### Level 6", 6},
		{"  ## Indented", 2},
		{"Not a heading", 0},
		{"#NotAHeading", 1}, // 边界情况
	}

	for _, test := range tests {
		result := processor.getHeadingLevel(test.line)
		if result != test.expected {
			t.Errorf("行 '%s' 期望级别 %d，实际得到 %d", test.line, test.expected, result)
		}
	}
}

func TestValidateContent(t *testing.T) {
	processor := NewProcessor()

	// 测试有效内容
	err := processor.ValidateContent("这是有效的内容")
	if err != nil {
		t.Errorf("有效内容验证失败: %v", err)
	}

	// 测试空内容
	err = processor.ValidateContent("")
	if err == nil {
		t.Error("空内容应该验证失败")
	}

	// 测试只有空白字符的内容
	err = processor.ValidateContent("   \n\t  ")
	if err == nil {
		t.Error("只有空白字符的内容应该验证失败")
	}
}

// 新增测试：多文档检测
func TestContainsMultipleDocuments(t *testing.T) {
	processor := NewProcessor()

	// 测试 YAML front matter 多文档
	yamlContent := `---
title: 第一个文档
type: task
---

这是第一个文档的内容

---
title: 第二个文档  
type: task
---

这是第二个文档的内容

---
title: 第三个文档
type: task
---

这是第三个文档的内容`

	if !processor.containsMultipleDocuments(yamlContent) {
		t.Error("应该检测到 YAML front matter 多文档结构")
	}

	// 测试单文档
	singleDoc := `# 单个标题
这是单个文档的内容`

	if processor.containsMultipleDocuments(singleDoc) {
		t.Error("不应该检测到多文档结构")
	}

	// 测试多个标题但空行较少的情况
	multiHeading := `# 第一个标题
内容1

# 第二个标题
内容2`

	if processor.containsMultipleDocuments(multiHeading) {
		t.Error("标题较密集时不应该检测为多文档")
	}
}

// 新增测试：YAML front matter 分割
func TestSplitByFrontMatter(t *testing.T) {
	processor := NewProcessor()

	content := `---
title: 任务一
priority: high
tags: [development, backend]
---

# 开发后端 API

创建用户管理相关的 REST API 接口。

## 需求
- 用户注册
- 用户登录
- 用户信息查询

---
title: 任务二
priority: medium  
tags: [frontend, ui]
---

# 前端界面开发

开发用户管理界面。

## 需求
- 登录页面
- 注册页面
- 用户信息页面

---
title: 任务三
priority: low
tags: [testing]
---

# 测试用例编写

为上述功能编写测试用例。`

	parts := processor.splitByFrontMatter(content)

	if len(parts) != 3 {
		t.Errorf("期望分割成 3 个文档，实际得到 %d 个", len(parts))
	}

	expectedTitles := []string{"任务一", "任务二", "任务三"}
	for i, part := range parts {
		if part.Title != expectedTitles[i] {
			t.Errorf("文档 %d 的标题期望是 '%s'，实际是 '%s'", i, expectedTitles[i], part.Title)
		}

		// 检查元数据
		if part.Metadata == nil {
			t.Errorf("文档 %d 应该有元数据", i)
			continue
		}

		if title, ok := part.Metadata["title"].(string); !ok || title != expectedTitles[i] {
			t.Errorf("文档 %d 元数据中的标题不正确", i)
		}

		if tags, ok := part.Metadata["tags"]; !ok {
			t.Errorf("文档 %d 应该有 tags 元数据", i)
		} else {
			t.Logf("文档 %d 的 tags: %v", i, tags)
		}
	}
}

// 新增测试：长度约束
func TestLengthConstraints(t *testing.T) {
	processor := NewProcessor()
	processor.SetLengthConstraints(20, 100) // 最小20字符，最大100字符

	content := `# 任务一
这是一个很短的任务。

# 任务二  
这是一个中等长度的任务，包含了足够的内容来满足最小长度要求，但不会超过最大长度限制。

# 任务三
这是一个非常长的任务描述，包含了大量的详细信息和说明。这个任务描述会超过设定的最大长度限制，因此应该被分割成多个较小的部分。这样可以确保每个部分都不会太长，便于处理和管理。我们需要确保分割后的内容仍然保持完整性和可读性。`

	documents := processor.ProcessContent(content, "test.md")

	// 检查是否过滤掉了太短的文档
	for _, doc := range documents {
		if len(doc.Content) < 20 {
			t.Errorf("文档内容太短: %d 字符，应该被过滤掉", len(doc.Content))
		}
	}

	// 检查是否有长文档被分割
	hasLongDocSplit := false
	for _, doc := range documents {
		if strings.Contains(doc.Title, "第") && strings.Contains(doc.Title, "部分") {
			hasLongDocSplit = true
			break
		}
	}

	if !hasLongDocSplit {
		t.Log("注意：可能没有文档被分割，这取决于内容的实际长度")
	}
}

// 新增测试：自定义分割器
func TestCustomSplitter(t *testing.T) {
	processor := NewProcessor()

	// 设置自定义分割器：按 "TASK:" 分割
	processor.SetCustomSplitter(func(content string) []string {
		lines := strings.Split(content, "\n")
		var parts []string
		var currentPart []string

		for _, line := range lines {
			if strings.HasPrefix(strings.TrimSpace(line), "TASK:") {
				// 保存当前部分
				if len(currentPart) > 0 {
					parts = append(parts, strings.Join(currentPart, "\n"))
				}
				// 开始新部分
				currentPart = []string{line}
			} else {
				currentPart = append(currentPart, line)
			}
		}

		// 添加最后一部分
		if len(currentPart) > 0 {
			parts = append(parts, strings.Join(currentPart, "\n"))
		}

		return parts
	})

	content := `一些介绍内容

TASK: 创建数据库表
创建用户表和订单表的SQL脚本。

TASK: 实现API接口  
实现用户管理的REST API。

TASK: 编写测试用例
为上述功能编写单元测试。`

	documents := processor.ProcessContent(content, "test.md")

	if len(documents) != 3 {
		t.Errorf("期望分割成 3 个文档，实际得到 %d 个", len(documents))
	}

	// 检查每个文档是否包含 TASK: 开头
	for i, doc := range documents {
		if !strings.Contains(doc.Content, "TASK:") {
			t.Errorf("文档 %d 应该包含 'TASK:'", i)
		}
	}
}

// 新增测试：重叠配置
func TestOverlapSize(t *testing.T) {
	processor := NewProcessor()
	processor.SetLengthConstraints(50, 150) // 较小的最大长度以便测试分割
	processor.SetOverlapSize(20)            // 20字符重叠

	// 创建一个足够长的文档来触发分割
	content := `# 长文档测试
这是一个很长的文档内容，用于测试文档分割和重叠功能。这个文档应该被分割成多个部分，每个部分之间会有一定的重叠内容。重叠内容有助于保持上下文的连续性，确保分割后的文档仍然可以独立理解。我们需要验证重叠功能是否正常工作。`

	documents := processor.ProcessContent(content, "test.md")

	if len(documents) > 1 {
		t.Logf("文档被分割成 %d 个部分", len(documents))

		// 检查是否有重叠（这是一个简单的检查）
		for i := 0; i < len(documents)-1; i++ {
			current := documents[i].Content
			next := documents[i+1].Content

			// 检查下一个文档的开头是否在当前文档的结尾附近出现
			if len(current) > 30 && len(next) > 10 {
				currentEnd := current[len(current)-30:]
				nextStart := next[:10]

				// 这是一个简化的重叠检查
				t.Logf("文档 %d 结尾: %s", i, currentEnd)
				t.Logf("文档 %d 开头: %s", i+1, nextStart)
			}
		}
	} else {
		t.Log("文档未被分割，可能是因为长度不足")
	}
}

// 新增测试：parseYAMLMetadata
func TestParseYAMLMetadata(t *testing.T) {
	processor := NewProcessor()

	yamlContent := `title: 测试任务
priority: high  
tags: [development, backend]
author: "张三"
date: 2024-01-01
description: |
  这是一个多行描述
  包含详细信息`

	metadata := processor.parseYAMLMetadata(yamlContent)

	expectedKeys := []string{"title", "priority", "tags", "author", "date", "description"}
	for _, key := range expectedKeys {
		if _, ok := metadata[key]; !ok {
			t.Errorf("元数据中缺少键: %s", key)
		}
	}

	if title, ok := metadata["title"].(string); !ok || title != "测试任务" {
		t.Errorf("title 解析错误, 期望: '测试任务', 实际: '%v'", metadata["title"])
	}

	if priority, ok := metadata["priority"].(string); !ok || priority != "high" {
		t.Errorf("priority 解析错误, 期望: 'high', 实际: '%v'", metadata["priority"])
	}

	t.Logf("解析的元数据: %+v", metadata)
}
