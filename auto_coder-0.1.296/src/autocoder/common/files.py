from autocoder.common.auto_coder_lang import get_message_with_format
from typing import List, Dict, Union, Generator, Tuple

def read_file(file_path):
    """Read a file with automatic encoding detection.
    
    Tries common encodings in sequence to handle cross-platform encoding issues.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        str: The file contents as a string
        
    Raises:
        ValueError: If the file cannot be decoded with any of the tried encodings
    """
    # Expanded list of encodings to try
    encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1', 
                'big5', 'shift_jis', 'euc-jp', 'iso-8859-1',
                'cp1252', 'ascii']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # Log other errors but continue trying other encodings
            continue
            
    # If all encodings fail, try reading as binary and decode with 'replace'
    try:
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    except Exception as e:
        raise ValueError(get_message_with_format("file_decode_error", 
            file_path=file_path, 
            encodings=", ".join(encodings)))

def read_lines(file_path:str):
    """Read a file line by line with automatic encoding detection.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        List[str]: List of lines in the file
        
    Raises:
        ValueError: If the file cannot be decoded with any of the tried encodings
    """
    # Expanded list of encodings to try
    encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1', 
                'big5', 'shift_jis', 'euc-jp', 'iso-8859-1',
                'cp1252', 'ascii']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # Log other errors but continue trying other encodings
            continue
            
    # If all encodings fail, try reading as binary and decode with 'replace'
    try:
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace').splitlines()
    except Exception as e:
        raise ValueError(get_message_with_format("file_decode_error", 
            file_path=file_path, 
            encodings=", ".join(encodings)))



def read_file_with_line_numbers(file_path: str,line_number_start:int=0) -> Generator[Tuple[int, str], None, None]:
    """Read a file and return its content with line numbers.

    Args:
        file_path (str): Path to the file to read

    Returns:
        List[str]: A list of strings where each string is in the format "line_number:line_content"

    Raises:
        ValueError: If the file cannot be decoded with any of the tried encodings
    """
    encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                for line_number, line in enumerate(file, start=line_number_start):
                    yield (line_number, line)                
        except UnicodeDecodeError:
            continue

    raise ValueError(get_message_with_format("file_decode_error", 
        file_path=file_path, 
        encodings=", ".join(encodings)))


def save_file(file_path: str, content: Union[str, List[str]]) -> None:
    """Save content to a file using UTF-8 encoding.
    
    Args:
        file_path (str): Path to the file to write
        content (Union[str, List[str]]): Content to write to the file. 
            Can be a string or list of strings (will be joined with newlines)
        
    Raises:
        IOError: If the file cannot be written
        TypeError: If content is neither str nor List[str]
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if isinstance(content, str):
                f.write(content)
            elif isinstance(content, list):
                f.write('\n'.join(content))
            else:
                raise TypeError("Content must be either str or List[str]")
    except IOError as e:
        raise IOError(get_message_with_format("file_write_error",
            file_path=file_path,
            error=str(e)))
