from autocoder.common import AutoCoderArgs
from autocoder.dispacher.actions.copilot import ActionCopilot
from autocoder.dispacher.actions.action import (
    ActionTSProject,
    ActionPyProject,
    ActionSuffixProject,
)
from autocoder.dispacher.actions.plugins.action_regex_project import ActionRegexProject
from typing import Optional
import byzerllm
# from autocoder.common.conversations.get_conversation_manager import (
#     get_conversation_manager,
#     get_conversation_manager_config,
#     reset_conversation_manager
# )


class Dispacher:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None):
        self.args = args
        self.llm = llm

    def dispach(self):
        # manager = get_conversation_manager()
        # if not manager.get_current_conversation():
        #     manager.create_conversation(name="New Conversation", description="New Conversation")
        #     manager.set_current_conversation(manager.get_current_conversation_id())

        args = self.args
        actions = [            
            ActionTSProject(args=args, llm=self.llm),
            ActionPyProject(args=args, llm=self.llm),
            ActionCopilot(args=args, llm=self.llm),
            ActionRegexProject(args=args, llm=self.llm),
            ActionSuffixProject(args=args, llm=self.llm),
        ]
        for action in actions:
            if action.run():
                return
