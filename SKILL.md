---
name: flow-trace
description: 分析Java微服务调用链，输出追踪路径，生成业务流程图。输入入口点，AI自动分析代码，识别HTTP/RPC/MQ/DB调用，输出JSON路径，调用drawio生成流程图。
---

# Flow Trace Skill

AI驱动的Java微服务调用链分析。

## 使用方式

```
/flow-trace <入口点> [选项]
```

### 入口点格式

| 格式 | 示例 |
|------|------|
| `服务名:类名.方法名` | `user-service:UserController.login` |
| `服务名:/api路径` | `order-service:/api/orders/create` |
| `服务名:类名` | `payment-service:PaymentService` |

### 选项

| 选项 | 说明 |
|------|------|
| `--depth N` | 追踪深度，默认5 |
| `--output FILE` | 输出文件名 |

### 示例

```
/flow-trace user-service:UserController.login
/flow-trace order-service:/api/orders --depth 10
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

---

## 输出格式

### 追踪路径JSON

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

---

## 执行步骤

### Step 1: 解析入口

```
1. 确认服务代码路径
   - 如果已知路径，直接使用
   - 如果未知，询问用户

2. 定位入口文件
   - 类名.方法名 → 搜索对应Java文件
   - API路径 → 搜索Controller中的映射
```

### Step 2: 分析代码

```
1. 读取入口文件
2. 定位目标方法
3. 分析方法体，识别调用
4. 对每个调用：
   - HTTP/RPC → 记录目标服务，准备递归
   - MQ → 记录Topic，查找消费者
   - DB → 记录表和操作
```

### Step 3: 递归追踪

```
对每个外部服务调用：
1. 询问/确认目标服务路径
2. 进入目标服务
3. 定位处理方法
4. 重复Step 2

控制：
- 最大深度限制（默认5）
- 已访问检查（避免循环）
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

## 注意事项

1. **需要代码访问权限**：AI需要能读取服务的源代码
2. **最大深度**：默认5层，避免无限递归
3. **已访问检查**：避免循环调用导致的无限分析
4. **不支持的调用**：
   - 反射调用
   - 动态代理
   - 运行时生成的代码

---

*此skill让AI自己分析代码，不需要Python脚本，输出结构化JSON，调用drawio生成流程图*