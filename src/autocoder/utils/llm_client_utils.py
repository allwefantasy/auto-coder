from byzerllm.utils.client import EventCallbackResult,EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from typing import List,Dict,Any


def token_counter_intercept_callback(event_name: EventName, event_data: Any) -> EventCallbackResult:
    if event_name == EventName.TOKEN_COUNTER:
        tokens = event_data["tokens"]
        token_counter = {}
        for token in tokens:
            if token in token_counter:
                token_counter[token] += 1
            else:
                token_counter[token] = 1
        sorted_token_counter = sorted(token_counter.items(), key=lambda x: x[1], reverse=True)
        token_counter_str = "\n".join([f"{token}: {count}" for token, count in sorted_token_counter])
        print(token_counter_str)
    return EventCallbackResult.CONTINUE