# 模型价格管理指南

## 功能介绍
AutoCoder 提供完善的模型价格管理功能，支持通过命令行或API设置不同模型的输入/输出价格。这些价格信息将用于：
1. 代码生成成本预估
2. 用量监控告警
3. 资源优化建议
4. 账单生成

## 核心命令

### 设置输入价格
```bash
auto-coder models --update-input-price <模型名称> <价格>
```
- 价格单位：美元/百万tokens
- 示例：`auto-coder models --update-input-price gpt-4 3.0`

### 设置输出价格 
```bash
auto-coder models --update-output-price <模型名称> <价格>
```
- 价格单位：美元/百万tokens
- 示例：`auto-coder models --update-output-price gpt-4 6.0`

## 价格设置规范
1. 价格精度支持到小数点后6位
2. 设置为0表示禁用该模型
3. 输入输出价格比例建议保持1:1.3~1.5
4. 价格变更实时生效，不会影响正在运行的任务

## 最佳实践
1. 定期同步官方价格变更
```bash
# 同步OpenAI最新价格
auto-coder models --update-input-price gpt-4 3.0 --update-output-price gpt-4 6.0
auto-coder models --update-input-price gpt-3.5 0.5 --update-output-price gpt-3.5 1.5
```

2. 企业私有模型定价
```bash
# 设置内部模型价格
auto-coder models --update-input-price internal-llm 0.001 --update-output-price internal-llm 0.002
```

3. 价格验证命令
```bash
# 查看当前所有模型价格
auto-coder models --list
```

## 常见问题

### Q: 如何确认价格已生效？
A: 使用查看命令验证：
```bash
auto-coder models --list | grep <模型名称>
```

### Q: 设置错误价格如何回滚？
A: 直接重新设置正确价格，系统会保留历史版本在models.json中

### Q: 为什么实际扣费与设置价格有差异？
A: 可能原因包括：
1. 模型供应商的实际计费策略变化
2. 流量折损系数未考虑（默认系数1.05）
3. 四舍入误差（系统精确到小数点后6位）

## 高级配置
在~/.auto-coder/config.yaml中可配置：
```yaml
price:
  currency: USD  # 支持USD/CNY/EUR
  tax_rate: 0.07 # 默认税率
  discount: 0.9  # 企业折扣
```