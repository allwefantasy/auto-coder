import os
import mimetypes
from pathlib import Path


class FileTypeDetector:
    """文件类型检测器，用于判断文件类型和编码"""
    
    # 常见的文本文件MIME类型前缀
    TEXT_MIME_PREFIXES = ('text/', 'application/json', 'application/xml', 'application/javascript')
    
    # 常见的文本文件扩展名
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass',
        '.json', '.xml', '.yaml', '.yml', '.ini', '.conf', '.sh', '.bash', '.zsh', '.c', '.cpp',
        '.h', '.hpp', '.java', '.kt', '.rs', '.go', '.rb', '.php', '.pl', '.swift', '.dart',
        '.vue', '.svelte', '.lua', '.r', '.sql', '.graphql', '.toml', '.csv'
    }
    
    @staticmethod
    def is_text_file(file_path: str) -> bool:
        """
        判断文件是否为文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为文本文件
        """
        # 首先通过扩展名判断
        ext = os.path.splitext(file_path)[1].lower()
        if ext in FileTypeDetector.TEXT_EXTENSIONS:
            return True
            
        # 通过MIME类型判断
        mime_type = FileTypeDetector.get_mime_type(file_path)
        if any(mime_type.startswith(prefix) for prefix in FileTypeDetector.TEXT_MIME_PREFIXES):
            return True
            
        # 通过文件内容判断
        try:
            with open(file_path, 'rb') as f:
                # 读取前4KB进行判断
                chunk = f.read(4096)
                # 检查是否包含空字节（二进制文件通常包含空字节）
                if b'\x00' in chunk:
                    return False
                # 尝试解码为UTF-8
                try:
                    chunk.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    # 尝试其他常见编码
                    for encoding in ['gbk', 'latin1', 'ascii']:
                        try:
                            chunk.decode(encoding)
                            return True
                        except UnicodeDecodeError:
                            continue
                    return False
        except (IOError, OSError):
            pass
            
        return False
    
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件编码，默认为utf-8
        """
        # 尝试常见编码
        encodings = ['utf-8', 'gbk', 'latin1', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(100)  # 尝试读取一小部分内容
                    return encoding
            except UnicodeDecodeError:
                continue
            except (IOError, OSError):
                break
                
        return 'utf-8'  # 默认编码
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """
        获取文件的MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MIME类型
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'  # 默认为二进制类型
