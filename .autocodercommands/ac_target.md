# 需求验证脚本生成指南

当用户给定需求时，生成一个可验证需求是否满足的脚本。

## 基本原则

1. **文件名**：`target.ts` 或描述性名称
2. **位置**：<项目>/.auto-coder/targets
3. **语言**：优先使用项目的语言

该脚本会用于后续的项目迭代，每次大模型修改完代码，都会用该脚本修改是否正确以及达到了用户的预期。

下面是一个例子，用户希望给某个nodejs项目的添加cli 命令，你可以写类似如下的脚本：

## 脚本模板

```typescript
#!/usr/bin/env node --experimental-transform-types

/**
 * 验证 [需求描述] 功能
 */

async function main(): Promise<void> {
  console.log('🧪 开始验证 [需求名称]\n');
  
  try {
    // 测试步骤
    await testStep1();
    await testStep2();
    
    console.log('🎉 所有测试通过！');
  } catch (error) {
    console.error('❌ 测试失败:', error);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}
```

## 常用验证方式

### CLI 命令验证
```typescript
import { execSync } from 'child_process';

function runCommand(cmd: string): string {
  return execSync(cmd, { encoding: 'utf8' });
}

// 测试命令输出
const output = runCommand('agent --help');
if (!output.includes('Usage:')) {
  throw new Error('帮助信息不正确');
}
```

### 数据验证
```typescript
function verify(actual: any, expected: any, desc: string) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${desc}: 期望 ${JSON.stringify(expected)}, 实际 ${JSON.stringify(actual)}`);
  }
  console.log(`✅ ${desc} 通过`);
}
```

### 多步骤验证
```typescript
async function testWorkflow() {
  console.log('📋 步骤 1: 初始化');
  const result1 = await step1();
  
  console.log('📋 步骤 2: 验证结果');
  await verifyResult(result1);
}
```

## 输出格式

**成功**：
```
🧪 开始验证 功能名称
✅ 测试点1 通过
✅ 测试点2 通过
🎉 所有测试通过！
```

**失败**：
```
🧪 开始验证 功能名称
❌ 测试失败: 错误描述
```

## 使用流程

1. 分析需求核心功能
2. 编写验证脚本
3. 运行确保通过
4. 记录结果

## 一些常见case 提示

1. 如果用户是要实现一个模块目录下有.ac.mod.md 文件,那么可以参考该文件里的用户快速开始章节里的示例来设计目标文件。
2. 如果是 rest 或者 命令行之类的，则可以通过命令行脚本来完成，比如使用curl 来测试结果是否符合预期。

===

现在，用户的需求是：

<query>
{{ query }}
</query>

请开始撰写验证脚本。