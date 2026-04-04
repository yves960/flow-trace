---
name: flow-trace
description: 跨微服务调用链分析工具。输入入口点，AI自动追踪跨服务的HTTP/RPC/MQ/DB调用，支持网关路由解析、表驱动异步流程递归追踪，输出JSON路径，默认生成Mermaid时序图。
instructions: |
  ## 🔴 强制规则
  
  ### 规则1: 分析前查看上下文
  ```bash
  python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py context
  ```
  
  ### 规则2: 分析后保存结果
  ```bash
  python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<JSON结果>'
  ```
  
  ### 规则3: 保存后必须询问
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
  
  **禁止**: 跳过询问、连续分析不保存、直接生成图表
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

```
Step 0: 查看上下文 → context 命令
Step 1: 解析入口点 → 定位服务目录
Step 2: 分析服务 → 识别调用
Step 3: 递归追踪 → 发现跨服务调用
Step 4: 保存结果 → save 命令
Step 5: 探索询问 → 继续/结束
Step 6: 生成图表 → summary 命令
```

---

## 流程记录脚本

解决长对话遗忘问题。详细用法见 `scripts/flow_trace_record.py`。

### 核心命令

```bash
# 查看配置的服务路径
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py config

# 分析前：查看上下文
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py context

# 分析后：保存结果
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<JSON>'

# 结束时：汇总所有服务
python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py summary
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
3. 必须调用脚本保存结果
4. 必须展示探索询问菜单