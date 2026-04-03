---
name: flow-trace
description: 分析Java微服务/网关调用链，输出追踪路径，生成业务流程图。输入入口点，AI自动分析代码或网关配置，识别HTTP/RPC/MQ/DB调用，输出JSON路径，调用drawio生成流程图。
---

# Flow Trace Skill

AI驱动的微服务调用链分析，支持**业务服务**和**边缘网关**。

## 使用方式

```
/flow-trace <入口点> [选项]
```

### 入口点格式

**业务服务**：

| 格式 | 示例 |
|------|------|
| `服务名:类名.方法名` | `user-service:UserController.login` |
| `服务名:/api路径` | `order-service:/api/orders/create` |
| `服务名:类名` | `payment-service:PaymentService` |

**网关服务**：

| 格式 | 示例 |
|------|------|
| `网关名:gateway` | `api-gateway:gateway` |
| `网关名:/api路径` | `api-gateway:/api/user/login` |

### 选项

| 选项 | 说明 |
|------|------|
| `--depth N` | 追踪深度，默认5 |
| `--output FILE` | 输出文件名 |
| `--gateway-type TYPE` | 网关类型：spring-cloud-gateway/kong/nginx/apisix |

### 示例

**业务服务**：
```
/flow-trace user-service:UserController.login
/flow-trace order-service:/api/orders --depth 10
```

**网关服务**：
```
/flow-trace api-gateway:gateway
/flow-trace api-gateway:/api/user/login
/flow-trace gateway:gateway --gateway-type spring-cloud-gateway
```

---

## 分析流程

```
1. 解析入口点
   └── 定位服务代码目录

2. 读取入口文件
   └── 分析Controller/Service

3. 识别调用链
   ├── HTTP调用 → 提取目标服务
   ├── RPC调用 → 提取目标服务
   ├── MQ调用 → 提取Topic/Queue
   └── DB调用 → 提取表/操作

4. 递归分析
   └── 对下游服务重复步骤2-3

5. 输出追踪路径
   └── JSON格式路径

6. 生成流程图
   └── 调用drawio skill
```

---

## 网关分析

边缘网关是API入口，通过配置文件定义路由规则，不写业务代码。

### 支持的网关类型

| 网关 | 配置文件 | 识别方式 |
|------|----------|----------|
| Spring Cloud Gateway | `application.yml` / `RouteDefinition` | Java配置或YAML |
| Kong | `kong.yml` / Admin API | YAML/JSON |
| APISIX | `apisix.yaml` / Admin API | YAML |
| Nginx | `nginx.conf` | 配置文件 |
| Envoy | `envoy.yaml` | YAML |

### 网关分析流程

```
1. 检测网关类型
   └── 根据文件结构或参数判断

2. 读取路由配置
   ├── Spring Cloud Gateway → application.yml 或 RouteLocator
   ├── Kong → kong.yml
   ├── APISIX → apisix.yaml
   └── Nginx → nginx.conf

3. 解析路由规则
   └── 提取：路径 → 下游服务

4. 构建路由表
   └── 记录所有API路由映射

5. 【重要】询问下游服务路径
   └── 对每个下游服务，询问代码路径

6. 追踪下游服务
   └── 对每个下游服务继续分析
```

### 网关分析关键点

**必须在发现下游服务后询问路径！**

```
分析完网关配置后，AI必须：

1. 列出发现的所有下游服务
2. 逐个询问每个服务的代码路径
3. 用户可以选择：
   - 输入路径 → 继续追踪
   - skip → 跳过该服务
   - quit → 结束追踪

示例流程：
┌─────────────────────────────────────┐
│ 分析 api-gateway 路由配置            │
├─────────────────────────────────────┤
│ 发现下游服务:                        │
│ • user-service                      │
│ • order-service                     │
│ • payment-service                   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 请输入 user-service 的代码路径:      │
│ (skip跳过 / quit退出)                │
└─────────────────────────────────────┘
```

### Spring Cloud Gateway 配置分析

**YAML配置**：

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service-route
          uri: lb://user-service
          predicates:
            - Path=/api/user/**
          filters:
            - StripPrefix=1

        - id: order-service-route
          uri: lb://order-service
          predicates:
            - Path=/api/order/**
```

**分析输出**：
```
路由规则:
  /api/user/** → user-service
  /api/order/** → order-service
```

**Java配置**：

```java
@Bean
public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
    return builder.routes()
        .route("user-service", r -> r.path("/api/user/**")
            .uri("lb://user-service"))
        .route("order-service", r -> r.path("/api/order/**")
            .uri("lb://order-service"))
        .build();
}
```

**识别要点**：
- `uri: lb://service-name` → 负载均衡到服务
- `uri: http://host:port` → 直接转发
- `predicates: Path=/api/xxx` → 路径匹配规则
- `filters` → 过滤器（可选）

### Kong 配置分析

```yaml
_format_version: "3.0"

services:
  - name: user-service
    url: http://user-service:8080
    routes:
      - name: user-route
        paths:
          - /api/user

  - name: order-service
    url: http://order-service:8080
    routes:
      - name: order-route
        paths:
          - /api/order
```

**识别要点**：
- `services[].name` → 服务名
- `services[].url` → 下游地址
- `routes[].paths` → 路由路径

### APISIX 配置分析

```yaml
routes:
  - uri: /api/user/*
    upstream:
      service_name: user-service
    plugins:
      proxy-rewrite:
        regex_uri: ["^/api/user/(.*)", "/$1"]

  - uri: /api/order/*
    upstream:
      service_name: order-service
```

**识别要点**：
- `uri` → 路由路径
- `upstream.service_name` → 下游服务

### Nginx 配置分析

```nginx
location /api/user/ {
    proxy_pass http://user-service:8080/;
}

location /api/order/ {
    proxy_pass http://order-service:8080/;
}
```

**识别要点**：
- `location` → 路由路径
- `proxy_pass` → 下游地址

### 网关输出格式

```json
{
  "entry": {
    "service": "api-gateway",
    "type": "gateway",
    "gateway_type": "spring-cloud-gateway"
  },
  "routes": [
    {
      "path": "/api/user/**",
      "target_service": "user-service",
      "target_url": "lb://user-service"
    },
    {
      "path": "/api/order/**",
      "target_service": "order-service",
      "target_url": "lb://order-service"
    }
  ],
  "flows": [
    {
      "id": "flow-1",
      "nodes": [
        {"id": "gw-1", "type": "gateway", "name": "API Gateway"},
        {"id": "gw-2", "type": "endpoint", "name": "/api/user/**"},
        {"id": "gw-3", "type": "service", "name": "user-service"}
      ],
      "edges": [
        {"from": "gw-1", "to": "gw-2", "label": "路由"},
        {"from": "gw-2", "to": "gw-3", "label": "转发"}
      ]
    }
  ]
}
```

---

## 代码分析指南

### HTTP调用识别

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

### RPC调用识别

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

### MQ调用识别

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

### 数据库调用识别

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

### 表驱动异步流程识别

**场景**：通过数据库表进行异步流程编排
- 上个流程 → 写入表/更新状态
- 下个流程 → 从表查询 → 继续处理
- **没有直接的API调用，通过表解耦**

**识别模式**：

```java
// 上游流程 - 写入/更新
orderMapper.insert(order);
orderMapper.updateStatus(orderId, "PENDING");

// 下游流程 - 查询处理
List<Order> orders = orderMapper.findByStatus("PENDING");
for (Order order : orders) {
    processOrder(order);
    orderMapper.updateStatus(order.getId(), "PROCESSED");
}
```

**分析要点**：
1. 识别**状态字段**（如 `status`, `state`, `process_status`）
2. 识别**状态流转**（PENDING → PROCESSING → PROCESSED）
3. 找到**写入端**（上游流程）
4. 找到**消费端**（下游流程）
5. 识别**触发机制**（定时任务/事件监听/手动触发）

**需要询问用户**：
```
发现表驱动流程:
表名: process_task
状态字段: status
状态值: PENDING → PROCESSING → COMPLETED

请确认:
1. 上游流程是什么? (哪个服务/方法写入这个表)
2. 下游流程是什么? (哪个服务/方法消费这个表)
3. 触发机制是什么? (定时任务/事件/手动)
```

---

## 输出格式

### 追踪路径JSON

**标准同步调用**：

```json
{
  "entry": {
    "service": "user-service",
    "class": "UserController",
    "method": "login",
    "file": "/path/to/UserController.java"
  },
  "flows": [
    {
      "id": "flow-1",
      "nodes": [
        {
          "id": "node-1",
          "type": "endpoint",
          "service": "user-service",
          "name": "POST /api/login",
          "detail": "UserController.login",
          "file": "UserController.java:25"
        },
        {
          "id": "node-2",
          "type": "method",
          "service": "user-service",
          "name": "UserService.login",
          "file": "UserService.java:45"
        },
        {
          "id": "node-3",
          "type": "http",
          "service": "auth-service",
          "name": "POST /api/verify",
          "detail": "RestTemplate → auth-service"
        },
        {
          "id": "node-4",
          "type": "method",
          "service": "auth-service",
          "name": "AuthService.verify",
          "file": "AuthService.java:30"
        },
        {
          "id": "node-5",
          "type": "database",
          "service": "auth-service",
          "name": "MyBatis",
          "detail": "authMapper.findByToken"
        }
      ],
      "edges": [
        {"from": "node-1", "to": "node-2", "label": "调用"},
        {"from": "node-2", "to": "node-3", "label": "HTTP"},
        {"from": "node-3", "to": "node-4", "label": "进入服务"},
        {"from": "node-4", "to": "node-5", "label": "DB查询"}
      ]
    }
  ],
  "services": {
    "user-service": "/path/to/user-service",
    "auth-service": "/path/to/auth-service"
  }
}
```

**多层异步流程链**：

```json
{
  "entry": {
    "service": "flow-service",
    "class": "FlowExecutor",
    "method": "execute"
  },
  "async_chain": [
    {
      "layer": 1,
      "type": "async_table",
      "table": "process_task",
      "status_field": "status",
      "status_values": ["PENDING", "PROCESSING", "COMPLETED"],
      "upstream": {
        "service": "flow-service",
        "method": "FlowExecutor.execute",
        "action": "INSERT status='PENDING'"
      },
      "downstream": {
        "service": "task-service",
        "method": "TaskProcessor.process",
        "trigger": "scheduled(cron='0 */5 * * * ?')",
        "action": "SELECT status='PENDING'"
      },
      "external_calls": [
        {
          "type": "http",
          "service": "notification-service",
          "endpoint": "POST /api/notify",
          "context": "RestTemplate → notification-service:8080",
          "analyzed": true
        }
      ]
    },
    {
      "layer": 2,
      "type": "async_table",
      "table": "notification_queue",
      "status_field": "status",
      "status_values": ["PENDING", "COMPLETED", "FAILED"],
      "upstream": {
        "service": "notification-service",
        "method": "NotificationController.notify",
        "action": "INSERT status='PENDING'"
      },
      "downstream": {
        "service": "notify-service",
        "method": "NotificationSender.send",
        "trigger": "event(notification_queue_insert)",
        "action": "SELECT status='PENDING'"
      },
      "external_calls": []
    }
  ],
  "flows": [
    {
      "id": "flow-1",
      "name": "任务创建流程",
      "nodes": [...],
      "edges": [...]
    },
    {
      "id": "flow-2",
      "name": "任务处理流程",
      "nodes": [...],
      "edges": [...]
    },
    {
      "id": "flow-3",
      "name": "通知发送流程",
      "nodes": [...],
      "edges": [...]
    }
  ],
  "services": {
    "flow-service": "/path/to/flow-service",
    "task-service": "/path/to/task-service",
    "notification-service": "/path/to/notification-service",
    "notify-service": "/path/to/notify-service"
  }
}
```

### 节点类型

| type | 说明 | 图形 |
|------|------|------|
| `service` | 服务节点 | 矩形 |
| `endpoint` | API端点 | 圆角矩形 |
| `method` | 方法 | 圆角矩形 |
| `http` | HTTP调用 | 菱形 |
| `rpc` | RPC调用 | 菱形 |
| `mq` | 消息队列 | 平行四边形 |
| `database` | 数据库 | 圆柱 |

### 时序图数据格式

用于生成时序图的结构：

```json
{
  "sequence": {
    "participants": [
      {"id": "client", "name": "Client", "type": "actor"},
      {"id": "gw", "name": "edge-gateway", "type": "gateway"},
      {"id": "user", "name": "user-service", "type": "service"},
      {"id": "flow", "name": "flow-service", "type": "service"},
      {"id": "auth", "name": "auth-service", "type": "service"},
      {"id": "db", "name": "Database", "type": "database"},
      {"id": "mq", "name": "Kafka", "type": "mq"}
    ],
    "sequences": [
      {
        "id": "seq-1",
        "name": "用户登录流程",
        "steps": [
          {"from": "client", "to": "gw", "msg": "POST /api/user/login", "type": "sync"},
          {"from": "gw", "to": "user", "msg": "路由转发", "type": "sync"},
          {"from": "user", "to": "auth", "msg": "POST /api/verify", "type": "http"},
          {"from": "auth", "to": "db", "msg": "findByToken()", "type": "db"},
          {"from": "db", "to": "auth", "msg": "token记录", "type": "return"},
          {"from": "auth", "to": "user", "msg": "验证结果", "type": "return"},
          {"from": "user", "to": "gw", "msg": "登录结果", "type": "return"},
          {"from": "gw", "to": "client", "msg": "200 OK", "type": "return"}
        ]
      },
      {
        "id": "seq-2", 
        "name": "流程执行流程",
        "steps": [
          {"from": "client", "to": "gw", "msg": "POST /api/flow/execute", "type": "sync"},
          {"from": "gw", "to": "flow", "msg": "路由转发", "type": "sync"},
          {"from": "flow", "to": "mq", "msg": "publish flow-events", "type": "mq"},
          {"from": "flow", "to": "gw", "msg": "执行结果", "type": "return"},
          {"from": "gw", "to": "client", "msg": "200 OK", "type": "return"}
        ]
      }
    ]
  }
}
```

### 步骤类型

| type | 说明 | 时序图箭头 |
|------|------|-----------|
| `sync` | 同步调用 | 实线箭头 |
| `async` | 异步调用 | 虚线箭头 |
| `http` | HTTP请求 | 虚线+标注 |
| `rpc` | RPC调用 | 实线+标注 |
| `mq` | 消息发送 | 虚线+标注 |
| `db` | 数据库操作 | 实线+圆柱 |
| `return` | 返回 | 虚线箭头 |

---

## 图表生成

### 支持的图表类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **时序图** | 展示调用顺序 | 分析单个API完整流程 |
| **流程图** | 展示调用层级 | 分析整体架构关系 |
| **依赖图** | 展示服务依赖 | 分析服务拓扑 |

### 时序图生成

追踪完成后，根据sequence数据生成时序图：

**Mermaid格式**：
```mermaid
sequenceDiagram
    participant Client
    participant GW as edge-gateway
    participant User as user-service
    participant Auth as auth-service
    participant DB as Database
    
    Client->>GW: POST /api/user/login
    GW->>User: 路由转发
    User->>Auth: POST /api/verify (HTTP)
    Auth->>DB: findByToken()
    DB-->>Auth: token记录
    Auth-->>User: 验证结果
    User-->>GW: 登录结果
    GW-->>Client: 200 OK
```

**PlantUML格式**：
```plantuml
@startuml
actor Client
participant "edge-gateway" as GW
participant "user-service" as User
participant "auth-service" as Auth
database "Database" as DB

Client -> GW: POST /api/user/login
GW -> User: 路由转发
User -> Auth: POST /api/verify (HTTP)
Auth -> DB: findByToken()
DB --> Auth: token记录
Auth --> User: 验证结果
User --> GW: 登录结果
GW --> Client: 200 OK
@enduml
```

### DrawIO时序图

调用drawio skill生成.drawio文件：

```
时序图节点:
- participant: 矩形，顶部排列
- lifeline: 垂直虚线
- message: 水平箭头
- activation: 矩形条（可选）
```

---

## Step 6: 生成图表

分析完成后，询问用户需要生成哪种图表：

```
生成图表类型:
1. 时序图 (sequence) - 展示调用顺序和交互 ← 推荐
2. 流程图 (flowchart) - 展示调用层级关系
3. 两者都生成
4. 不生成

请选择 (1/2/3/4): 1
```

选择后，询问DrawIO情况：

```
是否安装了DrawIO桌面应用? (y/n): n

将生成Mermaid格式，可直接在Markdown中渲染
```

**判断逻辑**：
- 有DrawIO → 可选择Mermaid/PlantUML/DrawIO
- 无DrawIO → 自动使用Mermaid格式（无需额外工具）

---

### 时序图生成步骤

1. **构建participants列表**
   - 所有涉及的服务/系统/数据库/MQ
   - 按调用顺序排列

2. **构建sequences列表**
   - 每个API入口一个sequence
   - 按时间顺序记录每一步

3. **输出Mermaid/PlantUML**
   - 默认输出Mermaid格式
   - Markdown可直接渲染

### Mermaid时序图输出

**重要：用业务描述替代技术细节**

```
❌ 不要这样：
    User->>Auth: UserService.verifyToken()

✅ 要这样：
    User->>Auth: 验证用户Token
```

### Mermaid流程图输出

当没有DrawIO时，流程图也用Mermaid格式：

```mermaid
flowchart TB
    subgraph GW["API网关"]
        direction LR
        R1["/api/user/**"] --> S1["user-service"]
        R2["/api/order/**"] --> S2["order-service"]
        R3["/api/flow/**"] --> S3["flow-service"]
    end

    subgraph Services["微服务集群"]
        S1 --> U1["用户管理"]
        S2 --> O1["订单处理"]
        S3 --> F1["流程引擎"]
    end

    subgraph Infra["基础设施"]
        DB[(数据库)]
        MQ{{消息队列}}
        AUTH["认证服务"]
    end

    U1 --> AUTH
    U1 --> DB
    F1 --> MQ

    style GW fill:#e3f2fd
    style Services fill:#e8f5e9
    style Infra fill:#fff3e0
```

**流程图节点类型**：
- `[]` 矩形 - 服务/模块
- `()` 圆角矩形 - 操作
- `[()]` 圆柱 - 数据库
- `{{}}` 菱形 - 判断
- `{{}}` 六边形 - 消息队列

---

```mermaid
sequenceDiagram
    autonumber
    actor 用户 as Client
    participant 网关 as edge-gateway
    participant 用户服务 as user-service
    participant 认证服务 as auth-service
    participant 数据库 as Database
    participant 消息队列 as Kafka

    Note over 用户,网关: 用户登录流程
    用户->>网关: 发起登录请求
    网关->>用户服务: 转发登录请求
    用户服务->>认证服务: 验证用户身份
    activate 认证服务
    认证服务->>数据库: 查询用户信息
    数据库-->>认证服务: 返回用户数据
    deactivate 认证服务
    认证服务-->>用户服务: 返回验证结果
    用户服务-->>网关: 返回登录结果
    网关-->>用户: 登录成功

    Note over 用户,消息队列: 流程执行
    用户->>网关: 发起流程执行请求
    网关->>用户服务: 转发执行请求
    用户服务->>消息队列: 发布流程事件
    用户服务-->>网关: 返回执行结果
    网关-->>用户: 执行成功
```

### 描述转换规则

| 技术细节 | 业务描述 |
|----------|----------|
| `UserController.login` | 处理登录请求 |
| `UserService.login` | 执行登录逻辑 |
| `RestTemplate.post(url)` | 调用下游服务
| `authMapper.findByToken` | 查询认证信息 |
| `kafkaTemplate.send(topic)` | 发送消息到队列 |
| `POST /api/user/login` | 登录接口 |
| `GET /api/user/{id}` | 查询用户信息 |
| `Dubbo invoke xxx` | 调用RPC服务 |

### 描述生成原则

1. **从方法名推断业务含义**
   ```
   login → 登录
   createOrder → 创建订单
   verifyToken → 验证Token
   sendNotification → 发送通知
   ```

2. **从API路径推断**
   ```
   POST /api/user/login → 登录接口
   GET /api/order/{id} → 查询订单
   PUT /api/user/profile → 更新用户资料
   ```

3. **用业务语言而非技术语言**
   ```
   ❌ "调用AuthServiceImpl.verify方法"
   ✅ "验证用户身份"

   ❌ "执行SQL: SELECT * FROM users"
   ✅ "查询用户数据"

   ❌ "发送消息到Kafka topic flow-events"
   ✅ "发布流程事件"
   ```

---

## 表驱动异步流程

### 场景描述

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   上游流程   │ ──→  │   数据库表   │ ──→  │   下游流程   │
│  (写入端)   │      │  (状态流转)  │      │  (消费端)   │
└─────────────┘      └─────────────┘      └─────────────┘
        │                  │                    │
        │  INSERT/UPDATE   │   SELECT          │
        │  status=PENDING  │   status=PENDING  │
        └──────────────────┴────────────────────┘
                    异步解耦
```

### 识别表驱动模式

**代码模式**：
```java
// 上游写入
taskMapper.insert(task);           // INSERT
taskMapper.updateStatus(id, "PENDING"); // UPDATE

// 下游消费
List<Task> tasks = taskMapper.findByStatus("PENDING"); // SELECT
for (Task task : tasks) {
    process(task);
    taskMapper.updateStatus(task.getId(), "COMPLETED");
}

// 定时任务触发
@Scheduled(cron = "0 */5 * * * ?")
public void processPendingTasks() { ... }
```

**识别信号**：
- `status` / `state` / `process_status` 字段
- `findByStatus` / `updateStatus` 方法
- `@Scheduled` 定时任务
- 状态机模式

### 分析流程

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

### 时序图输出

**单层异步表**：

```mermaid
sequenceDiagram
    autonumber
    actor 用户
    participant 上游 as flow-service
    participant DB as process_task表
    participant 定时 as Scheduler
    participant 下游 as task-service

    Note over 用户,上游: 阶段1: 任务创建
    用户->>上游: 发起流程请求
    上游->>DB: INSERT status='PENDING'
    上游-->>用户: 返回任务ID

    Note over 定时,下游: 阶段2: 异步处理
    定时->>下游: 触发(每5分钟)
    下游->>DB: SELECT status='PENDING'
    DB-->>下游: 待处理任务
    下游->>DB: UPDATE status='PROCESSING'
    下游->>下游: 执行任务
    下游->>DB: UPDATE status='COMPLETED'

    Note over 用户,下游: 阶段3: 结果查询
    用户->>上游: 查询状态
    上游->>DB: SELECT BY id
    DB-->>上游: status='COMPLETED'
    上游-->>用户: 返回结果
```

**多层异步表 + 外部服务调用**：

```mermaid
sequenceDiagram
    autonumber
    actor 用户
    participant 上游 as flow-service
    participant DB1 as process_task表
    participant 定时1 as Scheduler
    participant 中游 as task-service
    participant 外部 as notification-service
    participant DB2 as notification_queue表
    participant 定时2 as EventListener
    participant 下游 as notify-service

    Note over 用户,上游: 阶段1: 创建处理任务
    用户->>上游: 发起流程请求
    上游->>DB1: INSERT status='PENDING'
    上游-->>用户: 返回任务ID

    Note over 定时1,中游: 阶段2: 异步处理任务
    定时1->>中游: 触发(每5分钟)
    中游->>DB1: SELECT status='PENDING'
    DB1-->>中游: 待处理任务
    中游->>DB1: UPDATE status='PROCESSING'
    
    Note over 中游,外部: 发现外部服务调用
    中游->>外部: HTTP POST /api/notify
    activate 外部
    外部->>DB2: INSERT status='PENDING'
    外部-->>中游: 返回成功
    deactivate 外部
    
    中游->>DB1: UPDATE status='COMPLETED'

    Note over 定时2,下游: 阶段3: 嵌套异步流程
    定时2->>下游: 事件触发
    下游->>DB2: SELECT status='PENDING'
    DB2-->>下游: 待发送通知
    下游->>下游: 发送通知
    下游->>DB2: UPDATE status='COMPLETED'

    Note over 用户,下游: 阶段4: 结果查询
    用户->>上游: 查询状态
    上游->>DB1: SELECT BY id
    DB1-->>上游: status='COMPLETED'
    上游-->>用户: 返回结果
```

### 流程图输出

**单层异步表**：

```mermaid
flowchart LR
    subgraph 上游["上游流程"]
        A1["接收请求"] --> A2["创建任务"]
        A2 --> A3["写入表<br/>PENDING"]
    end

    subgraph 表["数据库"]
        T1[("process_task")]
    end

    subgraph 触发["触发"]
        C1["定时任务<br/>每5分钟"]
    end

    subgraph 下游["下游流程"]
        B1["查询PENDING"] --> B2["更新PROCESSING"]
        B2 --> B3["执行逻辑"]
        B3 --> B4["更新COMPLETED"]
    end

    A3 --> T1
    T1 --> C1
    C1 --> B1
    B4 --> T1

    style 上游 fill:#e3f2fd
    style 表 fill:#f5f5f5
    style 触发 fill:#fff3e0
    style 下游 fill:#e8f5e9
```

**多层异步表 + 外部服务调用**：

```mermaid
flowchart TB
    subgraph Layer1["第一层: 任务处理"]
        subgraph 上游["flow-service"]
            A1["接收请求"] --> A2["创建任务"]
        end
        
        T1[("process_task<br/>status")]
        
        subgraph 触发1["触发机制"]
            C1["定时任务<br/>每5分钟"]
        end
        
        subgraph 中游["task-service"]
            B1["查询PENDING"] --> B2["处理任务"]
            B2 --> B3["调用外部服务"]
        end
    end

    subgraph Layer2["第二层: 通知发送"]
        subgraph 外部["notification-service"]
            D1["接收请求"] --> D2["创建通知任务"]
        end
        
        T2[("notification_queue<br/>status")]
        
        subgraph 触发2["触发机制"]
            C2["事件监听"]
        end
        
        subgraph 下游["notify-service"]
            E1["查询PENDING"] --> E2["发送通知"]
            E2 --> E3["更新COMPLETED"]
        end
    end

    A2 --> T1
    T1 --> C1
    C1 --> B1
    B3 -->|HTTP POST| D1
    D2 --> T2
    T2 --> C2
    C2 --> E1

    style Layer1 fill:#e3f2fd
    style Layer2 fill:#e8f5e9
    style T1 fill:#f5f5f5
    style T2 fill:#f5f5f5
    style 外部 fill:#fff3e0
```

---

### PlantUML时序图输出

```plantuml
@startuml
autonumber
skinparam participantPadding 10
skinparam boxPadding 10

actor "用户" as 用户
participant "API网关" as 网关
box "业务服务" #LightBlue
    participant "用户服务" as 用户服务
    participant "流程服务" as 流程服务
end box
participant "认证服务" as 认证服务
database "数据库" as 数据库
queue "消息队列" as MQ

== 用户登录流程 ==
用户 -> 网关: 发起登录请求
网关 -> 用户服务: 转发登录请求
用户服务 -> 认证服务: 验证用户身份
activate 认证服务
认证服务 -> 数据库: 查询用户信息
数据库 --> 认证服务: 返回用户数据
deactivate 认证服务
认证服务 --> 用户服务: 返回验证结果
用户服务 --> 网关: 返回登录结果
网关 --> 用户: 登录成功

== 流程执行 ==
用户 -> 网关: 发起流程执行请求
网关 -> 流程服务: 转发执行请求
activate 流程服务
流程服务 -> MQ: 发布流程事件
流程服务 --> 网关: 返回执行结果
deactivate 流程服务
网关 --> 用户: 执行成功

@enduml
```

---

### Step 1: 判断入口类型

```
判断是网关还是业务服务：
- 入口点是 "服务名:gateway" 或 "服务名:/api路径" + 有网关配置 → 网关模式
- 其他 → 业务服务模式
```

### Step 2a: 网关模式

```
1. 确认网关代码路径
2. 检测网关类型
3. 读取路由配置文件
4. 解析所有路由规则
5. 输出路由表
6. 【关键】询问每个下游服务的路径：
   
   "发现下游服务: user-service, order-service, flow-service"
   "请输入 user-service 的代码路径 (skip跳过/quit退出):"
   
7. 对每个提供了路径的服务，进入Step 2b继续分析
```

### Step 2b: 业务服务模式

```
1. 确认服务代码路径
2. 定位入口文件
3. 分析方法体，识别调用
4. 对每个调用：
   - HTTP/RPC → 记录目标服务，询问路径，准备递归
   - MQ → 记录Topic，查找消费者
   - DB → 记录表和操作
```

### Step 3: 递归追踪

```
对每个外部服务调用：
1. 【必须】询问目标服务路径
   - 输入路径 → 继续
   - skip → 跳过该服务
   - quit → 结束
2. 进入目标服务
3. 定位处理方法
4. 重复Step 2b

对每个表驱动异步流程：
1. 分析下游流程代码
2. 识别下游流程中的外部服务调用
3. 【关键】发现外部服务时询问是否继续分析：
   
   "下游流程 task-service:TaskProcessor.process 调用了外部服务 notification-service"
   "是否继续追踪 notification-service? (输入路径/skip/quit)"
   
4. 识别下游流程是否写入另一个异步表
5. 【关键】发现嵌套异步表时询问是否继续：
   
   "下游流程写入了新的异步表: notification_queue"
   "是否继续分析 notification_queue 的消费流程? (输入路径/skip/quit)"

控制：
- 最大深度限制（默认5）
- 已访问检查（避免循环）
- 支持异步表嵌套追踪
```

### Step 4: 输出路径

```
将追踪结果输出为JSON格式
包含：
- 入口信息
- 节点列表
- 边列表
- 服务路径映射
```

### Step 5: 生成流程图

```
调用 drawio skill，根据JSON生成.drawio文件
```

### Step 6: 【强制】探索询问

```
分析完成后，【必须】询问用户是否继续探索：

════════════════════════════════════════════════════════
分析完成！是否继续探索？
════════════════════════════════════════════════════════

本次分析发现的路径:
• user-service → auth-service (HTTP)
• flow-service → process_task (异步表)
• task-service → notification-service (HTTP)

探索选项:
1. 分析其他入口点 (输入新的入口点)
2. 深入分析某个节点 (指定服务和方法)
3. 追踪未分析的下游服务 (选择发现但未追踪的服务)
4. 生成图表 (流程图/时序图)
5. 结束分析

请选择 (1/2/3/4/5):

如果用户选择继续探索：
- 选项1 → 返回 Step 1，开始新的追踪
- 选项2 → 输入具体节点 → Step 2b 深入分析
- 选项3 → 列出未追踪的服务 → 用户选择 → Step 3 递归追踪
- 选项4 → Step 5 生成图表 → 完成后再次询问是否继续
- 选项5 → 输出最终结果，结束

【关键】：每次生成图表后，【必须】再次询问是否继续探索，不能自动结束！
```

---

## 服务路径配置

在分析过程中，需要知道每个服务的代码路径。

### 方式一：运行时询问

首次发现新服务时，询问用户：

```
发现外部服务调用: auth-service
上下文: RestTemplate POST http://auth-service/api/verify

请输入 auth-service 的代码路径 (skip跳过, quit退出):
```

### 方式二：配置文件

预先配置服务路径：

```yaml
# ~/.agents/skills/flow-trace/config.yaml
repositories:
  user-service: /projects/user-service
  order-service: /projects/order-service
  payment-service: /projects/payment-service
```

---

## 调用drawio生成流程图

追踪完成后，使用drawio skill生成流程图：

```
/flow-trace user-service:UserController.login
```

输出JSON后，调用：

```
/drawio 根据以下JSON生成流程图：
{追踪路径JSON}
```

### 节点样式

| 节点类型 | 样式 |
|----------|------|
| service | 矩形，蓝色填充 |
| endpoint | 圆角矩形，黄色填充 |
| method | 圆角矩形，绿色填充 |
| http/rpc | 菱形，紫色填充 |
| mq | 平行四边形，橙色填充 |
| database | 圆柱形，灰色填充 |

### 边样式

| 边类型 | 样式 |
|--------|------|
| 调用 | 实线箭头 |
| HTTP | 虚线箭头，标注方法 |
| MQ | 虚线箭头，标注Topic |

---

## 示例对话

### 示例1：标准同步调用

```
用户: /flow-trace user-service:UserController.login

AI: 开始分析 user-service:UserController.login

请输入 user-service 的代码路径: /projects/user-service

正在分析 UserController.java...
找到端点: POST /api/login
  → 调用 UserService.login

正在分析 UserService.java...
  → HTTP调用: RestTemplate POST http://auth-service/api/verify

发现外部服务: auth-service
请输入 auth-service 的代码路径: /projects/auth-service

正在分析 AuthController.java...
找到端点: POST /api/verify
  → 调用 AuthService.verify

正在分析 AuthService.java...
  → 数据库调用: authMapper.findByToken

分析完成！

追踪路径:
┌─────────────────┐
│ user-service    │
│ UserController  │
│ .login()        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ UserService     │
│ .login()        │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│ auth-service    │
│ POST /api/verify│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AuthService     │
│ .verify()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MyBatis         │
│ findByToken     │
└─────────────────┘

是否生成流程图? (y/n): y

正在调用 drawio skill...
已生成: login-flow.drawio
```

---

## 网关使用示例

```
用户: /flow-trace edge-gateway:gateway

AI: 开始分析网关 edge-gateway

请输入 edge-gateway 的代码路径: /projects/edge-gateway

检测到网关类型: Spring Cloud Gateway
正在分析 src/main/resources/application.yml...

发现路由规则:
┌──────────────────┬─────────────────┐
│ 路径              │ 下游服务         │
├──────────────────┼─────────────────┤
│ /api/user/**     │ user-service    │
│ /api/order/**    │ order-service   │
│ /api/flow/**     │ flow-service    │
└──────────────────┴─────────────────┘

════════════════════════════════════════════════════════
发现下游服务: user-service, order-service, flow-service
════════════════════════════════════════════════════════

请输入 user-service 的代码路径 (skip跳过/quit退出): /projects/user-service

请输入 order-service 的代码路径 (skip跳过/quit退出): skip

请输入 flow-service 的代码路径 (skip跳过/quit退出): /projects/flow-service

──────────────────────────────────────────────────────────
正在追踪 user-service...
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
正在追踪 flow-service...
──────────────────────────────────────────────────────────
找到: /api/flow/execute → FlowController.execute
  → FlowService.execute
  → MQ: flow-events (Kafka)
  → RPC: rule-engine (Dubbo)

发现下游服务: rule-engine
请输入 rule-engine 的代码路径 (skip跳过/quit退出): skip

分析完成！

════════════════════════════════════════════════════════
追踪路径摘要
════════════════════════════════════════════════════════

┌─────────────────┐
│ edge-gateway    │
│ (Spring Gateway)│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ user  │ │ flow  │
│service│ │service│
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│ auth  │ │Kafka  │
│service│ │flow-ev│
└───┬───┘ └───────┘
    │
    ▼
 MyBatis

生成图表类型:
1. 流程图 (flowchart) - 展示调用层级关系
2. 时序图 (sequence) - 展示调用顺序和交互
3. 两者都生成

请选择 (1/2/3): 2

正在生成时序图...

```mermaid
sequenceDiagram
    participant Client
    participant GW as edge-gateway
    participant User as user-service
    participant Flow as flow-service
    participant Auth as auth-service
    participant DB as Database
    participant MQ as Kafka

    Client->>GW: POST /api/user/login
    GW->>User: 路由转发
    User->>Auth: HTTP POST /api/verify
    Auth->>DB: findByToken()
    DB-->>Auth: token记录
    Auth-->>User: 验证结果
    User-->>GW: 登录结果
    GW-->>Client: 200 OK
    
    Client->>GW: POST /api/flow/execute
    GW->>Flow: 路由转发
    Flow->>MQ: publish flow-events
    Flow-->>GW: 执行结果
    GW-->>Client: 200 OK
```

已生成: edge-gateway-sequence.drawio
```

---

### 示例3：多层异步流程 + 外部服务调用

```
用户: /flow-trace flow-service:FlowExecutor.execute

AI: 开始分析 flow-service:FlowExecutor.execute

请输入 flow-service 的代码路径: /projects/flow-service

正在分析 FlowExecutor.java...
找到: execute方法
  → 写入异步表: process_task
  → 状态字段: status

════════════════════════════════════════════════════════
检测到表驱动异步流程
════════════════════════════════════════════════════════
表名: process_task
状态字段: status
状态值: PENDING → PROCESSING → COMPLETED

请确认:
1. 下游流程是什么? (哪个服务消费表)
2. 触发机制? (定时任务/事件/手动)

请输入下游服务 task-service 的代码路径: /projects/task-service
触发机制: 定时任务每5分钟

──────────────────────────────────────────────────────────
正在分析下游流程 task-service:TaskProcessor.process...
──────────────────────────────────────────────────────────
找到: TaskProcessor.process
  → SELECT process_task WHERE status='PENDING'
  → 处理任务逻辑
  → HTTP调用: notification-service/api/send
  → 上下文: RestTemplate POST http://notification-service:8080/api/send

════════════════════════════════════════════════════════
发现外部服务: notification-service
════════════════════════════════════════════════════════

是否继续分析 notification-service?
请输入 notification-service 的代码路径 (skip跳过/quit退出): /projects/notification-service

──────────────────────────────────────────────────────────
正在分析 notification-service...
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

表名: notification_queue
状态字段: status
状态值: PENDING → COMPLETED → FAILED

是否继续分析 notification_queue 的下游流程?
请输入下游服务 notify-service 的代码路径 (skip跳过/quit退出): /projects/notify-service
触发机制: 事件监听(notification_queue_insert)

──────────────────────────────────────────────────────────
正在分析下游流程 notify-service:NotificationSender.send...
──────────────────────────────────────────────────────────
找到: NotificationSender.send
  → SELECT notification_queue WHERE status='PENDING'
  → 发送通知
  → UPDATE status='COMPLETED'

════════════════════════════════════════════════════════
分析完成！发现多层异步流程链
════════════════════════════════════════════════════════

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

追踪路径摘要:
- 涉及服务: flow-service, task-service, notification-service, notify-service
- 异步表: process_task, notification_queue
- 外部服务调用: task-service → notification-service (HTTP)

生成图表类型:
1. 流程图 (flowchart) - 展示调用层级关系
2. 时序图 (sequence) - 展示调用顺序和交互
3. 两者都生成

请选择 (1/2/3): 2

正在生成时序图...

```mermaid
sequenceDiagram
    autonumber
    actor 用户
    participant 上游 as flow-service
    participant DB1 as process_task表
    participant 定时1 as Scheduler
    participant 中游 as task-service
    participant 外部 as notification-service
    participant DB2 as notification_queue表
    participant 定时2 as EventListener
    participant 下游 as notify-service

    Note over 用户,上游: 阶段1: 创建处理任务
    用户->>上游: 发起流程请求
    上游->>DB1: INSERT status='PENDING'
    上游-->>用户: 返回任务ID

    Note over 定时1,中游: 阶段2: 异步处理任务
    定时1->>中游: 触发(每5分钟)
    中游->>DB1: SELECT status='PENDING'
    DB1-->>中游: 待处理任务
    中游->>DB1: UPDATE status='PROCESSING'
    
    Note over 中游,外部: 发现外部服务调用
    中游->>外部: HTTP POST /api/notify
    activate 外部
    外部->>DB2: INSERT status='PENDING'
    外部-->>中游: 返回成功
    deactivate 外部
    
    中游->>DB1: UPDATE status='COMPLETED'

    Note over 定时2,下游: 阶段3: 嵌套异步流程
    定时2->>下游: 事件触发
    下游->>DB2: SELECT status='PENDING'
    DB2-->>下游: 待发送通知
    下游->>下游: 发送通知
    下游->>DB2: UPDATE status='COMPLETED'

    Note over 用户,下游: 阶段4: 结果查询
    用户->>上游: 查询状态
    上游->>DB1: SELECT BY id
    DB1-->>上游: status='COMPLETED'
    上游-->>用户: 返回结果
```

已生成: async-flow-chain-sequence.drawio
```

════════════════════════════════════════════════════════
分析完成！是否继续探索？
════════════════════════════════════════════════════════

本次分析发现的路径:
• flow-service → process_task (异步表)
• task-service → notification-service (HTTP)
• notification-service → notification_queue (异步表)
• notify-service (终端节点)

探索选项:
1. 分析其他入口点 (输入新的入口点)
2. 深入分析某个节点 (指定服务和方法)
3. 追踪未分析的下游服务 (选择发现但未追踪的服务)
4. 生成图表 (流程图/时序图)
5. 结束分析

请选择 (1/2/3/4/5): 3

════════════════════════════════════════════════════════
未分析的下游服务
════════════════════════════════════════════════════════

本次分析中发现但未深入追踪的服务:
• rule-engine (flow-service → Dubbo调用，用户选择skip)
• auth-service (user-service → HTTP调用，未在本轮分析)

是否继续追踪这些服务? 选择一个服务名或输入路径:
(输入服务名如 'rule-engine' 或直接输入路径 /projects/rule-engine，skip全部跳过，quit退出)

请输入: rule-engine

请输入 rule-engine 的代码路径: /projects/rule-engine

──────────────────────────────────────────────────────────
正在追踪 rule-engine...
──────────────────────────────────────────────────────────
...
```

---

## 注意事项

1. **需要代码访问权限**：AI需要能读取服务的源代码
2. **最大深度**：默认5层，避免无限递归
3. **已访问检查**：避免循环调用导致的无限分析
4. **异步流程递归**：发现外部服务调用或嵌套异步表时，必须询问是否继续分析
5. **【强制】探索询问**：分析完成后必须询问用户是否继续探索，不能自动结束
6. **图表后继续询问**：生成图表后必须再次询问是否继续探索，不能自动结束
7. **不支持的调用**：
   - 反射调用
   - 动态代理
   - 运行时生成的代码

---

## 关键行为规则

### 必须执行的询问点

| 时机 | 询问内容 | 不能跳过 |
|------|----------|----------|
| 发现外部服务调用 | 是否继续追踪该服务？ | ✅ |
| 发现嵌套异步表 | 是否继续分析下游流程？ | ✅ |
| 单个服务分析完成 | 是否继续探索其他路径？ | ✅ |
| 生成图表后 | 是否继续探索？ | ✅ |
| 用户选择skip的服务 | 在探索询问时再次列出，询问是否追踪 | ✅ |

### 询问格式模板

**发现外部服务**：
```
发现外部服务: notification-service
是否继续追踪 notification-service?
请输入代码路径 (skip跳过/quit退出):
```

**分析完成**：
```
本次分析发现的路径:
• xxx-service → xxx (调用类型)

探索选项:
1. 分析其他入口点
2. 深入分析某个节点
3. 追踪未分析的下游服务
4. 生成图表
5. 结束分析

请选择 (1/2/3/4/5):
```

**生成图表后**：
```
已生成: xxx.drawio

是否继续探索?
• 可以追踪之前skip的服务
• 可以分析其他入口点
• 可以深入分析某个节点

请输入入口点或选择继续探索的选项 (quit退出):
```

---

*此skill让AI自己分析代码，不需要Python脚本，输出结构化JSON，调用drawio生成流程图*