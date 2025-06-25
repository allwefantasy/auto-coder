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
	Metadata     map[string]interface{} // 新增：文档元数据
}

// SplitMode 分割模式
type SplitMode int

const (
	SplitByDelimiter     SplitMode = iota // 按分隔符分割（兼容模式）
	SplitByHeading1                       // 按 H1 标题分割
	SplitByHeading2                       // 按 H2 标题分割
	SplitByHeading3                       // 按 H3 标题分割
	SplitByAnyHeading                     // 按任何标题分割
	SplitByFrontMatter                    // 按 YAML front matter 分割
	SplitByCustomPattern                  // 按自定义正则模式分割
)

// SplitterConfig 分割器配置
type SplitterConfig struct {
	Pattern         string                // 自定义正则模式
	MinLength       int                   // 最小文档长度
	MaxLength       int                   // 最大文档长度
	OverlapSize     int                   // 重叠大小（用于长文档分割）
	PreserveContext bool                  // 是否保留上下文
	CustomSplitter  func(string) []string // 自定义分割函数
}

// Processor 处理 markdown 文件
type Processor struct {
	SplitMode       SplitMode
	Delimiter       string
	MinHeadingLevel int             // 最小标题级别
	MaxHeadingLevel int             // 最大标题级别
	Config          *SplitterConfig // 新增：分割器配置
}

// NewProcessor 创建新的 markdown 处理器
func NewProcessor() *Processor {
	return &Processor{
		SplitMode:       SplitByHeading1, // 默认按 H1 分割
		Delimiter:       "===",
		MinHeadingLevel: 1,
		MaxHeadingLevel: 6,
		Config: &SplitterConfig{
			MinLength:       50,    // 最小文档长度 50 字符
			MaxLength:       10000, // 最大文档长度 10k 字符
			OverlapSize:     100,   // 重叠 100 字符
			PreserveContext: true,
		},
	}
}

// ProcessContent 处理 markdown 内容，返回分割后的文档列表
func (p *Processor) ProcessContent(content, fileName string) []Document {
	var parts []DocumentPart
	var err error

	// 首先检测文档是否包含多个独立文档
	if p.containsMultipleDocuments(content) {
		fmt.Printf("检测到多文档结构，使用多文档解析模式\n")
		parts, err = p.parseMultipleDocuments(content)
		if err != nil {
			fmt.Printf("多文档解析失败: %v，回退到标准分割\n", err)
		}
	}

	// 如果没有检测到多文档或解析失败，使用原有分割逻辑
	if len(parts) == 0 {
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
	}

	// 使用自定义分割器（如果配置了）
	if p.Config != nil && p.Config.CustomSplitter != nil {
		fmt.Printf("使用自定义分割器\n")
		customParts := p.Config.CustomSplitter(content)
		parts = p.convertToDocumentParts(customParts)
	}

	// 如果没有找到任何分割，将整个内容作为一个文档
	if len(parts) == 0 {
		parts = append(parts, DocumentPart{
			Content: strings.TrimSpace(content),
			Title:   p.extractTitle(content),
			Level:   1,
		})
	}

	// 应用长度和重叠配置
	parts = p.applyLengthConstraints(parts)

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
			Metadata:     part.Metadata, // 新增：设置元数据
		}
		documents = append(documents, doc)
	}

	return documents
}

// containsMultipleDocuments 检测内容是否包含多个独立文档
func (p *Processor) containsMultipleDocuments(content string) bool {
	// 检测 YAML front matter 分隔符
	frontMatterPattern := regexp.MustCompile(`(?m)^---\s*$`)
	matches := frontMatterPattern.FindAllString(content, -1)
	if len(matches) >= 3 { // 至少有3个分隔符才认为是多文档
		return true
	}

	// 检测连续的空行分隔（可能是多文档）
	emptyLinePattern := regexp.MustCompile(`\n\s*\n\s*\n`)
	if len(emptyLinePattern.FindAllString(content, -1)) >= 2 {
		// 进一步检查是否有标题结构
		headingPattern := regexp.MustCompile(`(?m)^#{1,6}\s+.+$`)
		headings := headingPattern.FindAllString(content, -1)
		return len(headings) >= 2
	}

	return false
}

// parseMultipleDocuments 解析多文档结构
func (p *Processor) parseMultipleDocuments(content string) ([]DocumentPart, error) {
	var parts []DocumentPart

	// 尝试按 YAML front matter 分割
	if strings.Contains(content, "---") {
		yamlParts := p.splitByFrontMatter(content)
		if len(yamlParts) > 1 {
			parts = yamlParts
		}
	}

	// 如果没有找到 YAML 分割，尝试其他方法
	if len(parts) == 0 {
		// 可以添加其他多文档检测逻辑
		return nil, fmt.Errorf("无法解析多文档结构")
	}

	return parts, nil
}

// splitByFrontMatter 按 YAML front matter 分割
func (p *Processor) splitByFrontMatter(content string) []DocumentPart {
	var docParts []DocumentPart

	// 简单的实现：按 "---" 分割，然后解析每一块
	lines := strings.Split(content, "\n")
	var currentDoc strings.Builder
	var currentYAML strings.Builder
	inYAML := false
	var inContent bool

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		if trimmed == "---" {
			if !inYAML && !inContent {
				// 开始新的 YAML block
				inYAML = true
				continue
			} else if inYAML && !inContent {
				// YAML block 结束，内容开始
				inYAML = false
				inContent = true
				continue
			} else if inContent {
				// 当前文档结束，保存并开始新文档
				if currentDoc.Len() > 0 || currentYAML.Len() > 0 {
					p.addFrontMatterDoc(&docParts, currentYAML.String(), currentDoc.String())
				}

				// 重置状态
				currentDoc.Reset()
				currentYAML.Reset()
				inYAML = true
				inContent = false
				continue
			}
		}

		if inYAML {
			if currentYAML.Len() > 0 {
				currentYAML.WriteString("\n")
			}
			currentYAML.WriteString(line)
		} else if inContent {
			if currentDoc.Len() > 0 {
				currentDoc.WriteString("\n")
			}
			currentDoc.WriteString(line)
		} else {
			// 没有 YAML header 的情况，直接当作内容处理
			if currentDoc.Len() > 0 {
				currentDoc.WriteString("\n")
			}
			currentDoc.WriteString(line)
			inContent = true
		}
	}

	// 添加最后一个文档
	if currentDoc.Len() > 0 || currentYAML.Len() > 0 {
		p.addFrontMatterDoc(&docParts, currentYAML.String(), currentDoc.String())
	}

	// 如果没有找到任何文档，返回整个内容作为一个文档
	if len(docParts) == 0 {
		docParts = append(docParts, DocumentPart{
			Content:  strings.TrimSpace(content),
			Title:    p.extractTitle(content),
			Level:    1,
			Metadata: make(map[string]interface{}),
		})
	}

	return docParts
}

// addFrontMatterDoc 添加一个 front matter 文档
func (p *Processor) addFrontMatterDoc(docParts *[]DocumentPart, yamlContent, markdownContent string) {
	metadata := p.parseYAMLMetadata(yamlContent)
	content := strings.TrimSpace(markdownContent)

	title := p.extractTitle(content)
	if titleFromMeta, ok := metadata["title"].(string); ok && titleFromMeta != "" {
		title = titleFromMeta
	}

	if content != "" || len(metadata) > 0 {
		*docParts = append(*docParts, DocumentPart{
			Content:  content,
			Title:    title,
			Level:    1,
			Metadata: metadata,
		})
	}
}

// parseYAMLMetadata 解析 YAML 元数据（简单实现）
func (p *Processor) parseYAMLMetadata(yamlContent string) map[string]interface{} {
	metadata := make(map[string]interface{})
	lines := strings.Split(yamlContent, "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		if parts := strings.SplitN(line, ":", 2); len(parts) == 2 {
			key := strings.TrimSpace(parts[0])
			value := strings.TrimSpace(parts[1])
			// 移除引号
			value = strings.Trim(value, `"'`)
			metadata[key] = value
		}
	}

	return metadata
}

// convertToDocumentParts 将字符串数组转换为 DocumentPart
func (p *Processor) convertToDocumentParts(parts []string) []DocumentPart {
	var docParts []DocumentPart
	for _, part := range parts {
		if strings.TrimSpace(part) != "" {
			docParts = append(docParts, DocumentPart{
				Content: strings.TrimSpace(part),
				Title:   p.extractTitle(part),
				Level:   1,
			})
		}
	}
	return docParts
}

// applyLengthConstraints 应用长度约束和重叠配置
func (p *Processor) applyLengthConstraints(parts []DocumentPart) []DocumentPart {
	if p.Config == nil {
		return parts
	}

	var result []DocumentPart
	for _, part := range parts {
		// 如果文档太短，跳过
		if len(part.Content) < p.Config.MinLength {
			continue
		}

		// 如果文档太长，分割
		if len(part.Content) > p.Config.MaxLength {
			subParts := p.splitLongDocument(part)
			result = append(result, subParts...)
		} else {
			result = append(result, part)
		}
	}

	return result
}

// splitLongDocument 分割过长的文档
func (p *Processor) splitLongDocument(part DocumentPart) []DocumentPart {
	var parts []DocumentPart
	content := part.Content
	maxLen := p.Config.MaxLength
	overlap := p.Config.OverlapSize

	// 安全检查：防止无限循环
	maxIterations := 100
	iterations := 0

	for len(content) > maxLen && iterations < maxIterations {
		iterations++

		// 找到合适的分割点（优先在句号、换行符处分割）
		splitPos := p.findBestSplitPosition(content, maxLen)

		// 安全检查：确保分割位置有效
		if splitPos <= 0 {
			splitPos = maxLen / 2 // 强制分割
		}
		if splitPos >= len(content) {
			break
		}

		// 创建当前部分
		currentPart := DocumentPart{
			Content:  content[:splitPos],
			Title:    part.Title + fmt.Sprintf(" (第%d部分)", len(parts)+1),
			Level:    part.Level,
			Metadata: part.Metadata,
		}
		parts = append(parts, currentPart)

		// 计算下一部分的起始位置（考虑重叠）
		nextStart := splitPos - overlap
		if nextStart < 0 || nextStart >= splitPos {
			nextStart = splitPos // 确保前进
		}

		// 确保实际前进，防止无限循环
		if nextStart >= len(content) {
			break
		}

		content = content[nextStart:]

		// 额外的安全检查
		if len(content) <= overlap {
			break
		}
	}

	// 添加最后一部分
	if len(content) > p.Config.MinLength {
		parts = append(parts, DocumentPart{
			Content:  content,
			Title:    part.Title + fmt.Sprintf(" (第%d部分)", len(parts)+1),
			Level:    part.Level,
			Metadata: part.Metadata,
		})
	}

	// 如果没有成功分割，返回原文档
	if len(parts) == 0 {
		return []DocumentPart{part}
	}

	return parts
}

// findBestSplitPosition 找到最佳分割位置
func (p *Processor) findBestSplitPosition(content string, maxPos int) int {
	if maxPos >= len(content) {
		return len(content)
	}

	// 优先在句号后分割
	for i := maxPos - 1; i > maxPos-100 && i >= 0; i-- {
		if content[i] == '.' && i+1 < len(content) && content[i+1] == ' ' {
			return i + 1
		}
	}

	// 其次在换行符处分割
	for i := maxPos - 1; i > maxPos-100 && i >= 0; i-- {
		if content[i] == '\n' {
			return i + 1
		}
	}

	// 最后在空格处分割
	for i := maxPos - 1; i > maxPos-50 && i >= 0; i-- {
		if content[i] == ' ' {
			return i + 1
		}
	}

	return maxPos
}

// DocumentPart 表示文档的一个部分
type DocumentPart struct {
	Content  string
	Title    string
	Level    int
	Metadata map[string]interface{} // 新增：元数据
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

// SetCustomSplitter 设置自定义分割器
func (p *Processor) SetCustomSplitter(splitter func(string) []string) {
	if p.Config == nil {
		p.Config = &SplitterConfig{}
	}
	p.Config.CustomSplitter = splitter
}

// SetLengthConstraints 设置长度约束
func (p *Processor) SetLengthConstraints(minLength, maxLength int) {
	if p.Config == nil {
		p.Config = &SplitterConfig{}
	}
	p.Config.MinLength = minLength
	p.Config.MaxLength = maxLength
}

// SetOverlapSize 设置重叠大小
func (p *Processor) SetOverlapSize(size int) {
	if p.Config == nil {
		p.Config = &SplitterConfig{}
	}
	p.Config.OverlapSize = size
}
