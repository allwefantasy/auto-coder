"""
Rule Name: Token Counting for Third-Party Modules

Description:
This rule explains how external modules or projects can utilize the token counting functionality provided by the `autocoder` library, specifically using the `TokenCounter` class.

Usage Guidance:
To count tokens in your text using the `autocoder` library, follow these steps:

1. Import the `TokenCounter` class:
   ```python
   from autocoder.rag.token_counter import TokenCounter
   ```

2. Obtain the path to the tokenizer model file. This path is typically configured within the `autocoder` setup or passed via arguments (e.g., `args.tokenizer_path`). Ensure this path points to a valid tokenizer file compatible with the `tokenizers` library (e.g., `tokenizer.json`).

3. Instantiate the `TokenCounter` class with the tokenizer path:
   ```python
   # Replace 'path/to/your/tokenizer.json' with the actual path
   tokenizer_path = 'path/to/your/tokenizer.json'
   token_counter = TokenCounter(tokenizer_path=tokenizer_path)
   ```
   *Note: `TokenCounter` utilizes multiprocessing for potentially faster counting on multi-core systems.*

4. Call the `count_tokens` method on the instance with the text you want to count:
   ```python
   text_to_count = "This is the text whose tokens need to be counted."
   token_count = token_counter.count_tokens(text_to_count)

   if token_count != -1:
       print(f"The text contains approximately {token_count} tokens.")
   else:
       print("Error occurred during token counting.")
   ```

Considerations:
- Initialization Overhead: Creating a `TokenCounter` instance involves setting up a multiprocessing pool, which has some overhead. For frequent counting, reuse the same instance.
- Tokenizer Compatibility: Ensure the provided `tokenizer_path` leads to a tokenizer file compatible with the `tokenizers` library and appropriate for the model you are interacting with, as tokenization strategies differ between models.
- Error Handling: The `count_tokens` method returns `-1` in case of an error during the counting process. Implement appropriate error handling.
- Alternative (Internal Use): The `autocoder.rag.token_counter` module also contains a top-level `count_tokens` function. However, this function relies on a globally initialized `VariableHolder.TOKENIZER_MODEL`, making the `TokenCounter` class a more encapsulated and generally recommended approach for external use.
"""

# This file is a rule description and does not contain executable code by itself.
# Refer to the description above for usage examples.
pass