#!/bin/bash

# 项目名称
project="auto_coder"

# 使用Python一行命令提取版本号，减少对grep和cut的依赖
version=$(python -c "with open('src/autocoder/version.py') as f: print([line.split('=')[1].strip().strip('\"') for line in f if '__version__' in line][0])")
echo "Version: $version"

# 清理dist目录
echo "Clean dist"
rm -rf ./dist/*

# 卸载当前安装的项目版本
echo "Uninstall ${project}"
pip uninstall -y ${project}

# 构建项目
echo "Build ${project} ${version}"
python setup.py sdist bdist_wheel
cd ./dist/

# 安装新构建的项目版本
echo "Install ${project} ${version}"
pip install ${project}-${version}-py3-none-any.whl && cd -

# 默认模式设定
export MODE=${MODE:-"release"}

# 发布模式下的操作
if [[ ${MODE} == "release" ]]; then
 git tag v${version}
 git push origin v${version}  # 请根据实际情况使用正确的远程仓库名
 echo "Upload ${project} ${version}"
 twine upload dist/*
fi

