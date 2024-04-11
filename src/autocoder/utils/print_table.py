import tabulate
from autocoder.db.store import TokenCounter
from typing import List
def print_table(token_counters:List[TokenCounter]):    
    headers =  TokenCounter.model_fields.keys()
    table_data = [[getattr(counter, name) for name in headers] for counter in token_counters]    
    table_output = tabulate.tabulate(table_data, headers, tablefmt="grid")    
    print(table_output,flush=True)    