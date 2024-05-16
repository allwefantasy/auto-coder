# 027-AutoCoder_If I Just Want Good Results_What is the Best Combination

After exploring with at least 20 million tokens consumed, I have summarized the best model combination for assisted programming in AutoCoder:
1. Index building with DeepSeek/Haiku (corresponding to the index_model parameter)
2. Index querying/AutoCoder function driven by GPT3.5 (corresponding to the model parameter)
3. Code generation with Claude Opus/GPT-4o (with human_as_model set to true)
4. Knowledge base building with OpenAI Embedding (Small) (corresponding to the emb_model parameter)

In addition, because the token consumption for code generation is also significant, AutoCoder provides the unique human_as_model feature, allowing you to use the web version of the model for code generation, similar to a monthly subscription, to avoid billing for a large number of tokens.

If cost is not a consideration at all, the best combination would be:
1. Index building/Index querying/AutoCoder function driven by GPT-3.5
2. Code generation using Claude Opus (with human_as_model set to false, at this point it will generate code directly through the API without the need for manual copying and pasting in the web interface)
3. Knowledge base building with OpenAI Embedding (Big) (corresponding to the emb_model parameter)