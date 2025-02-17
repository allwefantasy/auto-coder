from typing import Dict, Any
from autocoder.utils import llms as llm_utils
from autocoder.common.printer import Printer

class CostCalculator:
    def __init__(self, product_mode: str):
        self.product_mode = product_mode
        self.printer = Printer()
        
    def calculate_cost(self, model_names: list, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """计算LLM调用成本
        
        Args:
            model_names: 模型名称列表
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            包含成本统计信息的字典
        """
        model_info_map = self._get_model_info_map(model_names)
        
        total_input_cost = 0.0
        total_output_cost = 0.0
        
        for model_name in model_names:
            info = model_info_map.get(model_name, {})
            total_input_cost += (input_tokens * info.get("input_price", 0.0)) / 1000000
            total_output_cost += (output_tokens * info.get("output_price", 0.0)) / 1000000
            
        return {
            "input_tokens_count": input_tokens,
            "generated_tokens_count": output_tokens,
            "input_cost": round(total_input_cost, 4),
            "output_cost": round(total_output_cost, 4)
        }
        
    def _get_model_info_map(self, model_names: list) -> Dict[str, Dict]:
        """获取模型价格信息映射"""
        model_info_map = {}
        for name in model_names:
            info = llm_utils.get_model_info(name, self.product_mode)
            if info:
                model_info_map[name] = {
                    "input_cost": info.get("input_price", 0.0),
                    "output_cost": info.get("output_price", 0.0)
                }
        return model_info_map
        
    def print_cost_statistics(self, model_name: str, elapsed_time: float, first_token_time: float,
                            input_tokens: int, output_tokens: int, input_cost: float, output_cost: float):
        """打印成本统计信息"""
        speed = output_tokens / elapsed_time
        self.printer.print_in_terminal(
            "stream_out_stats",
            model_name=model_name,
            elapsed_time=f"{elapsed_time:.2f}",
            first_token_time=f"{first_token_time:.2f}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=round(input_cost, 4),
            output_cost=round(output_cost, 4),
            speed=round(speed, 2)
        )