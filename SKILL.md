---
name: flow-trace
description: 跨微服务调用链分析工具。输入入口点，AI自动追踪跨服务的HTTP/RPC/MQ/DB调用，支持网关路由解析、表驱动异步流程递归追踪，输出JSON路径，默认生成Mermaid时序图。
instructions: |
  ## 🛑 强制规则（违反任何一条 = 分析失败）
  
  ### 分析每个服务时必须做的事
  
  1. **🛑 分析外部调用**：必须识别并列出所有外部服务调用（HTTP/RPC/MQ/DB）
     - 扫描代码中的 RestTemplate、Feign、Dubbo @Reference、Kafka/RabbitMQ/RocketMQ producer
     - 对每个外部调用，记录：目标服务、调用方式、路径/方法
     - 参考 references/code-patterns.md 中的识别模式
  
  2. **🛑 追踪外部服务**：发现外部调用时，如果目标服务在已配置目录中，必须递归分析
  
  3. **🛑 表驱动异步流程**：发现 INSERT/UPDATE 时，必须搜索读取端！
  
  ### 分析完成后必须做的事
  
  4. **🛑 必须调用 save 命令**
  ```bash
  python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> @/tmp/result.txt
  ```
  
  5. **🛑 save 后必须展示询问菜单并等待用户选择**（save 命令会自动输出菜单）
  
  **绝对禁止**：跳过外部调用分析、跳过 save、跳过询问菜单、不等待用户直接继续
---

# Flow Trace Skill

跨微服务调用链分析工具。

## 使用方式

```
/flow-trace <入口点> [选项]
```

| 入口点格式 | 示例 |
|------------|------|
| `服务名:类名.方法名` | `user-service:UserController.login` |
| `服务名:/api路径` | `order-service:/api/orders/create` |
| `网关名:gateway` | `api-gateway:gateway` |

| 选项 | 说明 |
|------|------|
| `--depth N` | 追踪深度，默认5 |
| `--format FORMAT` | mermaid(默认)/plantuml/drawio/all |
| `--type TYPE` | sequence(默认)/flowchart/both |

---

## 分析流程

```
Step 0: context 命令 → 查看上下文
Step 1: 解析入口点 → 定位服务目录
Step 2: 分析服务 → 🛑 必须识别所有外部调用（HTTP/RPC/MQ/DB）
Step 3: 递归追踪 → 🛑 对每个外部服务调用，追踪到目标服务
Step 4: save 命令 → 保存结果（包含外部调用列表）
Step 5: 🛑 展示询问菜单 → 等待用户选择（不可跳过）
Step 6: 用户选择「结束」→ preview → 确认 → export
```

### Step 2: 分析服务（必须识别外部调用）

分析代码时，**必须扫描并列出所有外部调用**：

| 调用类型 | 识别模式 | 输出信息 |
|---------|---------|--------|
| HTTP | RestTemplate, WebClient, Feign | 目标服务 + URL路径 |
| RPC | @Reference(Dubbo), gRPC Stub | 目标服务 + 方法 |
| MQ | kafkaTemplate, rabbitTemplate, rocketMQTemplate | Topic/Queue + 生产者/消费者 |
| DB | Mapper, Repository, JdbcTemplate | 表名 + 操作类型 |
| 异步 | @Async, CompletableFuture, EventPublisher | 异步目标 + 触发方式 |

**禁止只列出内部方法调用而忽略外部依赖！**

### Step 3: 表驱动异步流程

**发现 INSERT/UPDATE 时必须搜索读取端：**
1. 搜索 `findByStatus`/`selectByStatus` 方法
2. 搜索 `@Scheduled` 定时任务
3. 跨服务搜索（如已配置目录）
4. 未找到则询问用户

### Step 4: 保存结果

```bash
# 从文件读取（推荐）
python .../flow_trace_record.py save <服务名> <入口点> @/tmp/result.txt

# 或从 stdin 读取
cat result.txt | python .../flow_trace_record.py save <服务名> <入口点> -
```

### Step 5: 询问菜单

| 选项 | 说明 |
|------|------|
| 1. 分析其他入口点 | 新的分析 |
| 2. 深入分析某个节点 | 更深入分析 |
| 3. 追踪未分析的下游服务 | 继续追踪 |
| **4. 补充遗漏的异步链路** | **手动补充异步流程** |
| 5. 配置服务目录 | 添加服务路径 |
| 6. 结束探索 | 生成图表 |
| 7. 仅输出JSON | 输出原始数据 |

---

## 脚本命令

```bash
# 清空旧记录
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py clear

# 查看上下文
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py context

# 保存结果
python .../flow_trace_record.py save <服务名> <入口点> @/tmp/result.txt

# 汇总所有服务
python .../flow_trace_record.py summary

# 预览并导出
python .../flow_trace_record.py preview
python .../flow_trace_record.py export [输出路径]
```

---

## 详细文档

- [代码识别模式](references/code-patterns.md) - HTTP/RPC/MQ/DB/异步调用识别
- [图表生成说明](references/diagram-generation.md) - Mermaid/DrawIO模板
- [示例对话](references/examples.md) - 完整分析流程示例

---

## 注意事项

1. 需要代码访问权限
2. 默认深度5层
3. **🛑 必须保存结果**
4. **🛑 必须展示询问菜单**
5. **🛑 发现 INSERT/UPDATE 必须搜索读取端**
6. 输出前需用户确认