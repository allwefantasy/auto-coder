package markdown

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
)

// Document 表示一个 markdown 文档
type Document struct {
	OriginalFile string
	Index        int
	Content      string
	TempFileName string
	Title        string
	HeadingLevel int
}

// SplitMode 分割模式
type SplitMode int

const (
	SplitByDelimiter SplitMode = iota // 按分隔符分割（兼容模式）
	SplitByHeading1                   // 按 H1 标题分割
	SplitByHeading2                   // 按 H2 标题分割
	SplitByHeading3                   // 按 H3 标题分割
	SplitByAnyHeading                 // 按任何标题分割
)

// Processor 处理 markdown 文件
type Processor struct {
	SplitMode     SplitMode
	Delimiter     string
	MinHeadingLevel int // 最小标题级别
	MaxHeadingLevel int // 最大标题级别
}

// NewProcessor 创建新的 markdown 处理器
func NewProcessor() *Processor {
	return &Processor{
		SplitMode:       SplitByHeading1, // 默认按 H1 分割
		Delimiter:       "===",
		MinHeadingLevel: 1,
		MaxHeadingLevel: 6,
	}
}

// ProcessContent 处理 markdown 内容，返回分割后的文档列表
func (p *Processor) ProcessContent(content, fileName string) []Document {
	var parts []DocumentPart
	var err error

	// 首先尝试按 markdown 结构分割
	if p.SplitMode != SplitByDelimiter {
		parts, err = p.splitByHeadings(content)
		if err != nil || len(parts) <= 1 {
			// 如果解析失败或没有找到标题，回退到分隔符模式
			parts = p.splitByDelimiter(content)
		}
	} else {
		// 使用分隔符模式
		parts = p.splitByDelimiter(content)
	}

	// 如果没有找到任何分割，将整个内容作为一个文档
	if len(parts) == 0 {
		parts = append(parts, DocumentPart{
			Content: strings.TrimSpace(content),
			Title:   p.extractTitle(content),
			Level:   1,
		})
	}

	var documents []Document
	baseName := p.getBaseName(fileName)

	for i, part := range parts {
		doc := Document{
			OriginalFile: fileName,
			Index:        i,
			Content:      part.Content,
			Title:        part.Title,
			HeadingLevel: part.Level,
			TempFileName: p.generateTempFileName(baseName, i, len(parts), part.Title),
		}
		documents = append(documents, doc)
	}

	return documents
}

// DocumentPart 表示文档的一个部分
type DocumentPart struct {
	Content string
	Title   string
	Level   int
}

// splitByHeadings 按标题分割 markdown 内容
func (p *Processor) splitByHeadings(content string) ([]DocumentPart, error) {
	lines := strings.Split(content, "\n")
	var parts []DocumentPart
	var currentPart DocumentPart
	var currentLines []string

	for _, line := range lines {
		// 检查是否是标题行
		if strings.HasPrefix(strings.TrimSpace(line), "#") {
			level := p.getHeadingLevel(line)
			title := p.extractTitleFromLine(line)
			
			// 如果这是我们要分割的标题级别
			if p.shouldSplitAtLevel(level) {
				// 保存之前的部分
				if len(currentLines) > 0 {
					currentPart.Content = strings.Join(currentLines, "\n")
					if currentPart.Title == "" {
						currentPart.Title = p.extractTitle(currentPart.Content)
						currentPart.Level = 1
					}
					parts = append(parts, currentPart)
				}

				// 开始新的部分
				currentPart = DocumentPart{
					Title: title,
					Level: level,
				}
				currentLines = []string{line}
			} else {
				// 不是分割级别的标题，添加到当前部分
				currentLines = append(currentLines, line)
			}
		} else {
			// 普通行，添加到当前部分
			currentLines = append(currentLines, line)
		}
	}

	// 添加最后一个部分
	if len(currentLines) > 0 {
		currentPart.Content = strings.Join(currentLines, "\n")
		if currentPart.Title == "" {
			currentPart.Title = p.extractTitle(currentPart.Content)
			currentPart.Level = 1
		}
		parts = append(parts, currentPart)
	}

	// 如果没有找到任何部分，使用整个内容
	if len(parts) == 0 {
		parts = append(parts, DocumentPart{
			Content: content,
			Title:   p.extractTitle(content),
			Level:   1,
		})
	}

	return parts, nil
}

// getHeadingLevel 获取标题级别
func (p *Processor) getHeadingLevel(line string) int {
	trimmed := strings.TrimSpace(line)
	level := 0
	for _, char := range trimmed {
		if char == '#' {
			level++
		} else {
			break
		}
	}
	return level
}

// extractTitleFromLine 从标题行提取标题文本
func (p *Processor) extractTitleFromLine(line string) string {
	re := regexp.MustCompile(`^#+\s*`)
	title := re.ReplaceAllString(strings.TrimSpace(line), "")
	title = strings.TrimSpace(title)
	if title == "" {
		return "Untitled"
	}
	return title
}

// shouldSplitAtLevel 判断是否应该在指定级别分割
func (p *Processor) shouldSplitAtLevel(level int) bool {
	switch p.SplitMode {
	case SplitByHeading1:
		return level == 1
	case SplitByHeading2:
		return level <= 2
	case SplitByHeading3:
		return level <= 3
	case SplitByAnyHeading:
		return level >= p.MinHeadingLevel && level <= p.MaxHeadingLevel
	default:
		return false
	}
}



// splitByDelimiter 按分隔符分割内容（向后兼容）
func (p *Processor) splitByDelimiter(content string) []DocumentPart {
	parts := strings.Split(content, p.Delimiter)
	var result []DocumentPart

	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			result = append(result, DocumentPart{
				Content: trimmed,
				Title:   p.extractTitle(trimmed),
				Level:   1,
			})
		}
	}

	return result
}

// extractTitle 从内容中提取标题
func (p *Processor) extractTitle(content string) string {
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") {
			// 移除 # 符号和前后空格
			re := regexp.MustCompile(`^#+\s*`)
			title := re.ReplaceAllString(line, "")
			title = strings.TrimSpace(title)
			if title != "" {
				return title
			}
		}
	}
	
	// 如果没有找到标题，使用前50个字符
	if len(content) > 50 {
		return content[:50] + "..."
	}
	return content
}

// getBaseName 获取文件的基本名称（不包含扩展名）
func (p *Processor) getBaseName(fileName string) string {
	if fileName == "" || fileName == "stdin" {
		return "stdin"
	}

	base := filepath.Base(fileName)
	return strings.TrimSuffix(base, filepath.Ext(base))
}

// generateTempFileName 生成临时文件名
func (p *Processor) generateTempFileName(baseName string, index, total int, title string) string {
	// 清理标题以用作文件名
	safeTitle := p.sanitizeFileName(title)
	
	if total == 1 {
		if safeTitle != "" && safeTitle != "Untitled" {
			return fmt.Sprintf("%s_%s.md", baseName, safeTitle)
		}
		return fmt.Sprintf("%s.md", baseName)
	}

	if safeTitle != "" && safeTitle != "Untitled" {
		return fmt.Sprintf("%s_%02d_%s.md", baseName, index+1, safeTitle)
	}
	
	return fmt.Sprintf("%s_%02d.md", baseName, index+1)
}

// sanitizeFileName 清理文件名，移除不安全字符
func (p *Processor) sanitizeFileName(title string) string {
	// 移除或替换不安全的文件名字符
	re := regexp.MustCompile(`[<>:"/\\|?*\s]+`)
	safe := re.ReplaceAllString(title, "_")
	
	// 移除多余的下划线
	re = regexp.MustCompile(`_+`)
	safe = re.ReplaceAllString(safe, "_")
	
	// 移除开头和结尾的下划线
	safe = strings.Trim(safe, "_")
	
	// 限制长度
	if len(safe) > 50 {
		safe = safe[:50]
	}
	
	return strings.ToLower(safe)
}

// ValidateContent 验证 markdown 内容
func (p *Processor) ValidateContent(content string) error {
	if strings.TrimSpace(content) == "" {
		return fmt.Errorf("内容为空")
	}
	return nil
}

// GetDocumentInfo 获取文档信息摘要
func (p *Processor) GetDocumentInfo(doc Document) string {
	contentPreview := doc.Content
	if len(contentPreview) > 100 {
		contentPreview = contentPreview[:100] + "..."
	}

	title := doc.Title
	if title == "" {
		title = "无标题"
	}

	return fmt.Sprintf("标题: %s (H%d), 文件: %s, 部分: %d, 临时文件: %s, 内容预览: %s",
		title, doc.HeadingLevel, doc.OriginalFile, doc.Index+1, doc.TempFileName, contentPreview)
}

// SetSplitMode 设置分割模式
func (p *Processor) SetSplitMode(mode SplitMode) {
	p.SplitMode = mode
}

// SetDelimiter 设置自定义分隔符（用于兼容模式）
func (p *Processor) SetDelimiter(delimiter string) {
	if delimiter != "" {
		p.Delimiter = delimiter
	}
	p.SplitMode = SplitByDelimiter
}

// SetHeadingLevelRange 设置标题级别范围
func (p *Processor) SetHeadingLevelRange(min, max int) {
	if min >= 1 && min <= 6 && max >= min && max <= 6 {
		p.MinHeadingLevel = min
		p.MaxHeadingLevel = max
	}
}