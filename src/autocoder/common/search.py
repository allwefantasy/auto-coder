from typing import List,Optional
import httpx
import json
from loguru import logger
from pydantic import BaseModel,Field
import requests
from enum import Enum
import byzerllm
from langchain_core.prompts import PromptTemplate
from autocoder.utils.rest import HttpDoc

# Search engine related. You don't really need to change this.
BING_SEARCH_V7_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
BING_MKT = "en-US"
GOOGLE_SEARCH_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
SERPER_SEARCH_ENDPOINT = "https://google.serper.dev/search"
SEARCHAPI_SEARCH_ENDPOINT = "https://www.searchapi.io/api/v1/search"

# Specify the number of references from the search engine you want to use.
# 8 is usually a good number.
REFERENCE_COUNT = 8

# Specify the default timeout for the search engine. If the search engine
# does not respond within this time, we will return an error.
DEFAULT_SEARCH_ENGINE_TIMEOUT = 5

class DocWithRelevance(BaseModel):
    docs:List[int] = Field(default_factory=list,description="The index list of documents")
    relevance: List[float] = Field(default_factory=list,description="The relevance score of the documents")

def llm_rerank(llm:byzerllm.ByzerLLM,query:str,docs:List[str],top_k:int=1):
    DEFAULT_CHOICE_SELECT_PROMPT_TMPL = (
        "A list of documents is shown below. Each document has a number next to it along "
        "with a summary of the document. A question is also provided. \n"
        "Respond with the numbers of the documents "
        "you should consult to answer the question, in order of relevance, as well \n"
        "as the relevance score. The relevance score is a number from 1-10 based on "
        "how relevant you think the document is to the question.\n"
        "Do not include any documents that are not relevant to the question. \n"
        "Example format: \n"
        "Document 1:\n<summary of document 1>\n\n"
        "Document 2:\n<summary of document 2>\n\n"
        "...\n\n"
        "Document 10:\n<summary of document 10>\n\n"
        "Question: <question>\n"
        "Answer:\n"
        "Doc: 9, Relevance: 7\n"
        "Doc: 3, Relevance: 4\n"
        "Doc: 7, Relevance: 3\n\n"
        "Let's try this now: \n\n"
        "{context_str}\n"
        "Question: {query_str}\n"
        "Answer:\n"
    )
    DEFAULT_CHOICE_SELECT_PROMPT = PromptTemplate.from_template(
        DEFAULT_CHOICE_SELECT_PROMPT_TMPL
    )

    context_str = ""
    for i,metric in enumerate(docs):
        context_str += f"Document {i+1}:\n {docs[i]}\n\n"

    query_str = query

    r = llm.chat_oai(conversations=[{
        "role": "user",
        "content": DEFAULT_CHOICE_SELECT_PROMPT.format(context_str=context_str,query_str=query_str)
    }])
    
    r = llm.chat_oai(conversations=[{
        "role": "user",
        "content": r[0].output
    }],response_class=DocWithRelevance,enable_default_sys_message=True)
    
    doc_with_relevents:DocWithRelevance = r[0].value 

    if doc_with_relevents is None:
        raise ValueError("LLM Ranker failed, please try again.")
    # target_values = [] 

    # print(f"docs:{docs} doc_with_relevents {doc_with_relevents}",flush=True)

    # for choice in doc_with_relevents.docs[0:top_k]:
    #     target_values.append(docs[int(choice)-1]) 
    return (doc_with_relevents.docs,doc_with_relevents.relevance)

class SearchEngine(Enum):
    BING = "bing"
    GOOGLE = "google"
    SERPER = "serper"
    SEARCHAPI = "searchapi"

class SearchContext(BaseModel):
    name: str
    url: str
    snippet: str

class RelatedQuestion(BaseModel):
    related_question: List[str]    

def search_with_bing(query: str, subscription_key: str):
        """
        Search with bing and return the contexts.
        """
        params = {"q": query, "mkt": BING_MKT}        
        response = requests.get(
            BING_SEARCH_V7_ENDPOINT,
            headers={"Ocp-Apim-Subscription-Key": subscription_key},
            params=params,
            timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT,
        )
        if not response.ok:
            logger.error(f"{response.status_code} {response.text}")
            raise Exception(response.status_code, "Search engine error.")
        json_content = response.json()
        try:
            contexts = json_content["webPages"]["value"][:REFERENCE_COUNT]
        except KeyError:
            logger.error(f"Error encountered: {json_content}")
            return []
        return contexts


def search_with_google(query: str, subscription_key: str, cx: str):
    """
    Search with google and return the contexts.
    """
    params = {
        "key": subscription_key,
        "cx": cx,
        "q": query,
        "num": REFERENCE_COUNT,
    }
    response = requests.get(
        GOOGLE_SEARCH_ENDPOINT, params=params, timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT
    )
    if not response.ok:
        logger.error(f"{response.status_code} {response.text}")
        raise Exception(response.status_code, "Search engine error.")
    json_content = response.json()
    try:
        contexts = json_content["items"][:REFERENCE_COUNT]
    except KeyError:
        logger.error(f"Error encountered: {json_content}")
        return []
    return contexts


def search_with_serper(query: str, subscription_key: str):
    """
    Search with serper and return the contexts.
    """
    payload = json.dumps({
        "q": query,
        "num": (
            REFERENCE_COUNT
            if REFERENCE_COUNT % 10 == 0
            else (REFERENCE_COUNT // 10 + 1) * 10
        ),
    })
    headers = {"X-API-KEY": subscription_key, "Content-Type": "application/json"}
    logger.info(
        f"{payload} {headers} {subscription_key} {query} {SERPER_SEARCH_ENDPOINT}"
    )
    response = requests.post(
        SERPER_SEARCH_ENDPOINT,
        headers=headers,
        data=payload,
        timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT,
    )
    if not response.ok:
        logger.error(f"{response.status_code} {response.text}")
        raise Exception(response.status_code, "Search engine error.")
    json_content = response.json()
    try:
        # convert to the same format as bing/google
        contexts = []
        if json_content.get("knowledgeGraph"):
            url = json_content["knowledgeGraph"].get("descriptionUrl") or json_content["knowledgeGraph"].get("website")
            snippet = json_content["knowledgeGraph"].get("description")
            if url and snippet:
                contexts.append({
                    "name": json_content["knowledgeGraph"].get("title",""),
                    "url": url,
                    "snippet": snippet
                })
        if json_content.get("answerBox"):
            url = json_content["answerBox"].get("url")
            snippet = json_content["answerBox"].get("snippet") or json_content["answerBox"].get("answer")
            if url and snippet:
                contexts.append({
                    "name": json_content["answerBox"].get("title",""),
                    "url": url,
                    "snippet": snippet
                })
        contexts += [
            {"name": c["title"], "url": c["link"], "snippet": c.get("snippet","")}
            for c in json_content["organic"]
        ]
        return contexts[:REFERENCE_COUNT]
    except KeyError:
        logger.error(f"Error encountered: {json_content}")
        return []

def search_with_searchapi(query: str, subscription_key: str):
    """
    Search with SearchApi.io and return the contexts.
    """
    payload = {
        "q": query,
        "engine": "google",
        "num": (
            REFERENCE_COUNT
            if REFERENCE_COUNT % 10 == 0
            else (REFERENCE_COUNT // 10 + 1) * 10
        ),
    }
    headers = {"Authorization": f"Bearer {subscription_key}", "Content-Type": "application/json"}
    logger.info(
        f"{payload} {headers} {subscription_key} {query} {SEARCHAPI_SEARCH_ENDPOINT}"
    )
    response = requests.get(
        SEARCHAPI_SEARCH_ENDPOINT,
        headers=headers,
        params=payload,
        timeout=30,
    )
    if not response.ok:
        logger.error(f"{response.status_code} {response.text}")
        raise Exception(response.status_code, "Search engine error.")
    json_content = response.json()
    try:
        # convert to the same format as bing/google
        contexts = []

        if json_content.get("answer_box"):
            if json_content["answer_box"].get("organic_result"):
                title = json_content["answer_box"].get("organic_result").get("title", "")
                url = json_content["answer_box"].get("organic_result").get("link", "")
            if json_content["answer_box"].get("type") == "population_graph":
                title = json_content["answer_box"].get("place", "")
                url = json_content["answer_box"].get("explore_more_link", "")

            title = json_content["answer_box"].get("title", "")
            url = json_content["answer_box"].get("link")
            snippet =  json_content["answer_box"].get("answer") or json_content["answer_box"].get("snippet")

            if url and snippet:
                contexts.append({
                    "name": title,
                    "url": url,
                    "snippet": snippet
                })

        if json_content.get("knowledge_graph"):
            if json_content["knowledge_graph"].get("source"):
                url = json_content["knowledge_graph"].get("source").get("link", "")

            url = json_content["knowledge_graph"].get("website", "")
            snippet = json_content["knowledge_graph"].get("description")

            if url and snippet:
                contexts.append({
                    "name": json_content["knowledge_graph"].get("title", ""),
                    "url": url,
                    "snippet": snippet
                })

        contexts += [
            {"name": c["title"], "url": c["link"], "snippet": c.get("snippet", "")}
            for c in json_content["organic_results"]
        ]
        
        if json_content.get("related_questions"):
            for question in json_content["related_questions"]:
                if question.get("source"):
                    url = question.get("source").get("link", "")
                else:
                    url = ""  
                    
                snippet = question.get("answer", "")

                if url and snippet:
                    contexts.append({
                        "name": question.get("question", ""),
                        "url": url,
                        "snippet": snippet
                    })

        return contexts[:REFERENCE_COUNT]
    except KeyError:
        logger.error(f"Error encountered: {json_content}")
        return []




class Search:
    def __init__(self, 
                 llm:byzerllm.ByzerLLM,
                 search_engine: SearchEngine, 
                 subscription_key: str, 
                 reference_count: int = 8, timeout: int = 5):
        self.llm = llm
        self.search_engine = search_engine
        self.subscription_key = subscription_key
        self.reference_count = reference_count
        self.timeout = timeout
        self.client = httpx.Client(timeout=self.timeout)
    
    
    @byzerllm.prompt(lambda self: self.llm, render="jinja2")
    def _llm_search(self, query: str,context:str) -> str:
        '''        
        You are a large language AI assistant built by Lepton AI. You are given a user question, and please write clean, concise and accurate answer to the question. You will be given a set of related contexts to the question, each starting with a reference number like [[citation:x]], where x is a number. Please use the context and cite the context at the end of each sentence if applicable.

        Your answer must be correct, accurate and written by an expert using an unbiased and professional tone. Please limit to 1024 tokens. Do not give any information that is not related to the question, and do not repeat. Say "information is missing on" followed by the related topic, if the given context do not provide sufficient information.

        Please cite the contexts with the reference numbers, in the format [citation:x]. If a sentence comes from multiple contexts, please list all applicable citations, like [citation:3][citation:5]. Other than code and specific names and citations, your answer must be written in the same language as the question.

        Here are the set of contexts:
        
        {{ context }}

        Remember, don't blindly repeat the contexts verbatim. And here is the user question: {{ query }}
        '''

    @byzerllm.prompt(lambda self: self.llm, render="jinja2")    
    def _related_questions(self,query:str, context:str)->RelatedQuestion:
        '''        
        You are a helpful assistant that helps the user to ask related questions, 
        based on user's original question and the related contexts. 
        Please identify worthwhile topics that can be follow-ups, and write questions no longer than 20 words each. 
        Please make sure that specifics, like events, names, locations, are included in follow up questions so they can be asked standalone. 
        For example, if the original question asks about "the Manhattan project", in the follow up question, do not just say "the project", 
        but use the full name "the Manhattan project". Your related questions must be in the same language as the original question.

        Here are the contexts of the question:

        {{ context }}

        Remember, based on the original question and related contexts, suggest three such further questions. 
        Do NOT repeat the original question. Each related question should be no longer than 20 words. 
        Here is the original question: {{ query }}        
        '''

    def get_the_most_related_context(self, query: str) -> Optional[SearchContext]:
        print(f"search {self.search_engine} for {query}...")
        contexts = self.search(query)
        if len(contexts) == 0:
            print(f"failed to find any context for the question: {query}")
            return None
        snippets = [c.snippet for c in contexts]
        print(f"reraking the search result by snippets...")        
        (indices,scores) = llm_rerank(self.llm,query,snippets)          
        if indices and scores[0]>7:
            return contexts[indices[0]-1]
        else:
            print(f"no context is found with relevance score > 7 for the question: {query}")
            return None
         

    def llm_related_questions(self, query: str, context: str) -> RelatedQuestion:
        contexts = self.search(query)
        context="\n\n".join(
                [f"[[citation:{i+1}]] {c['snippet']}" for i, c in enumerate(contexts)]
            )
        return self._related_questions(query,context)

    def llm_search(self, query: str) -> str:
        contexts = self.search(query)
        context="\n\n".join(
                [f"[[citation:{i+1}]] {c['snippet']}" for i, c in enumerate(contexts)]
            )
        return self._llm_search(query,context)

    def answer_with_the_most_related_context(self, query: str) -> str:        
        context = self.get_the_most_related_context(query)
        if context is None:
            print(f"failed to find the most related context for the question: {query}")
            return ""
        
        print(f"fetch {context.url} and answer the quesion ({query}) based on the full content...")        
        doc = HttpDoc(args = self.args,llm = self.llm,urls=[context.url])
        source_codes = doc.crawl_urls()            
        return self._llm_search(query,[SearchContext(name=source_code.module_name,url=context.url,snippet=source_code.source_code) for source_code in source_codes])    
        
    def search(self, query: str) -> List[SearchContext]:        
        if self.search_engine == SearchEngine.BING:
            contexts = search_with_bing(query, self.subscription_key)
        elif self.search_engine == SearchEngine.GOOGLE:
            contexts = search_with_google(query, self.subscription_key, self.cx)  
        elif self.search_engine == SearchEngine.SERPER:
            contexts = search_with_serper(query, self.subscription_key)
        elif self.search_engine == SearchEngine.SEARCHAPI:
            contexts = search_with_searchapi(query, self.subscription_key)
        else:
            raise ValueError(f"Unsupported search engine: {self.search_engine}")
            
        return [SearchContext(**context) for context in contexts] 



