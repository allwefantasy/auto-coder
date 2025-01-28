def read_file(file_path):
    """Read a file with automatic encoding detection.
    
    Tries common encodings in sequence (UTF-8 > GBK > UTF-16 > Latin-1) to handle
    cross-platform encoding issues between Windows and Linux systems.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        str: The file contents as a string
        
    Raises:
        ValueError: If the file cannot be decoded with any of the tried encodings
    """
    encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                return content
        except UnicodeDecodeError:
            continue
            
    raise ValueError(f"无法解码文件: {file_path}。尝试的编码: {', '.join(encodings)}")