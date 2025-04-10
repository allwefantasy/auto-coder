#!/usr/bin/env python
"""
Anything2Img Demo Script
========================

This script demonstrates how to use the Anything2Img utility to convert PDF and DOCX 
documents into Markdown format with extracted text and images. It leverages a 
vision-language model (VL model) to analyze document pages and identify content.

Usage:
------
# Process a PDF file
python anything2img_demo.py --file_path="path/to/document.pdf" --output_dir="./output"

# Process a DOCX file
python anything2img_demo.py --file_path="path/to/document.docx" --output_dir="./result_folder"

# Process only the first 3 pages with 8 parallel workers
python anything2img_demo.py --file_path="path/to/document.pdf" --pages=3 --workers=8

# Process a document with a specific VL model
python anything2img_demo.py --file_path="/Users/allwefantasy/Downloads/DeepSeek_V3.pdf" --pages=7 --workers=7 --model_name=doubao_vl

Arguments:
----------
--file_path (required): Path to the PDF or DOCX file to convert
--output_dir (optional): Directory to save extracted images and output (default: ./output)
--pages (optional): Number of pages to process, -1 for all pages (default: -1)
--workers (optional): Number of parallel workers for processing (default: 4)
--product_mode (optional): Product mode for LLM initialization [pro|lite] (default: lite)
--model_name (optional): Vision-language model to use (default: doubao_vl)

Output:
-------
1. A markdown file with the extracted content from the document
2. Extracted images saved in the _images subdirectory of the output folder
"""

import os
import sys
from pathlib import Path
from autocoder.utils.llms import get_single_llm
from autocoder.common.anything2img import Anything2Img
from autocoder.common import AutoCoderArgs
import argparse
import time

def main():
    """
    Demo script for the Anything2Img class that converts documents to markdown
    with extracted text and images using a vision-language model.
    """
    parser = argparse.ArgumentParser(description='Convert documents to markdown using VL model')
    parser.add_argument('--file_path', type=str, required=True, 
                        help='Path to the PDF or DOCX file to convert')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='Directory to save extracted images and temporary files')
    parser.add_argument('--pages', type=int, default=-1,
                        help='Number of pages to process, -1 for all pages')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of parallel workers for processing')
    parser.add_argument('--product_mode', type=str, default='lite',
                        choices=['pro', 'lite'], help='Product mode for LLM initialization')
    parser.add_argument('--model_name', type=str, default='doubao_vl',
                        help='Vision-language model to use')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Initializing LLM with model: {args.model_name}")
    # Get the LLM object with the specified model
    llm = get_single_llm(args.model_name, args.product_mode)
    
    # Prepare AutoCoderArgs
    autocoder_args = AutoCoderArgs(
        output=args.output_dir
    )
    
    print(f"Creating Anything2Img instance")
    # Create an instance of Anything2Img
    converter = Anything2Img(
        llm=llm,
        args=autocoder_args,
        keep_conversion=True  # Keep the intermediate conversion files
    )
    
    print(f"Processing file: {args.file_path}")
    # Record start time
    start_time = time.time()
    
    # Convert the document to markdown
    markdown_content = converter.to_markdown(
        file_path=args.file_path,
        size=args.pages,
        max_workers=args.workers
    )
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Save the markdown content to a file
    output_markdown_path = os.path.join(
        args.output_dir, 
        os.path.basename(args.file_path) + '.md'
    )
    
    with open(output_markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"Conversion complete in {execution_time:.2f} seconds!")
    print(f"Markdown saved to: {output_markdown_path}")
    print(f"Extracted images saved to: {os.path.join(args.output_dir, '_images')}")
    print(f"Total pages processed: {args.pages if args.pages > 0 else 'all'}")
    print(f"Workers used: {args.workers}")

if __name__ == "__main__":
    main() 