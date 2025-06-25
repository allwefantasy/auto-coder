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