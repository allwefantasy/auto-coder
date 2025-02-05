from autocoder.common.auto_coder_lang import get_message_with_format

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
            
    raise ValueError(get_message_with_format("file_decode_error", 
        file_path=file_path, 
        encodings=", ".join(encodings)))



def save_file(file_path: str, content: str) -> None:
    """Save content to a file using UTF-8 encoding.
    
    Args:
        file_path (str): Path to the file to write
        content (str): Content to write to the file
        
    Raises:
        IOError: If the file cannot be written
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except IOError as e:
        raise IOError(get_message_with_format("file_write_error",
            file_path=file_path,
            error=str(e)))