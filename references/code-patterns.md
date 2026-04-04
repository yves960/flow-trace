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

## 异步调用识别（⚠️ 新增）

### @Async 注解
```java
@Async
public void processAsync(Order order) {
    // 异步执行
}

// 调用方
orderService.processAsync(order); // 触发异步
```

**识别要点**：
- 方法标注 `@Async`
- 调用后立即返回，实际执行在异步线程
- 需要追踪异步方法内部的调用

### CompletableFuture
```java
CompletableFuture.supplyAsync(() -> {
    return orderService.process(order);
}).thenAccept(result -> {
    notificationService.send(result);
});
```

**识别要点**：
- `supplyAsync`/`runAsync` 启动异步
- `thenApply`/`thenAccept` 链式调用
- 追踪 Lambda 内部的方法调用

### ApplicationEventPublisher
```java
// 发布事件
applicationEventPublisher.publishEvent(new OrderCreatedEvent(order));

// 监听事件
@EventListener
public void onOrderCreated(OrderCreatedEvent event) {
    // 处理
}

@TransactionalEventListener
public void onOrderCommitted(OrderCreatedEvent event) {
    // 事务提交后处理
}
```

**识别要点**：
- `publishEvent()` → 搜索 `@EventListener`/`@TransactionalEventListener`
- 事件类名作为关联依据
- 可能跨服务（通过 MQ 传输事件）

### 线程池执行
```java
// 方式1: TaskExecutor
@Autowired
private TaskExecutor taskExecutor;
taskExecutor.execute(() -> process(order));

// 方式2: ThreadPoolExecutor
threadPool.submit(() -> process(order));

// 方式3: @Bean TaskExecutor
@Bean
public TaskExecutor asyncExecutor() { ... }
```

**识别要点**：
- `execute()`/`submit()` 启动异步
- 追踪 Runnable/Callable 内部的调用

### 分布式事务补偿
```java
// TCC
@Compensable
public void try() { ... }
public void confirm() { ... }
public void cancel() { ... }

// Seata
@TwoPhaseBusinessAction
public void prepare() { ... }
```

**识别要点**：
- TCC 的 cancel 是异步补偿链路
- Saga 的补偿步骤需要单独追踪

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

**【关键规则】**：发现 INSERT/UPDATE 写入表时，**先自动搜索** SELECT 读取端，找不到时才询问用户！

### 写入时识别

```java
// 发现写入操作
orderMapper.insert(order);
orderMapper.updateStatus(orderId, "PENDING");
```

### 自动搜索读取端

发现写入后，**自动搜索**：

```java
// 搜索模式1: findByStatus 方法
List<Order> orders = orderMapper.findByStatus("PENDING");

// 搜索模式2: @Scheduled 定时任务
@Scheduled(cron = "0 */5 * * * ?")
public void processPendingOrders() {
    List<Order> orders = orderMapper.findByStatus("PENDING");
    // ...
}

// 搜索模式3: 事件监听器
@EventListener(OrderCreatedEvent.class)
public void onOrderCreated(OrderCreatedEvent event) {
    Order order = orderMapper.findById(event.getOrderId());
    // ...
}
```

### 搜索策略

**按以下顺序搜索**：

1. **同一服务内搜索**：
   - 搜索 `findByStatus`、`selectByStatus`、`queryByStatus` 方法
   - 搜索包含表名的 Mapper 方法
   - 搜索 `@Scheduled` 注解的方法中查询该表

2. **跨服务搜索**（如已配置多个服务目录）：
   - 在所有已配置服务中搜索该表的 SELECT 操作

3. **状态字段匹配**：
   - 如果写入时设置 `status='PENDING'`，搜索 `findByStatus("PENDING")`

### 搜索结果处理

**找到唯一读取端**：
```
自动找到读取端:
表名: order_task
读取端: task-service:TaskProcessor.process
触发机制: @Scheduled(cron="0 */5 * * * ?")

是否确认追踪该读取端? (y/n):
```

**找到多个候选**：
```
找到多个读取端候选:
1. task-service:TaskProcessor.process (定时任务)
2. admin-service:OrderQuery.list (管理后台)

请选择主要读取端 (输入序号):
```

**未找到读取端**：
```
未自动找到读取端，请手动输入:
请输入读取端服务名:
```

### 追踪顺序

```
写入端 → 数据表 → 自动搜索读取端 → 读取端的下游调用

示例:
OrderService.createOrder (写入端)
    │ INSERT order_task (自动发现)
    ▼
order_task 表 (status字段)
    │ 自动搜索 → 找到 TaskProcessor.process
    │ SELECT status='PENDING'
    ▼
TaskProcessor.process (读取端，自动追踪)
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