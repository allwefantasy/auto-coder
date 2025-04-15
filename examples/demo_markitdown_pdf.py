#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo script showing how to use the MarkItDown module to convert PDF files to Markdown.
This script demonstrates how to initialize MarkItDown and convert a local PDF file.

Usage:
    python demo_markitdown_pdf.py path/to/your/document.pdf

"""

import os
import sys
import argparse
from pathlib import Path

# Import the MarkItDown class from the autocoder module
from autocoder.utils._markitdown import MarkItDown

def main():
    """
    Main function that parses command line arguments and converts a PDF file to Markdown.
    """
    parser = argparse.ArgumentParser(description='Convert PDF file to Markdown using MarkItDown.')
    parser.add_argument('pdf_path', help='Path to the PDF file to convert')
    parser.add_argument('--output', '-o', help='Output directory for images (default: "_images" in the same directory as the PDF)')
    
    args = parser.parse_args()
    
    # Check if the file exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    # Check if it's a PDF file
    if pdf_path.suffix.lower() != '.pdf':
        print(f"Error: {pdf_path} is not a PDF file")
        return 1
    
    # Create the image output directory if specified
    image_output_dir = None
    if args.output:
        image_output_dir = Path(args.output)
        image_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize MarkItDown
    print(f"Initializing MarkItDown...")
    markitdown = MarkItDown()
    
    # Convert the PDF file
    print(f"Converting {pdf_path}...")
    try:
        kwargs = {}
        if image_output_dir:
            kwargs['image_output_dir'] = str(image_output_dir)
        
        result = markitdown.convert(str(pdf_path), **kwargs)
        
        # Print some information about the result
        print("\nConversion successful!")
        
        # Calculate statistics
        lines = result.text_content.split('\n')
        words = result.text_content.split()
        chars = len(result.text_content)
        images = result.text_content.count('![Image')
        
        print(f"\nStatistics:")
        print(f"- Lines: {len(lines)}")
        print(f"- Words: {len(words)}")
        print(f"- Characters: {chars}")
        print(f"- Images extracted: {images}")
        
        # Save the markdown content to a file
        output_file = pdf_path.with_suffix('.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        print(f"\nMarkdown content saved to: {output_file}")
        
        # Print a sample of the content
        preview_length = min(500, len(result.text_content))
        print(f"\nPreview of the first {preview_length} characters:")
        print("-" * 40)
        print(result.text_content[:preview_length] + "...")
        print("-" * 40)
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 