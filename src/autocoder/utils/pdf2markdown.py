from markitdown import MarkItDown
import os
import sys

def convert_pdf_to_markdown(pdf_path: str, output_path: str = None) -> str:
    """
    Convert PDF file to Markdown format
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the markdown file. If None, return the markdown content
        
    Returns:
        str: Markdown content if output_path is None, otherwise None
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
    # Initialize MarkItDown
    mid = MarkItDown()
    
    try:
        # Convert PDF to markdown
        result = mid.convert(pdf_path)
        
        # Get the markdown content
        markdown_content = result.text_content
        
        if output_path:
            # Write to file if output path is specified
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            return None
        else:
            # Return the content if no output path
            return markdown_content
            
    except Exception as e:
        print(f"Error converting PDF to Markdown: {str(e)}", file=sys.stderr)
        raise

def main():
    """Command line interface for PDF to Markdown conversion"""
    if len(sys.argv) < 2:
        print("Usage: python pdf2markdown.py <pdf_path> [output_path]")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = convert_pdf_to_markdown(pdf_path, output_path)
        if result:  # If no output_path specified, print to stdout
            print(result)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()