from autocoder.chat_auto_coder_lang import MESSAGES

def transform_messages():
    # 创建一个新的字典来存储转换后的消息
    transformed = {}
    
    # 遍历原始的 MESSAGES 字典
    for key, value in MESSAGES.items():
        # 如果值已经是字典格式且包含 'en' 和 'zh' 键，则直接使用
        if isinstance(value, dict) and 'en' in value and 'zh' in value:
            transformed[key] = value
        # 否则，创建新的格式
        else:
            transformed[key] = {
                'en': str(value),
                'zh': ''
            }
    
    # 生成新的 Python 文件内容
    output = 'MESSAGES = ' + str(transformed).replace("}, '", "},\n    '")
    
    # 将转换后的内容写入新文件
    with open('transformed_messages.py', 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == '__main__':
    transform_messages()
    print('转换完成，请查看 transformed_messages.py 文件')