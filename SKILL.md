---
name: flow-trace
description: 跨微服务调用链分析工具。输入入口点，AI自动追踪跨服务的HTTP/RPC/MQ/DB调用，支持网关路由解析、表驱动异步流程递归追踪，输出JSON路径，默认生成Mermaid时序图。
instructions: |
  ## 🛑 分析完成后必须立即停止！
  
  **每个服务分析完成后，必须按以下顺序执行，缺一不可：**
  
  ### 1. 保存分析结果（直接保存原始输出）
  ```bash
  python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<原始输出内容>'
  ```
  
  直接把分析结果保存进去，不需要转JSON格式。
  
  ### 2. 🛑 立即停止，展示询问菜单
  
  **询问菜单（必须完整输出）：**
  ```
  ════════════════════════════════════════════════════════
  📍 分析完成！请选择下一步操作：
  ════════════════════════════════════════════════════════
  
  1. 分析其他入口点
  2. 深入分析某个节点
  3. 追踪未分析的下游服务
  4. 配置/更新服务目录
  5. 批量配置服务目录
  6. 结束探索，生成图表
  7. 仅输出JSON，不生成图表
  
  请选择 (1/2/3/4/5/6/7):
  ```
  
  ### 3. 等待用户选择
  
  **🚫 绝对禁止：**
  - 分析完直接继续分析下一个服务
  - 跳过询问菜单
  - 不等用户选择就继续
  
  用户选择"结束探索"后，调用 summary 汇总所有结果，然后 preview/export。
---

# Flow Trace Skill

跨微服务调用链分析工具。

## 使用方式

```
/flow-trace <入口点> [选项]
```

### 入口点格式

| 格式 | 示例 |
|------|------|
| `服务名:类名.方法名` | `user-service:UserController.login` |
| `服务名:/api路径` | `order-service:/api/orders/create` |
| `网关名:gateway` | `api-gateway:gateway` |

### 选项

| 选项 | 说明 |
|------|------|
| `--depth N` | 追踪深度，默认5 |
| `--format FORMAT` | mermaid(默认)/plantuml/drawio/all |
| `--type TYPE` | sequence(默认)/flowchart/both |

---

## 分析流程

**⚠️ 每个步骤必须按顺序执行，不得跳过！**

```
Step 0: 查看上下文 → context 命令
Step 1: 解析入口点 → 定位服务目录
Step 2: 分析服务 → 识别调用
Step 3: 递归追踪 → 发现跨服务调用
Step 4: 保存结果 → save 命令（见下方格式说明）
Step 5: 🛑 立即停止，展示询问菜单 → 等待用户选择
Step 6: 用户选择「结束探索」→ preview → 用户确认 → export
```

### Step 4: 保存结果

分析完一个服务后，直接把分析结果保存进去，不需要转JSON格式：

```bash
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<分析结果原始内容>'
```

**示例**：
```bash
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save user-service UserController.login '
## 分析结果

入口点: UserController.login

调用链:
1. UserService.login() -> auth-service
2. AuthClient.verify() -> HTTP POST /api/verify

下游服务: auth-service
'
```

**Step 5 是强制步骤！** 分析完成后必须立即展示询问菜单，不能继续分析其他服务。

### Step 6: 输出图表

**用户选择"结束探索"后：**

1. 先展示图表预览（Mermaid 代码）
2. 询问用户确认：
   ```
   📊 图表已生成预览，是否输出到文件？
   
   输出路径（默认: ./flow-trace-output.md）:
   或输入 'cancel' 取消:
   ```
3. 用户确认路径后，写入 Markdown 文件

**输出文件格式：**
```markdown
# 跨微服务调用链分析

## 服务列表
- user-service
- auth-service
- ...

## 调用关系图

```mermaid
sequenceDiagram
    ...
```

## 详细调用链
...
```

---

## 流程记录脚本

解决长对话遗忘问题。详细用法见 `scripts/flow_trace_record.py`。

### 核心命令

```bash
# 开始前：清空旧记录（可选）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py clear

# 开始前：查看上下文
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py context

# 分析后：保存结果（直接保存原始输出）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<原始内容>'

# 结束时：汇总所有服务（输出所有原始内容给模型）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py summary

# 预览并导出
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py preview
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py export [输出路径]
```

---

## 详细文档

- [代码识别模式](references/code-patterns.md) - HTTP/RPC/MQ/DB调用识别
- [图表生成说明](references/diagram-generation.md) - Mermaid/DrawIO模板
- [示例对话](references/examples.md) - 完整分析流程示例

---

## 注意事项

1. 需要代码访问权限
2. 默认深度5层
3. **🛑 必须调用脚本保存结果**
4. **🛑 必须展示探索询问菜单，等待用户选择**
5. **🛑 禁止分析完直接继续，必须停下来询问**
6. 输出前必须用户确认