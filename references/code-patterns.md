# 代码识别模式

## HTTP调用识别

分析以下模式：

```java
// RestTemplate
restTemplate.getForObject(url, ...)
restTemplate.postForObject(url, ...)

// WebClient
webClient.get().uri(path)
webClient.post().uri(path)

// Feign
@FeignClient(name="service-name")
xxxClient.method()
```

**提取信息**：
- 调用类型：GET/POST/PUT/DELETE
- 目标服务：从URL或@FeignClient提取
- 路径：API路径

## RPC调用识别

```java
// Dubbo
@Reference
private XxxService xxxService;
xxxService.method()

// gRPC
xxxStub.method(request)
```

**提取信息**：
- RPC类型：Dubbo/gRPC
- 目标服务：从@Reference或Stub提取
- 方法名

## MQ调用识别

```java
// Producer
kafkaTemplate.send(topic, ...)
rabbitTemplate.convertAndSend(exchange, routingKey, ...)
rocketMQTemplate.send(topic, ...)

// Consumer
@KafkaListener(topics = "xxx")
@RabbitListener(queues = "xxx")
```

**提取信息**：
- MQ类型：Kafka/RabbitMQ/RocketMQ
- Topic/Queue名称
- 生产者/消费者角色

## 数据库调用识别

```java
// MyBatis
xxxMapper.selectXxx()
xxxMapper.insertXxx()
xxxMapper.updateXxx()

// JPA
xxxRepository.findById()
xxxRepository.save()

// JDBC
jdbcTemplate.query(...)
```

**提取信息**：
- 数据库类型：MyBatis/JPA/JDBC
- 操作类型：SELECT/INSERT/UPDATE/DELETE
- 表名（如有）

## 表驱动异步流程识别

**场景**：通过数据库表进行异步流程编排
- 上游流程 → 写入表/更新状态
- 下游流程 → 从表查询 → 继续处理
- **没有直接的API调用，通过表解耦**

**【关键规则】**：发现 INSERT/UPDATE 写入表时，**必须**追踪 SELECT 读取端！

### 写入时识别

```java
// 发现写入操作
orderMapper.insert(order);
orderMapper.updateStatus(orderId, "PENDING");
```

**发现写入时强制询问**：
```
发现数据写入:
表名: order_task
操作: INSERT status='PENDING'
上下文: OrderService.createOrder → orderMapper.insert(order)

════════════════════════════════════════════════════════
【强制】该表的数据被谁读取？
════════════════════════════════════════════════════════

请确认:
1. 读取这个表的服务是什么？
2. 读取方法/触发机制是什么？

请输入读取端服务名:
请输入读取端代码路径:
```

### 读取端识别

```java
// 追踪读取端
List<Order> orders = orderMapper.findByStatus("PENDING");
for (Order order : orders) {
    processOrder(order);
    orderMapper.updateStatus(order.getId(), "PROCESSED");
}
```

**分析要点**：
1. 识别**状态字段**（如 `status`, `state`, `process_status`）
2. 识别**状态流转**（PENDING → PROCESSING → PROCESSED）
3. 找到**写入端**（上游流程）← 从这里开始追踪
4. 找到**消费端**（下游流程）← **必须追踪到这里！**
5. 识别**触发机制**（定时任务/事件监听/手动触发）

### 追踪顺序

```
写入端 → 数据表 → 读取端 → 读取端的下游调用

示例:
OrderService.createOrder (写入端)
    │ INSERT order_task
    ▼
order_task 表 (status字段)
    │ SELECT status='PENDING'
    ▼
TaskProcessor.process (读取端)
    │ HTTP POST
    ▼
NotificationService (下游服务)
```

## 表驱动异步流程分析流程

**Step 1: 识别表驱动模式并询问上下游**

```
检测到表驱动异步流程:
表名: process_task
状态字段: status

请确认:
1. 上游流程是什么? (哪个服务写入表)
2. 下游流程是什么? (哪个服务消费表)
3. 触发机制? (定时任务/事件/手动)

上游: flow-service:FlowExecutor.execute
下游: task-service:TaskProcessor.process
触发: 每5分钟定时任务
```

**Step 2: 分析下游流程，识别外部服务调用**

分析下游流程代码，识别是否调用外部服务：
- HTTP/RPC调用其他服务
- 发送到MQ（需追踪消费者）
- 写入另一个异步表（可能触发更下游的流程）

**Step 3: 发现外部服务时递归询问**

```
分析下游流程 task-service:TaskProcessor.process 时发现:
  → HTTP调用: notification-service/api/send
  → 上下文: RestTemplate POST http://notification-service:8080/api/send

════════════════════════════════════════════════════════
发现外部服务: notification-service
════════════════════════════════════════════════════════

是否继续分析 notification-service?
- 输入代码路径 → 继续追踪
- skip → 跳过该服务，但记录在流程图中
- quit → 结束追踪

请输入 notification-service 的代码路径 (skip跳过/quit退出):
```

**Step 4: 支持多层异步表嵌套**

如果下游流程又写入另一个异步表：

```
分析 task-service:TaskProcessor.process 时发现:
  → 写入异步表: notification_queue
  → 状态字段: status

════════════════════════════════════════════════════════
发现嵌套的表驱动流程:
════════════════════════════════════════════════════════
第一层: process_task (当前分析)
  ↓
第二层: notification_queue (新发现)

是否继续分析 notification_queue 的下游流程?
- 输入下游服务路径 → 继续追踪
- skip → 跳过，只记录到当前流程
- quit → 结束追踪

请输入 notification_queue 消费服务的代码路径 (skip跳过/quit退出):
```

**Step 5: 构建完整的异步流程链**

将所有发现的异步表和外部服务调用串联起来：

```
异步流程链:
┌─────────────────┐
│ flow-service    │
│ FlowExecutor    │
└────────┬────────┘
         │ INSERT
         ▼
┌─────────────────┐
│ process_task    │ ← 异步表1
│ status=PENDING  │
└────────┬────────┘
         │ SELECT (定时任务每5分钟)
         ▼
┌─────────────────┐
│ task-service    │
│ TaskProcessor   │
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│ notification-   │ ← 外部服务
│ service         │
└────────┬────────┘
         │ INSERT
         ▼
┌─────────────────┐
│ notification_   │ ← 异步表2 (嵌套)
│ queue           │
└────────┬────────┘
         │ SELECT (事件触发)
         ▼
┌─────────────────┐
│ notify-service  │
│ NotificationSend│
└─────────────────┘
```