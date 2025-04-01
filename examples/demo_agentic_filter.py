import sys
import os
import json
import pkg_resources
from tokenizers import Tokenizer
import byzerllm

# Ensure the 'src' directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from autocoder.agent.agentic_filter import AgenticFilter #, AgenticFilterRequest - Not used by analyze
from autocoder.command_parser import AutoCommandRequest # analyze method uses this

# --- Tokenizer Setup (similar to test_context_prune_v2.py) ---
try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    if os.path.exists(tokenizer_path):
        VariableHolder.TOKENIZER_PATH = tokenizer_path
        VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
        print(f"Tokenizer loaded from: {tokenizer_path}")
    else:
        print(f"Tokenizer file not found at: {tokenizer_path}")
        VariableHolder.TOKENIZER_MODEL = None
except Exception as e:
    print(f"Failed to load tokenizer: {e}")
    tokenizer_path = None
    VariableHolder.TOKENIZER_MODEL = None
# --- End Tokenizer Setup ---


def main():
    # --- Args Setup (similar to test_context_prune_v2.py) ---
    args = AutoCoderArgs(
        source_dir=project_root, # Use project root as source_dir for context
        # Pointing to project root allows tools like get_project_structure to work
        # Adjust if your example needs a more specific sub-directory
        query="Find the add function in calculator.py and tell me which files reference it.", # Example query
        llm_model="gpt4o_mini", # Specify the model you want to use
        enable_auto_command=True, # AgenticFilter runs the auto command loop
        auto_command_max_iterations=5, # Limit iterations for the example
        # Add other necessary args if needed, e.g., API keys/bases if not using defaults
        # qianwen_api_key="your_api_key",
        # qianwen_base_url="your_base_url",
    )
    print(f"Using AutoCoderArgs: {args}")
    # --- End Args Setup ---

    # --- LLM Setup (similar to test_context_prune_v2.py) ---
    try:
        # Make sure BYZER_LLM_MODEL, BYZER_LLM_API_KEY etc are set in your environment
        # or configure the model directly if needed.
        # Example direct config:
        # llm = byzerllm.ByzerLLM()
        # llm.setup_template(model=args.llm_model, template="auto")
        # llm.setup_default_model_name(args.llm_model)
        # llm.setup_max_output_tokens(model=args.llm_model, max_output_tokens=args.model_max_output_tokens)
        # llm.setup_max_input_tokens(model=args.llm_model, max_input_tokens=args.model_max_input_tokens)
        # Or use the utility function:
        llm = get_single_llm(args=args)

        if llm is None:
             raise ValueError("Failed to initialize LLM. Check configuration and environment variables.")
        print(f"LLM Initialized: {llm.default_model_name}")

    except Exception as e:
        print(f"Error initializing LLM: {e}")
        print("Please ensure your LLM environment variables (e.g., BYZER_LLM_MODEL, BYZER_LLM_API_KEY) are set correctly or configure the model directly.")
        return
    # --- End LLM Setup ---

    # --- AgenticFilter Usage ---
    # AgenticFilter's analyze method runs an interactive loop with the LLM.
    # The LLM uses tools (like read_files, get_project_map) based on the query.
    # The final result identifying files usually comes from the 'response_user' tool call triggered by the LLM.

    print("\n--- Initializing AgenticFilter ---")
    # Start with an empty conversation history
    conversation_history = []
    agentic_filter = AgenticFilter(llm=llm, conversation_history=conversation_history, args=args)

    print(f"\n--- Running AgenticFilter Analysis for Query: '{args.query}' ---")
    # Create the request for the analyze method
    request = AutoCommandRequest(user_input=args.query)

    try:
        # The analyze method will internally use the LLM and tools to process the query.
        # It involves multiple LLM calls and tool executions.
        # The return value is the *last* AutoCommandResponse from the internal loop.
        # If the LLM successfully identifies the files and calls 'response_user',
        # that final response might be captured here, but it depends on the LLM's execution path.
        final_response = agentic_filter.analyze(request)

        print("\n--- AgenticFilter Analysis Complete ---")
        print("Final response from the analysis loop:")
        if final_response:
             # Pretty print the Pydantic model
            print(final_response.model_dump_json(indent=2))
             # You might need to inspect final_response.suggestions to see the last command,
             # which *should* ideally be 'response_user' with the file list if the process worked as intended.
            if final_response.suggestions and final_response.suggestions[0].command == "response_user":
                 print("\nSuccessfully identified files (check 'response_user' parameters above).")
            else:
                 print("\nAnalysis finished, but the final step might not have been 'response_user'. Check the suggestions.")

        else:
             print("Analysis did not return a final response object.")

    except Exception as e:
        print(f"\n--- Error during AgenticFilter analysis ---")
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- Example Finished ---")

if __name__ == "__main__":
    main()