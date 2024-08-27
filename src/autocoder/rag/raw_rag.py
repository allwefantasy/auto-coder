import os
import byzerllm
from byzerllm.apps.byzer_storage.simple_api import (
    ByzerStorage,
    DataType,
    FieldOption,
    SortOption,
)


def chunk_text(text, max_length=1000):
    chunks = []
    current_chunk = []
    current_length = 0

    for line in text.split("\n"):
        if current_length + len(line) > max_length and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(line)
        current_length += len(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


@byzerllm.prompt()
def process_query(context: str, query: str) -> str:
    """
    Based on the following context, please answer the query:

    Context:
    {{ context }}

    Query: {{ query }}

    Please provide a concise and accurate answer based on the given context.
    """


class RawRAG:
    def __init__(
        self, llm_model="deepseek_chat", emb_model="emb", storage_name="byzerai_store"
    ):
        self.storage = ByzerStorage(
            storage_name, "rag_database", "rag_table", emb_model=emb_model
        )
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_default_model_name(llm_model)

        # Create schema if not exists
        _ = (
            self.storage.schema_builder()
            .add_field("_id", DataType.STRING)
            .add_field("content", DataType.STRING, [FieldOption.ANALYZE])
            .add_field("raw_content", DataType.STRING, [FieldOption.NO_INDEX])
            .add_array_field("vector", DataType.FLOAT)
            .execute()
        )

    def build(self, directory):
        for filename in os.listdir(directory):
            if filename.endswith(".md"):
                with open(os.path.join(directory, filename), "r") as file:
                    content = file.read()
                    chunks = chunk_text(content)

                    for i, chunk in enumerate(chunks):
                        item = {
                            "_id": f"{filename}_{i}",
                            "content": chunk,
                            "raw_content": chunk,
                            "vector": chunk,
                        }
                        self.storage.write_builder().add_items(
                            [item], vector_fields=["vector"], search_fields=["content"]
                        ).execute()

        self.storage.commit()

    def query(self, query_text):
        query = self.storage.query_builder()
        query.set_vector_query(query_text, fields=["vector"])
        results = query.execute()

        if results:
            context = results[0]["raw_content"]
            response = process_query.with_llm(self.llm).run(
                context=context, query=query_text
            )
            return response
        else:
            return "Sorry, I couldn't find relevant information to answer your query."
