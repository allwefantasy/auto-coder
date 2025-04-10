#!/usr/bin/env python
"""
Object Detection Demo Script
===========================

This script demonstrates how to use the Anything2Img utility for object detection
in images. It uses a vision-language model to identify objects and their bounding boxes
in an input image.

Usage:
------
# Detect objects in an image
python object_detection_demo.py --image_path="path/to/image.jpg" --output_dir="./output"

# Extract detected objects as separate images
python object_detection_demo.py --image_path="path/to/image.jpg" --extract_objects

Arguments:
----------
--image_path (required): Path to the image file to analyze
--output_dir (optional): Directory to save visualization (default: ./output)
--product_mode (optional): Product mode for LLM initialization [pro|lite] (default: lite)
--visualize (optional): Whether to create visualization of bounding boxes (default: True)
--extract_objects (optional): Whether to extract detected objects as separate images (default: False)

Output:
-------
1. Console output with detected objects and their coordinates
2. If visualize=True, a visualization of the image with bounding boxes
3. If extract_objects=True, individual images for each detected object


python object_detection_demo.py --image_path="/Users/allwefantasy/projects/auto-coder/notebooks/output/DeepSeek_V3.pdf_page1.png" --output_dir="./output2" --model_name doubao_vl
"""

import os
import sys
import argparse
import json
import time
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
import random

from autocoder.utils.llms import get_single_llm
from autocoder.common.anything2img import Anything2Img
from autocoder.common import AutoCoderArgs
from byzerllm.utils.client import code_utils

# qvq_72b,doubao_vl
class ObjectDetection:
    def __init__(self, model_name="qvq_72b", product_mode="lite", output_dir="./output"):
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the LLM object with the specified model
        print(f"Initializing LLM with model: {model_name}")
        self.llm = get_single_llm(model_name, product_mode)
        
        # Prepare AutoCoderArgs
        self.autocoder_args = AutoCoderArgs(
            output=output_dir
        )
        
        # Create an instance of Anything2Img
        self.converter = Anything2Img(
            llm=self.llm,
            args=self.autocoder_args,
            keep_conversion=True
        )
        
        self.output_dir = output_dir
    
    def detect_objects(self, image_path):
        """Detect objects in an image using the VL model"""
        print(f"Analyzing image: {image_path}")
        # Use the new detect_objects method
        start_time = time.time()
        result = self.converter.detect_objects.with_llm(
            self.converter.vl_model
        ).run(image_path)
        end_time = time.time()
        
        # Calculate execution time
        execution_time = end_time - start_time
        print(f"Detection completed in {execution_time:.2f} seconds")
        
        # Convert the string result to a dictionary
        result = code_utils.extract_code(result)[-1][1]
        result = json.loads(result)
        return result, execution_time
    
    def extract_objects(self, image_path, detection_result):
        """Extract each detected object as a separate image"""
        extracted_paths = []
        
        print(f"\n===== Extracting Objects =====")
        for i, obj in enumerate(detection_result.get("objects", [])):
            # Get bbox from the bounding_box field
            if "bounding_box" in obj:
                bbox = obj["bounding_box"]
                
                # Only process if we have valid coordinates
                if len(bbox) == 4 and all(coord >= 0 for coord in bbox) and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                    output_filename = f"image_region_{i+1}.png"
                    
                    # Extract the object region
                    output_path = self.converter.extract_image_region(
                        image_path=image_path,
                        bbox=bbox,
                        output_filename=output_filename
                    )
                    
                    extracted_paths.append(output_path)
                    print(f"Extracted image region {i+1} to: {output_path}")
                    
        return extracted_paths
    
    def visualize_objects(self, image_path, detection_result, output_path=None):
        """Create a visualization of the detected objects"""
        # Open the image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Generate random colors for each object
        colors = []
        for _ in range(len(detection_result.get("objects", []))):
            color = (random.randint(0, 255), 
                     random.randint(0, 255), 
                     random.randint(0, 255))
            colors.append(color)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Draw each bounding box and label
        for i, obj in enumerate(detection_result.get("objects", [])):
            # Get bbox from the bounding_box field
            if "bounding_box" in obj:
                bbox = obj["bounding_box"]
                
                if len(bbox) == 4 and all(coord >= 0 for coord in bbox) and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                    # Draw rectangle
                    draw.rectangle(bbox, outline=colors[i], width=3)
                    
                    # Draw label (object description if available, otherwise just the number)
                    label = obj.get("text", f"Image {i+1}")
                    draw.text((bbox[0], bbox[1]-20), label, fill=colors[i], font=font)
        
        # Save the visualization
        if output_path is None:
            base_name = os.path.basename(image_path)
            output_path = os.path.join(self.output_dir, f"detected_{base_name}")
        
        image.save(output_path)
        print(f"Visualization saved to: {output_path}")
        
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Detect objects in images using VL model')
    parser.add_argument('--image_path', type=str, required=True,
                        help='Path to the image file to analyze')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='Directory to save visualization')
    parser.add_argument('--product_mode', type=str, default='lite',
                        choices=['pro', 'lite'], help='Product mode for LLM initialization')
    parser.add_argument('--visualize', action='store_true', default=True,
                        help='Whether to create visualization of bounding boxes')
    parser.add_argument('--extract_objects', action='store_true', default=False,
                        help='Whether to extract detected objects as separate images')
    parser.add_argument('--model_name', type=str, default="qvq_72b",
                        help='Vision-language model to use')
    
    args = parser.parse_args()
    
    # Initialize the object detection utility
    detector = ObjectDetection(
        model_name=args.model_name,
        product_mode=args.product_mode,
        output_dir=args.output_dir
    )
    
    # Detect objects and measure time
    detection_result, execution_time = detector.detect_objects(args.image_path)
    
    # Print execution time
    print(f"\n===== Performance =====")
    print(f"Model: {args.model_name}")
    print(f"Image: {os.path.basename(args.image_path)}")
    print(f"Detection time: {execution_time:.2f} seconds")
    
    # Print results
    print("\n===== Detection Results =====")
    if isinstance(detection_result, dict) and "objects" in detection_result:
        print(f"Found {len(detection_result['objects'])} image regions:")
        for i, obj in enumerate(detection_result['objects']):
            print(f"Image region {i+1}:")
            if "bounding_box" in obj:
                bbox = obj["bounding_box"]
                print(f"  Bounding box: [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
                if "text" in obj:
                    print(f"  Description: {obj['text']}")
    else:
        print("No structured object data found in the result.")
        print(f"Raw result: {detection_result}")
    
    # Create visualization if requested
    if args.visualize and isinstance(detection_result, dict) and "objects" in detection_result:
        viz_path = detector.visualize_objects(args.image_path, detection_result)
        
        # Show the visualization
        try:
            img = Image.open(viz_path)
            plt.figure(figsize=(10, 10))
            plt.imshow(np.array(img))
            plt.axis('off')
            plt.title(f"Detected Image Regions - {execution_time:.2f}s")
            plt.show()
        except Exception as e:
            print(f"Failed to display visualization: {e}")
    
    # Extract objects if requested
    if args.extract_objects and isinstance(detection_result, dict) and "objects" in detection_result:
        extracted_paths = detector.extract_objects(args.image_path, detection_result)
        
        # Show the extracted objects
        if extracted_paths:
            try:
                # Create a grid of extracted images
                cols = min(3, len(extracted_paths))
                rows = (len(extracted_paths) + cols - 1) // cols
                
                fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
                if rows == 1 and cols == 1:
                    axes = np.array([axes])  # Ensure axes is a numpy array for indexing
                axes = axes.flatten()
                
                for i, path in enumerate(extracted_paths):
                    if i < len(axes):
                        img = Image.open(path)
                        axes[i].imshow(np.array(img))
                        axes[i].set_title(f"Image region {i+1}")
                        axes[i].axis('off')
                
                # Hide any unused subplots
                for i in range(len(extracted_paths), len(axes)):
                    axes[i].axis('off')
                    
                plt.tight_layout()
                plt.show()
            except Exception as e:
                print(f"Failed to display extracted objects: {e}")

if __name__ == "__main__":
    main() 