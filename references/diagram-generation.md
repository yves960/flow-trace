# 图表生成详细说明

## 支持的图表类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **时序图** | 展示调用顺序 | 分析单个API完整流程 |
| **流程图** | 展示调用层级 | 分析整体架构关系 |
| **依赖图** | 展示服务依赖 | 分析服务拓扑 |

## 时序图生成

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

## DrawIO时序图

调用drawio skill生成.drawio文件：

```
时序图节点:
- participant: 矩形，顶部排列
- lifeline: 垂直虚线
- message: 水平箭头
- activation: 矩形条（可选）
```

## 流程图生成

**Mermaid流程图**：

```mermaid
flowchart TB
    subgraph GW["API网关"]
        direction LR
        R1["/api/user/**"] --> S1["user-service"]
        R2["/api/order/**"] --> S2["order-service"]
    end

    subgraph Services["微服务集群"]
        S1 --> U1["用户管理"]
        S2 --> O1["订单处理"]
    end

    subgraph Infra["基础设施"]
        DB[(数据库)]
        MQ{{消息队列}}
    end

    U1 --> DB
    O1 --> MQ

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

## 描述转换规则

| 技术细节 | 业务描述 |
|----------|----------|
| `UserController.login` | 处理登录请求 |
| `UserService.login` | 执行登录逻辑 |
| `RestTemplate.post(url)` | 调用下游服务 |
| `authMapper.findByToken` | 查询认证信息 |
| `kafkaTemplate.send(topic)` | 发送消息到队列 |
| `POST /api/user/login` | 登录接口 |
| `GET /api/user/{id}` | 查询用户信息 |
| `Dubbo invoke xxx` | 调用RPC服务 |

## 描述生成原则

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

## 节点样式

| 节点类型 | 样式 |
|----------|------|
| service | 矩形，蓝色填充 |
| endpoint | 圆角矩形，黄色填充 |
| method | 圆角矩形，绿色填充 |
| http/rpc | 菱形，紫色填充 |
| mq | 平行四边形，橙色填充 |
| database | 圆柱形，灰色填充 |

## 边样式

| 边类型 | 样式 |
|--------|------|
| 调用 | 实线箭头 |
| HTTP | 虚线箭头，标注方法 |
| MQ | 虚线箭头，标注Topic |

## 调用drawio

追踪完成后，使用drawio skill生成流程图：

```
/flow-trace user-service:UserController.login
```

输出JSON后，调用：

```
/drawio 根据以下JSON生成流程图：
{追踪路径JSON}
```

## 时序图模板 - 异步流程

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
```

## 流程图模板 - 异步流程

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
```