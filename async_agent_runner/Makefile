# Makefile for async_agent_runner

.PHONY: build install-user clean test help

# 变量
BINARY_NAME := async_agent_runner
BUILD_DIR := bin
INSTALL_DIR := $(HOME)/bin

# 默认目标
help:
	@echo "可用的 make 目标:"
	@echo "  build        - 构建二进制文件"
	@echo "  install-user - 安装到用户目录 (~/bin)"
	@echo "  clean        - 清理构建文件"
	@echo "  test         - 运行测试"
	@echo "  help         - 显示此帮助信息"

# 构建二进制文件
build:
	@echo "🔨 构建 $(BINARY_NAME)..."
	@mkdir -p $(BUILD_DIR)
	@go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME) .
	@echo "✅ 构建完成: $(BUILD_DIR)/$(BINARY_NAME)"

# 安装到用户目录
install-user: build
	@echo "📦 安装 $(BINARY_NAME) 到 $(INSTALL_DIR)..."
	@mkdir -p $(INSTALL_DIR)
	@cp $(BUILD_DIR)/$(BINARY_NAME) $(INSTALL_DIR)/
	@chmod +x $(INSTALL_DIR)/$(BINARY_NAME)
	@echo "✅ 安装完成"
	@echo "请确保 $(INSTALL_DIR) 在您的 PATH 中"

# 清理构建文件
clean:
	@echo "🧹 清理构建文件..."
	@rm -rf $(BUILD_DIR)
	@echo "✅ 清理完成"

# 运行测试
test:
	@echo "🧪 运行测试..."
	@go test ./...

# 构建所有平台
build-all:
	@echo "🔨 构建所有平台..."
	@mkdir -p $(BUILD_DIR)
	@GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 .
	@GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 .
	@GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-arm64 .
	@GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe .
	@echo "✅ 多平台构建完成" 