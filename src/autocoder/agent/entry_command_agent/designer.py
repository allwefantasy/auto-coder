






from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    DefaultValue,
    RequestOption,
)


class DesignerAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args

    def run(self):
        """执行 designer 命令的主要逻辑"""
        from autocoder.agent.designer import SVGDesigner, SDDesigner, LogoDesigner

        if self.args.agent_designer_mode == "svg":
            designer = SVGDesigner(self.args, self.llm)
            designer.run(self.args.query)
            print("Successfully generated image in output.png")
        elif self.args.agent_designer_mode == "sd":
            designer = SDDesigner(self.args, self.llm)
            designer.run(self.args.query)
            print("Successfully generated image in output.jpg")
        elif self.args.agent_designer_mode.startswith("logo"):
            designer = LogoDesigner(self.args, self.llm)
            designer.run(self.args.query)
            print("Successfully generated image in output.png")
        
        if self.args.request_id:
            request_queue.add_request(
                self.args.request_id,
                RequestValue(
                    value=DefaultValue(
                        value="Successfully generated image"),
                    status=RequestOption.COMPLETED,
                ),
            )






