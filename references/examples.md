# 示例对话

## 示例1：标准同步调用

```
用户: /flow-trace user-service:UserController.login

AI: 开始分析 user-service:UserController.login (Step 1)

请输入 user-service 的代码路径: /projects/user-service

正在分析 UserController.java... (Step 2b)
找到端点: POST /api/login
  → 调用 UserService.login

正在分析 UserService.java...
  → HTTP调用: RestTemplate POST http://auth-service/api/verify

发现外部服务: auth-service
请输入 auth-service 的代码路径 (skip跳过/quit退出): /projects/auth-service

正在分析 AuthController.java... (Step 3 递归)
找到端点: POST /api/verify
  → 调用 AuthService.verify

正在分析 AuthService.java...
  → 数据库调用: authMapper.findByToken

分析完成！(Step 4 记录结果)

════════════════════════════════════════════════════════
是否继续探索？(Step 5)
════════════════════════════════════════════════════════

本次分析发现的路径:
• user-service → auth-service (HTTP)

探索选项:
1. 分析其他入口点
2. 深入分析某个节点
3. 追踪未分析的下游服务
4. 结束探索，生成图表
5. 仅输出JSON，不生成图表

请选择 (1/2/3/4/5): 4

════════════════════════════════════════════════════════
生成图表 (Step 6)
════════════════════════════════════════════════════════

生成图表类型:
1. 流程图 (flowchart)
2. 时序图 (sequence)
3. 两者都生成

请选择 (1/2/3): 2

正在调用 drawio skill...
已生成: login-flow-sequence.drawio

分析结束。
```

---

## 示例2：网关分析

```
用户: /flow-trace edge-gateway:gateway

AI: 开始分析网关 edge-gateway (Step 1)

请输入 edge-gateway 的代码路径: /projects/edge-gateway

检测到网关类型: Spring Cloud Gateway (Step 2a)
正在分析 src/main/resources/application.yml...

发现路由规则:
┌──────────────────┬─────────────────┐
│ 路径              │ 下游服务         │
├──────────────────┼─────────────────┤
│ /api/user/**     │ user-service    │
│ /api/order/**    │ order-service   │
│ /api/flow/**     │ flow-service    │
└──────────────────┴─────────────────┘

发现下游服务: user-service, order-service, flow-service

请输入 user-service 的代码路径 (skip跳过/quit退出): /projects/user-service

请输入 order-service 的代码路径 (skip跳过/quit退出): skip

请输入 flow-service 的代码路径 (skip跳过/quit退出): /projects/flow-service

──────────────────────────────────────────────────────────
正在追踪 user-service... (Step 3 递归)
──────────────────────────────────────────────────────────
找到: /api/user/login → UserController.login
  → UserService.login
  → HTTP调用: auth-service/api/verify

发现下游服务: auth-service
请输入 auth-service 的代码路径 (skip跳过/quit退出): /projects/auth-service

正在追踪 auth-service...
  POST /api/verify
    → AuthService.verify
    → DB: authMapper.findByToken

──────────────────────────────────────────────────────────
正在追踪 flow-service... (Step 3 递归)
──────────────────────────────────────────────────────────
找到: /api/flow/execute → FlowController.execute
  → FlowService.execute
  → MQ: flow-events (Kafka)
  → RPC: rule-engine (Dubbo)

发现下游服务: rule-engine
请输入 rule-engine 的代码路径 (skip跳过/quit退出): skip

分析完成！(Step 4 记录结果)

════════════════════════════════════════════════════════
是否继续探索？(Step 5)
════════════════════════════════════════════════════════

本次分析发现的路径:
• edge-gateway → user-service → auth-service
• edge-gateway → flow-service → Kafka

本次发现但未追踪的服务:
• order-service (用户选择skip)
• rule-engine (用户选择skip)

探索选项:
1. 分析其他入口点
2. 深入分析某个节点
3. 追踪未分析的下游服务
4. 结束探索，生成图表
5. 仅输出JSON，不生成图表

请选择 (1/2/3/4/5): 4

════════════════════════════════════════════════════════
生成图表 (Step 6)
════════════════════════════════════════════════════════

汇总追踪结果:
- 涉及服务: edge-gateway, user-service, auth-service, flow-service
- 外部服务调用: HTTP, Dubbo (未追踪)
- MQ: Kafka flow-events

生成图表类型:
1. 流程图 (flowchart)
2. 时序图 (sequence)
3. 两者都生成

请选择 (1/2/3): 2

已生成: edge-gateway-sequence.drawio

分析结束。
```

---

## 示例3：多层异步流程 + 外部服务调用

```
用户: /flow-trace flow-service:FlowExecutor.execute

AI: 开始分析 flow-service:FlowExecutor.execute (Step 1)

请输入 flow-service 的代码路径: /projects/flow-service

正在分析 FlowExecutor.java... (Step 2b)
找到: execute方法
  → 写入异步表: process_task
  → 状态字段: status

════════════════════════════════════════════════════════
检测到表驱动异步流程
════════════════════════════════════════════════════════
表名: process_task
状态字段: status

请确认:
1. 下游流程是什么? (哪个服务消费表)
2. 触发机制? (定时任务/事件/手动)

请输入下游服务 task-service 的代码路径: /projects/task-service
触发机制: 定时任务每5分钟

──────────────────────────────────────────────────────────
正在分析下游流程 task-service:TaskProcessor.process... (Step 3)
──────────────────────────────────────────────────────────
找到: TaskProcessor.process
  → SELECT process_task WHERE status='PENDING'
  → 处理任务逻辑
  → HTTP调用: notification-service/api/send

════════════════════════════════════════════════════════
发现外部服务: notification-service
════════════════════════════════════════════════════════

是否继续分析 notification-service?
请输入 notification-service 的代码路径 (skip跳过/quit退出): /projects/notification-service

──────────────────────────────────────────────────────────
正在分析 notification-service... (Step 3 递归)
──────────────────────────────────────────────────────────
找到: NotificationController.notify
  → NotificationService.createNotifyTask
  → 写入异步表: notification_queue
  → 状态字段: status

════════════════════════════════════════════════════════
发现嵌套的表驱动流程 (第二层)
════════════════════════════════════════════════════════
第一层: process_task (已分析)
  ↓
第二层: notification_queue (新发现)

是否继续分析 notification_queue 的下游流程?
请输入下游服务 notify-service 的代码路径 (skip跳过/quit退出): /projects/notify-service
触发机制: 事件监听(notification_queue_insert)

──────────────────────────────────────────────────────────
正在分析下游流程 notify-service:NotificationSender.send... (Step 3)
──────────────────────────────────────────────────────────
找到: NotificationSender.send
  → SELECT notification_queue WHERE status='PENDING'
  → 发送通知
  → UPDATE status='COMPLETED'

分析完成！(Step 4 记录结果)

════════════════════════════════════════════════════════
分析完成！是否继续探索？(Step 5)
════════════════════════════════════════════════════════

异步流程链:
flow-service → process_task → task-service → notification-service → notification_queue → notify-service

探索选项:
1. 分析其他入口点
2. 深入分析某个节点
3. 追踪未分析的下游服务
4. 结束探索，生成图表
5. 仅输出JSON，不生成图表

请选择 (1/2/3/4/5): 4

════════════════════════════════════════════════════════
生成图表 (Step 6)
════════════════════════════════════════════════════════

汇总追踪结果:
- 涉及服务: flow-service, task-service, notification-service, notify-service
- 异步表: process_task, notification_queue
- 外部服务调用: task-service → notification-service (HTTP)

生成图表类型:
1. 流程图 (flowchart)
2. 时序图 (sequence)
3. 两者都生成

请选择 (1/2/3): 2

已生成: async-flow-chain-sequence.drawio

分析结束。
```