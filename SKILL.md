---
name: flow-trace
description: 跨微服务调用链分析工具。输入入口点，AI自动追踪跨服务的HTTP/RPC/MQ/DB调用，支持网关路由解析、表驱动异步流程递归追踪，输出JSON路径，默认生成Mermaid时序图。
instructions: |
  ## 🛑 分析完成后必须立即停止！
  
  **每个服务分析完成后，必须按以下顺序执行，缺一不可：**
  
  ### 1. 保存分析结果
  ```bash
  # 从文件读取（推荐）
  python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> @/path/to/result.txt
  
  # 或从 stdin 读取
  cat result.txt | python .../flow_trace_record.py save <服务名> <入口点> -
  ```
  
  ### 2. 🛑 立即停止，展示询问菜单
  
  **询问菜单（必须完整输出）：**
  ```
  ════════════════════════════════════════════════════════
  📍 分析完成！请选择下一步操作：
  ════════════════════════════════════════════════════════
  
  1. 分析其他入口点
  2. 深入分析某个节点
  3. 追踪未分析的下游服务
  4. 补充遗漏的异步链路
  5. 配置/更新服务目录
  6. 结束探索，生成图表
  7. 仅输出JSON，不生成图表
  
  请选择 (1/2/3/4/5/6/7):
  ```
  
  ### 3. 等待用户选择
  
  **🚫 绝对禁止：**
  - 分析完直接继续分析下一个服务
  - 跳过询问菜单
  - 不等用户选择就继续
  
  ---
  
  ## ⚠️ 表驱动异步流程（INSERT/UPDATE → 定时任务）
  
  **发现 INSERT/UPDATE 时，必须搜索读取端！**
  
  1. 记录：表名、操作、状态字段
  2. 搜索读取端：
     - `findByStatus`/`selectByStatus` 方法
     - `@Scheduled` 定时任务中的查询
     - 跨服务搜索（如已配置目录）
  3. 找到后继续追踪下游
  4. 未找到则询问用户
  
  **禁止跳过异步流程追踪！**
  
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
Step 3: 递归追踪 → 发现跨服务调用/表驱动异步流程
Step 4: 保存结果 → save 命令
Step 5: 🛑 立即停止，展示询问菜单 → 等待用户选择
Step 6: 用户选择「结束探索」→ preview → 用户确认 → export
```

### Step 3: 递归追踪（关键步骤）

#### 3.1 发现调用时的处理

| 调用类型 | 处理方式 |
|----------|----------|
| HTTP/RPC | 询问是否继续追踪目标服务 |
| MQ | 追踪生产者 → 搜索消费者 |
| **INSERT/UPDATE** | **必须搜索读取端！** |

#### 3.2 表驱动异步流程（⚠️ 重点）

**发现 INSERT/UPDATE 时，必须执行：**

1. **记录写入**：表名、操作类型、状态字段
2. **搜索读取端**：
   - 在当前服务内搜索 `findByStatus`/`selectByStatus` 等方法
   - 搜索 `@Scheduled` 定时任务中查询该表的代码
   - 如果配置了多个服务目录，跨服务搜索
3. **找到读取端后**：继续追踪读取端的下游调用
4. **未找到读取端**：询问用户补充

**示例输出**：
```
发现数据写入:
表名: order_task
操作: INSERT status='PENDING'

正在搜索读取端...
✅ 找到定时任务: TaskProcessor.process
   触发: @Scheduled(cron="0 */5 * * * ?")
   查询: taskMapper.findByStatus("PENDING")

是否继续追踪 TaskProcessor.process? (y/n):
```

**如果未找到**：
```
⚠️ 未找到 order_task 表的读取端

请确认:
1. 读取这个表的服务是什么？
2. 触发机制是什么？（定时任务/事件/手动）

请输入读取端服务名 (或 skip 跳过):
```

### Step 4: 保存结果

分析完一个服务后，直接把分析结果保存进去：

```bash
# 方式1：直接传递（适合短内容）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<内容>'

# 方式2：从文件读取（适合长内容，推荐）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> @/path/to/result.txt

# 方式3：从 stdin 读取
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> -
```

**示例**：
```bash
# 从文件读取
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save user-service UserController.login @/tmp/analysis.txt

# 从 stdin 读取
cat analysis.md | python .../flow_trace_record.py save user-service UserController.login -
```

**Step 5 是强制步骤！** 分析完成后必须立即展示询问菜单，不能继续分析其他服务。

### 询问菜单选项说明

| 选项 | 说明 |
|------|------|
| 1. 分析其他入口点 | 输入新的入口点开始新的分析 |
| 2. 深入分析某个节点 | 对已分析的某个服务进行更深入的分析 |
| 3. 追踪未分析的下游服务 | 继续追踪发现的下游服务 |
| **4. 补充遗漏的异步链路** | **手动补充模型未识别的异步流程** |
| 5. 配置/更新服务目录 | 添加或修改服务代码路径 |
| 6. 结束探索，生成图表 | 汇总所有分析结果，输出图表 |
| 7. 仅输出JSON，不生成图表 | 输出原始数据 |

### 选项 4：补充遗漏的异步链路

**使用场景**：
- 发现 INSERT/UPDATE 但没找到读取端
- 发现 `@Async`/`CompletableFuture` 但没追踪
- 发现事件发布但没找到监听器

**交互示例**：
```
请输入遗漏的异步链路信息：

上游服务: order-service
上游方法: OrderService.createOrder
中间表/事件: order_task 表
下游服务: task-service
下游方法: TaskProcessor.process
触发机制: 定时任务 @Scheduled(cron="0 */5 * * * ?")

是否继续追踪 task-service:TaskProcessor.process? (y/n):
```

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
# 开始前：清空旧记录
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py clear

# 开始前：查看上下文
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py context

# 分析后：保存结果（从文件读取，推荐）
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> @/tmp/result.txt

# 或从 stdin 读取
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> -

# 结束时：汇总所有服务
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