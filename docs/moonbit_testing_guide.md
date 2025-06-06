
# MoonBit 语言测试指南

## 单元测试实现

MoonBit的单元测试主要通过`test`代码块和断言库实现：

### 基础断言测试示例
```rust
fn add(x: Int, y: Int) -> Int { x + y }

test {
  @assertion.assert_eq(add(1, 2), 3)?
}
```
执行命令：`moon test`

### 使用inspect函数简化测试
```rust
test {
  inspect(add(1, 2))?
}
```
执行更新命令：`moon test -u`后会自动更新为：
```rust
test {
  inspect(add(1, 2), ~content="3")?
}
```

## 集成测试机制

MoonBit支持多文件联合测试：
- 常规测试文件（_test.mbt）
- 文档测试文件（*.mbt.md）
执行命令：`moon test`

## 文档内联测试示例

在Markdown中嵌入测试：
````markdown
```mbt example
fn fib(10) should return 55:
  test {
    @assertion.assert_eq(fib(10), 55)?
  }
```
````

## 复杂测试场景示例
```rust
test {
  [8,9,10].map(fib) |> inspect
}
```
执行更新后会生成：
```rust
test {
  [8,9,10].map(fib) |> inspect(~content="[21, 34, 55]")
}
```

## 关键测试命令
- `moon test`：执行所有测试
- `moon test -u`：更新测试期望值
