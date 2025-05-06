#!/bin/bash

# 脚本功能：将.autocoderrules目录下的所有markdown文件复制到.cursor/rules目录
# 如果有重名文件，强制替换

# 获取当前工作目录
CURRENT_DIR=$(pwd)

# 源目录和目标目录
SOURCE_DIR="${CURRENT_DIR}/.autocoderrules"
TARGET_DIR="${CURRENT_DIR}/.cursor/rules"

# 检查源目录是否存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "错误: 源目录 $SOURCE_DIR 不存在!"
    exit 1
fi

# 检查目标目录是否存在，如果不存在则创建
if [ ! -d "$TARGET_DIR" ]; then
    echo "目标目录 $TARGET_DIR 不存在，正在创建..."
    mkdir -p "$TARGET_DIR"
    if [ $? -ne 0 ]; then
        echo "错误: 无法创建目标目录 $TARGET_DIR!"
        exit 1
    fi
fi

echo "开始复制文件..."

# 找到所有markdown文件并保存到临时数组
files=($(find "$SOURCE_DIR" -type f -name "*.md"))
TOTAL_FILES=${#files[@]}
COPIED_FILES=0

# 遍历所有找到的文件进行复制
for file in "${files[@]}"; do
    # 获取文件名
    filename=$(basename "$file")
    
    # 复制文件到目标目录，强制覆盖已存在的文件
    cp -f "$file" "$TARGET_DIR/"
    
    if [ $? -eq 0 ]; then
        COPIED_FILES=$((COPIED_FILES + 1))
        echo "已复制: $filename"
    else
        echo "复制失败: $filename"
    fi
done

echo "操作完成!"
echo "总共找到 $TOTAL_FILES 个markdown文件"
echo "成功复制 $COPIED_FILES 个文件到 $TARGET_DIR"

# 给脚本执行权限
chmod +x "$0" 