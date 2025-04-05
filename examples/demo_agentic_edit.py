import os
import sys
from typing import Iterator, Union, Generator
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.common import AutoCoderArgs, SourceCodeList
from autocoder.utils.llms import get_single_llm
from autocoder.agent.agentic_edit import (
    AgenticEdit,
    MemoryConfig,
    BaseTool,
    PlainTextOutput,
    ExecuteCommandTool,
    ReadFileTool,
    WriteToFileTool
)
from loguru import logger

# 1. Load tokenizer (Important for token counting if needed)
load_tokenizer()

# 2. Configure arguments
args = AutoCoderArgs(
    source_dir=".",  # Specify your project source directory
    model="v3_chat",  # Choose your LLM model
    product_mode="lite", # Or your specific product mode
    # Add other relevant args as needed
)

# 3. Get LLM instance
llm = get_single_llm(args.model, product_mode=args.product_mode)

# 4. Prepare necessary components for AgenticEdit
#    - SourceCodeList (can be empty or loaded from source_dir)
files = SourceCodeList(sources=[])
#    - MemoryConfig (dummy for this example)
def dummy_save_memory(memory: dict):
    logger.info("Dummy save memory called.")
memory_config = MemoryConfig(memory={}, save_memory_func=dummy_save_memory)
#    - Conversation history (empty for this example)
conversation_history = []

# 5. Instantiate AgenticEdit
agentic_editor = AgenticEdit(
    llm=llm,
    conversation_history=conversation_history,
    files=files,
    args=args,
    memory_config=memory_config,
    # command_config is optional and not needed for this specific demo
)

# 6. Define a sample string generator simulating LLM output
def sample_llm_output_generator() -> Iterator[str]:
    yield "This is some initial plain text. "
    yield "Now, here comes a tool call: "
    yield "<execute_command>"
    yield "<command>ls -l</command>"
    yield "<requires_approval>false</requires_approval>"
    yield "</execute_command>"
    yield " And some more plain text afterwards. "
    yield "Let's try another tool: "
    yield "<read_file><path>./some_file.txt</path></read_file>"
    yield " Followed by final text."
    yield "<write_to_file><path>output.log</path><content>Log entry.</content></write_to_file>"


# 7. Use the stream_and_parse_llm_response method
logger.info("Starting to parse LLM stream...")
parsed_items: Generator[Union[BaseTool, PlainTextOutput], None, None] = agentic_editor.stream_and_parse_llm_response(sample_llm_output_generator())

# 8. Iterate and process the parsed items
for item in parsed_items:
    if isinstance(item, PlainTextOutput):
        logger.info(f"Received Plain Text: '{item.text}'")
    elif isinstance(item, ExecuteCommandTool):
        logger.info(f"Received ExecuteCommandTool: command='{item.command}', requires_approval={item.requires_approval}")
    elif isinstance(item, ReadFileTool):
        logger.info(f"Received ReadFileTool: path='{item.path}'")
    elif isinstance(item, WriteToFileTool):
         logger.info(f"Received WriteToFileTool: path='{item.path}', content='{item.content}'")
    elif isinstance(item, BaseTool):
        logger.info(f"Received a BaseTool subclass: {type(item).__name__} - {item.model_dump()}")
    else:
        logger.warning(f"Received unexpected item type: {type(item)}")

logger.info("Finished parsing LLM stream.")