
from autocoder.common import AutoCoderArgs
from autocoder.dispacher.actions.copilot import ActionCopilot
from autocoder.dispacher.actions.action import ActionTSProject, ActionPyScriptProject, ActionPyProject, ActionSuffixProject
from autocoder.dispacher.actions.plugins.action_translate import ActionTranslate
from autocoder.dispacher.actions.plugins.action_regex_project import ActionRegexProject
from typing import Optional
import byzerllm
import re

class Dispacher():
    def __init__(self, args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None):
        self.args = args
        self.llm = llm 

    def dispach(self):
        args = self.args        
        actions = [ActionTranslate(args=args,llm=self.llm),
                    ActionTSProject(args=args,llm=self.llm),
                    ActionPyScriptProject(args=args,llm=self.llm),
                    ActionPyProject(args=args,llm=self.llm),
                    ActionCopilot(args=args,llm=self.llm),
                    ActionRegexProject(args=args,llm=self.llm),
                    ActionSuffixProject(args=args,llm=self.llm)
                    ]
        for action in actions:
            if action.run():
                return                
        
    