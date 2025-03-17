# 036-AutoCoder_Coding_Prompt_Practice_1

In AutoCoder programming, there are two main stages:

1. Searching for files based on your requirements.
2. Using these files as context, combining them with the requirements, generating code, and merging it into the source files.

Today, we will focus on how to help the large model find your files and how to describe your requirements to achieve the best generation results.

## How to Help AutoCoder Find the Required Code Files

The first stage requires us to be able to find at least:

1. The files to be modified.
2. Other files that we need to depend on to make these modifications.

At this point, we have some tricks when writing requirements. Here is an actual example from AutoCoder:

```yaml
include_file: 
   - ./common/diff.yml

query: |   
   In the files starting with code_auto_generate, we need to check if llm has a code_model value. Refer to the way vl_model is checked in rest.py. If code_model exists, we need to use code_model instead of the model's llm for processing.
   
```

This is actually a way I am quite proud of. In just a few lines of text, we provide three pieces of information:

1. Which files need to be modified.
2. What is the modification logic.
3. What is a specific modification example.

Generally speaking, in the actual usage process, 1 must be mentioned. 3 in 2,3 is optional. If 2 is detailed enough, then 3 is not needed. If your modification is reversible, it is best to inform AutoCoder of the logic you have written.

From this example, we can see the efficiency of AutoCoder. We only need to describe the three points above, and all code modifications can be completed automatically and accurately without having to open a code file ourselves.

### Which Files Need to Be Modified

Here we use several techniques:

1. Explicitly tell AutoCoder the names of the files we need to modify, which in normal circumstances AutoCoder can find these files, which should be `code_auto_generate.py`, `code_auto_generate_diff.py`, and `code_auto_generate_strict_diff.py`.
2. You can be more precise by mentioning parts of the file path, such as `common/__init__.py`.
3. You can locate by function name and then use some code to locate. Function names can help you quickly find files, and auxiliary code can help you control the scope of modifications more clearly. This is particularly useful for frontend work, for example, if I want to add an input box behind that form input, I can precisely add a new input box.

In addition, you can specifically mention a file and explicitly state that all files it depends on should be found (whether they can be found in the end depends on the intelligence level of the large model).
However, you may still encounter difficulties at the end, such as AutoCoder not understanding what you mean. In this case, you can explicitly write the path or specify the file path through the `urls` parameter to ensure that the file is referenced.

### How Should You Describe Your Requirements (Modification Logic)

Modification logic is generally expressed in three ways:

1. Provide a relatively general modification description, but the specific implementation details can be referenced from previous code.
2. Provide detailed modification logic, step by step instructions.
3. Provide a goal and then briefly describe it, allowing AutoCoder to implement it on its own.

In addition, for the second case, if you cannot explain it clearly at once, you can iterate in multiple steps, making small changes each time, and ultimately complete the final business logic implementation through multiple iterations. The example I provided earlier is a classic example of the first solution, telling you the logic and providing a reference example, and the large model accurately completed the requirement.

For the second case, here is another actual example:

```yaml
enable_rag_search: | 
   byzerllm uses the openai_tts model in Python code.

query: | 
   We need to implement a new class called PlayStreamAudioFromText in audio.py,
   which has a method named run,
   the input of this method is a string generator, and inside the method, the text will be converted to speech and played.
   
   The specific logic is:
   1. PlayStreamAudioFromText maintains a queue and a thread pool.
   2. At runtime, it reads text from the generator and puts it into the queue.
   3. It takes text from the queue, splits the sentences based on Chinese and English periods or line breaks, and calls the openai_tts model to convert the text to speech, saving it in the /tmp/wavs directory.
```The audio files are named according to the naming rule 001.wav, 002.wav, 003.wav... and are saved in a directory.
3. Use a separate thread to play the audio files. Play the next audio file only after finishing the current one, until all audio files are played. 

Here we have written the business logic in detail so that AutoCoder can complete this requirement in a controlled manner, instead of improvising. In addition, we have used the RAG method to recall some example code from the document, avoiding the need to manually add these example codes when writing queries.

In the third scenario, let's look at an example:

```yaml
query: |
  Add a revert subcommand in auto_coder.py.
  The command should be as follows:
  
  ```shell
  auto_coder revert --file {args.file}
  ```

  Specific logic:

  0. Use the Python git package instead of shell commands, and place the revert function in git_utils.py.
  1. Find the git log where the git message is equal to {args.file} and find the corresponding commit id.
  2. Use git revert {commit_id} to revert the corresponding commit.
  3. If the revert fails, print a warning message.
```

In this example, we first tell you what effect we want to achieve, then we add some restrictions or logic to help balance between control and the freedom of a large model.

## Conclusion

In the process of using AutoCoder, the basic approach is as described above. Inform which files are needed, describe your modification requirements based on the actual situation. Since it is based on an existing project, there is no need to describe the technologies used in detail. Just describe our requirements. 

You can also look at the examples in the AutoCoder actions directory, where there are actual examples that can help you better understand how to write requirements.