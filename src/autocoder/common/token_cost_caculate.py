from typing import Dict, Any, Optional, Tuple, List
import time
from loguru import logger
import byzerllm
from byzerllm import MetaHolder
from autocoder.common.types import CodeGenerateResult
from autocoder.events.event_types import EventMetadata
from autocoder.utils import llms
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from pydantic import BaseModel, Field
from autocoder.common import AutoCoderArgs
from autocoder.common.printer import Printer


class TokenUsageStats(BaseModel):
    """Token使用统计数据模型"""
    input_tokens: int = Field(default=0, description="输入的token数量")
    output_tokens: int = Field(default=0, description="输出的token数量")
    input_cost: float = Field(default=0.0, description="输入token的成本")
    output_cost: float = Field(default=0.0, description="输出token的成本")

    @property
    def total_tokens(self) -> int:
        """总token数"""
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        """总成本"""
        return self.input_cost + self.output_cost


class TokenCostCalculator:
    """
    Token计费计算器 - 提供获取模型信息、计算token成本和记录token统计信息的公共功能
    """

    def __init__(self, logger_name: str = "TokenCostCalculator",args:Optional[AutoCoderArgs]=None):
        """
        初始化Token计费计算器

        Args:
            logger_name: logger名称，默认为TokenCostCalculator            
        """
        self.logger = logger.bind(name=logger_name)
        self.args = args
        self.printer = Printer()

    def get_model_info(self, llm: byzerllm.ByzerLLM, product_mode: str = "lite") -> Tuple[str, Dict[str, Dict[str, float]]]:
        """
        获取模型名称和价格信息

        Args:
            llm: ByzerLLM实例

        Returns:
            Tuple[str, Dict]: 模型名称字符串和价格信息字典
        """
        # 获取模型名称列表
        model_names = llms.get_llm_names(llm)
        model_name = ",".join(model_names)

        # 获取模型价格信息
        model_info_map = {}
        for name in model_names:
            info = llms.get_model_info(name, product_mode)
            if info:
                model_info_map[name] = {
                    "input_price": info.get("input_price", 0.0),
                    "output_price": info.get("output_price", 0.0)
                }

        return model_name, model_info_map

    def calculate_token_costs_by_generate(self, generate: CodeGenerateResult) -> TokenUsageStats:        
        stats = TokenUsageStats()
        stats.input_tokens = generate.metadata.get("input_tokens_count", 0)
        stats.output_tokens = generate.metadata.get(
            "generated_tokens_count", 0)
        stats.input_cost = generate.metadata.get("input_tokens_cost", 0)
        stats.output_cost = generate.metadata.get("generated_tokens_cost", 0)
        return stats

    def calculate_token_costs(self, meta_holder: MetaHolder,
                              model_info_map: Dict[str, Dict[str, float]]) -> TokenUsageStats:
        """
        计算token统计和成本

        Args:
            meta_holder: MetaHolder实例
            model_info_map: 模型价格信息字典

        Returns:
            TokenUsageStats: Token使用统计数据对象
        """
        stats = TokenUsageStats()

        if meta_holder.get_meta():
            meta_dict = meta_holder.get_meta()
            stats.input_tokens = meta_dict.get("input_tokens_count", 0)
            stats.output_tokens = meta_dict.get("generated_tokens_count", 0)

            for name, info in model_info_map.items():
                stats.input_cost += (stats.input_tokens *
                                     info.get("input_price", 0.0)) / 1000000
                stats.output_cost += (stats.output_tokens *
                                      info.get("output_price", 0.0)) / 1000000

        return stats
    
    def log_event(self,
                  model_name: str,
                  operation_name: str,
                  start_time: float,
                  end_time: float,
                  stats: TokenUsageStats,
                  event_file: Optional[str] = None):
        elapsed_time = end_time - start_time

        # 计算token生成速度（每秒生成的token数）
        speed = stats.output_tokens / elapsed_time if elapsed_time > 0 else 0

        # 记录日志
        self.logger.info(f"{operation_name} Stats - Model: {model_name}, "
                    f"Input Tokens: {stats.input_tokens}, "
                    f"Output Tokens: {stats.output_tokens}, "
                    f"Total Tokens: {stats.total_tokens}, "
                    f"Time: {elapsed_time:.2f}s, "
                    f"Speed: {speed:.2f}tokens/s, "
                    f"Total Cost: ${stats.total_cost:.6f}")
        
        get_event_manager(event_file).write_result(
            EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                model_name=model_name,
                elapsed_time=elapsed_time,
                first_token_time=0,  # 不跟踪首个token时间
                input_tokens=stats.input_tokens,
                output_tokens=stats.output_tokens,
                input_cost=stats.input_cost,
                output_cost=stats.output_cost,
                speed=speed
            ).to_dict()))
                

    def log_event_by_generate(self,
                  model_name: str,
                  operation_name: str,
                  start_time: float,
                  end_time: float,
                  stats: TokenUsageStats,
                  event_file: Optional[str] = None,
                  sampling_count: int = 1):
        """
        记录token统计信息到日志和事件系统

        Args:
            model_name: 模型名称
            operation_name: 操作名称，用于日志记录
            start_time: 开始时间
            end_time: 结束时间
            stats: Token使用统计数据
            event_file: 事件文件路径，如果提供则写入事件
        """
        elapsed_time = end_time - start_time

        # 计算token生成速度（每秒生成的token数）
        speed = stats.output_tokens / elapsed_time if elapsed_time > 0 else 0

        self.printer.print_in_terminal(
            operation_name,
            duration=elapsed_time,
            input_tokens=stats.input_tokens,
            output_tokens=stats.output_tokens,
            input_cost=stats.input_cost,
            output_cost=stats.output_cost,
            speed=round(speed, 2),
            model_names=model_name,
            sampling_count=sampling_count
        )

        # 记录事件（如果提供了event_file）
        get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                    model_name=model_name,
                    elapsed_time=elapsed_time,
                    input_tokens=stats.input_tokens,
                    output_tokens=stats.output_tokens,
                    input_cost=stats.input_cost,
                    output_cost=stats.output_cost,
                    speed=round(speed, 2)
                )).to_dict(), metadata=EventMetadata(
                    action_file=self.args.file
                ).to_dict())

    
    def track_token_usage_by_generate(self,
                                      llm: byzerllm.ByzerLLM,
                                      generate: CodeGenerateResult,
                                      operation_name: str,
                                      start_time: float,
                                      end_time: float,
                                      product_mode: Optional[str] = None,
                                      event_file: Optional[str] = None) -> TokenUsageStats:        
        model_name, model_info_map = self.get_model_info(llm, product_mode)
        stats = self.calculate_token_costs_by_generate(generate)

        self.log_event_by_generate(
            model_name=model_name,
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            stats=stats,
            event_file=event_file,
            sampling_count=len(generate.contents)
        )

    def track_token_usage(self,
                          llm: byzerllm.ByzerLLM,
                          meta_holder: MetaHolder,
                          operation_name: str,
                          start_time: float,
                          end_time: float,
                          product_mode: Optional[str] = None,
                          event_file: Optional[str] = None) -> TokenUsageStats:
        """
        跟踪token使用情况的便捷方法，整合了获取模型信息、计算成本和记录统计的功能

        Args:
            llm: ByzerLLM实例
            meta_holder: MetaHolder实例
            operation_name: 操作名称
            start_time: 开始时间
            end_time: 结束时间
            product_mode: 产品模式，如果不提供则使用实例的product_mode
            event_file: 事件文件路径

        Returns:
            TokenUsageStats: Token使用统计数据对象
        """
        # 使用传入的product_mode或实例的product_mode
        actual_product_mode = product_mode

        # 获取模型信息
        model_name, model_info_map = self.get_model_info(
            llm, actual_product_mode)

        # 计算token统计和成本
        stats = self.calculate_token_costs(meta_holder, model_info_map)

        # 记录事件
        self.log_event(
            model_name=model_name,
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            stats=stats,
            event_file=event_file
        )

        return stats
