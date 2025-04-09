
import os
import byzerllm
from byzerllm.utils.client import code_utils
import traceback
from loguru import logger

# Placeholder for potential PaddleOCR import and initialization
# try:
#     import paddleocr
#     PADDLE_OCR_AVAILABLE = True
# except ImportError:
#     PADDLE_OCR_AVAILABLE = False
#     logger.warning("paddleocr not installed. PaddleOCR extraction method will not be available.")

PADDLE_OCR_AVAILABLE = False # Explicitly disable until implementation is added


class ImageLoader:
    """
    Extracts text and table information from images using a Vision Language Model (VL)
    or optionally PaddleOCR, saving the result as a Markdown file.
    """
    def __init__(self, llm: byzerllm.ByzerLLM):
        """
        Initializes the ImageLoader.

        Args:
            llm (byzerllm.ByzerLLM): The ByzerLLM instance, expected to have a VL model client configured.
        """
        self.llm = llm
        if llm.get_sub_client("vl_model"):
            self.vl_model = llm.get_sub_client("vl_model")
            logger.info("Using VL model client from ByzerLLM.")
        else:
            # Fallback to the main LLM instance if specific vl_model client is not found
            self.vl_model = self.llm
            logger.warning("Specific 'vl_model' client not found in ByzerLLM. Using the main LLM instance. Ensure it supports vision capabilities.")

        # Placeholder for PaddleOCR engine initialization
        self.ocr_engine = None
        # if PADDLE_OCR_AVAILABLE:
        #     try:
        #         # Example: Initialize PaddleOCR (adjust parameters as needed)
        #         # self.ocr_engine = paddleocr.PaddleOCR(use_angle_cls=True, lang='ch') # Common languages: 'ch', 'en', 'fr', 'german', 'korean', 'japan'
        #         # logger.info("PaddleOCR engine initialized.")
        #         logger.info("PaddleOCR library is available but engine initialization is commented out.")
        #     except Exception as e:
        #         logger.error(f"Failed to initialize PaddleOCR engine: {e}")
        #         PADDLE_OCR_AVAILABLE = False # Disable if initialization fails

    @byzerllm.prompt() # Decorator associates the prompt with the main LLM by default
    def _extract_text_with_vl(self, image_path: str) -> str:
        """
        {{ image }}
        Analyze the image provided. Extract all text content visible in the image.
        If you identify any tables within the image, please represent them accurately using Markdown table syntax.
        Structure the output clearly. Combine all extracted text and Markdown tables into a single Markdown formatted string.
        Return only the final Markdown string, without any additional explanations or preamble.
        """
        try:
            image = byzerllm.Image.load_image_from_path(image_path)
            return {"image": image}
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            raise

    def _extract_text_with_paddle(self, image_path: str) -> str:
        """
        Extracts text using PaddleOCR. (Placeholder - requires implementation)
        """
        if not PADDLE_OCR_AVAILABLE or not self.ocr_engine:
            logger.error("PaddleOCR is not available or not initialized.")
            raise NotImplementedError("PaddleOCR extraction is not available or implemented.")

        logger.info(f"Starting PaddleOCR extraction for {image_path}...")
        try:
            # Placeholder for actual PaddleOCR implementation
            # result = self.ocr_engine.ocr(image_path, cls=True)
            # # Process 'result' to extract text and potentially detect/format tables
            # # This basic example just joins lines:
            # if result and result[0]:
            #      text_content = "\n".join([line[1][0] for line in result[0] if line and len(line) >= 2])
            # else:
            #      text_content = ""
            # logger.info(f"PaddleOCR extraction successful for {image_path}.")
            # return text_content
            text_content = f"## PaddleOCR Placeholder\n\nText extracted from {os.path.basename(image_path)}\n(Full implementation pending)"
            logger.warning("PaddleOCR extraction called, but using placeholder implementation.")
            return text_content
        except Exception as e:
            logger.error(f"Error during PaddleOCR extraction for {image_path}: {e}")
            traceback.print_exc()
            raise

    def extract_text_and_save_md(self, image_path: str, output_dir: str = None, method: str = "vl") -> str:
        """
        Extracts text from an image using the specified method and saves it to a Markdown file.

        Args:
            image_path (str): Path to the input image file.
            output_dir (str, optional): Directory to save the Markdown file. Defaults to the image's directory.
            method (str): Extraction method ('vl' for Vision Language Model, 'paddle' for PaddleOCR). Defaults to 'vl'.

        Returns:
            str: Path to the generated Markdown file.

        Raises:
            ValueError: If an unsupported method is specified or required resources are unavailable.
            FileNotFoundError: If the input image path does not exist.
            Exception: If extraction or file writing fails.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        logger.info(f"Starting text extraction from {image_path} using method: {method}")

        extracted_content = ""
        try:
            if method == "vl":
                # Run the prompt using the configured VL model client
                raw_result = self._extract_text_with_vl.with_llm(self.vl_model).run(image_path=image_path)

                # Extract Markdown content if the LLM wraps it
                extracted_content = code_utils.extract_markdown_content(raw_result)
                if not extracted_content: # If no markdown block detected, use the raw result
                    extracted_content = raw_result
                logger.info(f"VL model extraction successful for {image_path}.")

            elif method == "paddle":
                if not PADDLE_OCR_AVAILABLE:
                     raise ValueError("PaddleOCR method requested, but the library is not installed or available.")
                extracted_content = self._extract_text_with_paddle(image_path)
            else:
                raise ValueError(f"Unsupported extraction method: {method}. Choose 'vl' or 'paddle'.")

        except Exception as e:
            logger.error(f"Extraction failed for {image_path} using method {method}: {e}")
            traceback.print_exc()
            # Optionally, implement fallback logic here, e.g., try 'paddle' if 'vl' fails
            raise  # Re-raise the exception after logging

        # Determine output path
        if output_dir is None:
            output_dir = os.path.dirname(image_path)
        os.makedirs(output_dir, exist_ok=True) # Ensure output directory exists

        base_name = os.path.splitext(os.path.basename(image_path))[0]
        md_file_path = os.path.join(output_dir, f"{base_name}.md")

        # Save the extracted content to the Markdown file
        try:
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(extracted_content)
            logger.info(f"Successfully extracted text to: {md_file_path}")
        except IOError as e:
            logger.error(f"Error writing Markdown file {md_file_path}: {e}")
            raise # Re-raise the exception

        return md_file_path

# Example usage (for demonstration purposes):
# if __name__ == '__main__':
#     # This block is for testing and will not run when imported
#     # You would need to initialize ByzerLLM properly in your actual application
#     try:
#         llm_instance = byzerllm.ByzerLLM()
#         # Configure llm_instance, potentially setting up vl_model client
#         # e.g., llm_instance.setup_sub_client("vl_model", ...)
#
#         # Check if a VL model is configured (replace with actual check)
#         if not llm_instance.get_sub_client("vl_model"):
#              print("Warning: 'vl_model' sub_client not configured in ByzerLLM. Ensure the main client supports vision.")
#
#         loader = ImageLoader(llm_instance)
#
#         # Create a dummy image file path for testing structure
#         dummy_image_path = "dummy_image.png"
#         # Create a dummy file for the test to pass the exists check
#         # with open(dummy_image_path, "w") as f: f.write("dummy")
#
#         print(f"Attempting to process: {dummy_image_path} (Note: This requires a real image and configured LLM/VL model)")
#
#         # md_path = loader.extract_text_and_save_md(dummy_image_path, method="vl")
#         # print(f"Markdown would be saved to: {md_path}")
#
#         # os.remove(dummy_image_path) # Clean up dummy file
#
#     except ImportError as ie:
#         print(f"Import error: {ie}. Please ensure ByzerLLM is installed.")
#     except FileNotFoundError as fnfe:
#          print(f"File not found: {fnfe}. Please provide a valid image path for testing.")
#     except Exception as ex:
#         print(f"An error occurred during example execution: {ex}")
#         traceback.print_exc()

