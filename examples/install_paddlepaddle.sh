
#!/bin/bash

# 安装 PaddlePaddle 和 PaddleOCR 的脚本
# 使用说明: 
# 1. 给脚本执行权限: chmod +x install_paddlepaddle.sh
# 2. 运行脚本: ./install_paddlepaddle.sh

echo "正在安装 PaddlePaddle 和 PaddleOCR..."

# 检查是否已安装 Python3
if ! command -v python3 &> /dev/null
then
    echo "Python3 未安装，请先安装 Python3"
    exit 1
fi

# 检查 pip 是否可用
if ! command -v pip3 &> /dev/null
then
    echo "pip3 未安装，请先安装 pip3"
    exit 1
fi

# 安装 PaddlePaddle (CPU版本)
echo "安装 PaddlePaddle CPU 版本..."
pip3 install paddlepaddle -i https://mirror.baidu.com/pypi/simple

# 安装 PaddleOCR
echo "安装 PaddleOCR..."
pip3 install "paddleocr>=2.0.1" -i https://mirror.baidu.com/pypi/simple

# 验证安装
echo "验证安装..."
python3 -c "
try:
    import paddle
    import paddleocr
    print('PaddlePaddle 版本:', paddle.__version__)
    print('PaddleOCR 安装成功!')
except ImportError as e:
    print('安装失败:', e)
    exit(1)
"

echo "安装完成!"
