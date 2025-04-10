#!/usr/bin/env python
import os
import sys
from pathlib import Path
from autocoder.utils.llms import get_single_llm
from autocoder.common.anything2img import Anything2Img
from autocoder.common import AutoCoderArgs
import argparse

def main():
    
    model = "doubao_vl"
    # model = "qvq_72b"

    print(f"Initializing LLM with model: {model}")

    # Get the LLM object with the "doubao_vl" model
    llm = get_single_llm(model, "lite")
    
    # Prepare AutoCoderArgs
    autocoder_args = AutoCoderArgs(
        output="./output2"
    )
    
    print(f"Creating Anything2Img instance")
    # Create an instance of Anything2Img
    converter = Anything2Img(
        llm=llm,
        args=autocoder_args,
        keep_conversion=True  # Keep the intermediate conversion files
    )
    
    print(converter.detect_objects.with_llm(llm).run("/Users/allwefantasy/projects/auto-coder/notebooks/output/DeepSeek_V3.pdf_page1.png"))

if __name__ == "__main__":
    main() 