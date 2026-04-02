---
name: flow-trace
description: 自动分析微服务调用链，生成业务流程图。输入入口点，动态追踪下游服务、数据库、消息队列，运行时询问未知服务路径，输出draw.io流程图。
---

# Flow Trace Skill (交互式版本)

自动分析Java微服务调用链，生成业务流程图。**无需预配置**，运行时动态询问未知服务路径。

## 使用方式

```bash
python ~/.agents/skills/flow-trace/scripts/trace_flow.py --entry "服务名:类名.方法名"
```

### 入口点格式

| 格式 | 说明 | 示例 |
|------|------|------|
| `服务名:类名.方法名` | 分析特定方法 | `user-service:UserController.login` |
| `服务名:/api路径` | 分析API端点 | `order-service:/api/orders/create` |
| `服务名:类名` | 分析整个类 | `payment-service:PaymentService` |

### 参数

| 参数 | 说明 | 必填 |
|------|------|------|
| `--entry, -e` | 入口点 | 是 |
| `--service-path, -p` | 入口服务路径 | 否（运行时询问） |
| `--output, -o` | 输出文件 | 否（默认flow-trace.drawio） |
| `--depth, -d` | 最大追踪深度 | 否（默认5） |

### 示例

```bash
# 最简单的用法（运行时询问路径）
python trace_flow.py -e "user-service:UserController.login"

# 指定入口服务路径
python trace_flow.py -e "user-service:UserController.login" -p /path/to/user-service

# 指定深度和输出
python trace_flow.py -e "order-service:/api/orders" -d 10 -o order-flow.drawio
```

## 运行流程

```
1. 输入入口点和初始服务路径

2. 分析入口服务代码
   ├── 解析Controller/Service
   ├── 追踪方法调用链
   └── 识别跨服务调用

3. 发现外部服务时
   ├── 打印调用信息
   └── 询问用户提供服务路径
       ├── 输入路径 → 继续分析
       ├── 输入 skip → 跳过该服务
       └── 输入 quit → 退出

4. 发现MQ时
   ├── 询问消费者服务名
   └── 询问消费者服务路径

5. 生成流程图
   └── 输出 .drawio 文件
```

## 示例交互

```
$ python trace_flow.py -e "user-service:UserController.login"

============================================================
🚀 开始追踪: user-service:UserController.login
============================================================
请输入 'user-service' 的代码路径: /projects/user-service

🚀 开始追踪: user-service:UserController.login
   服务路径: /projects/user-service
📦 分析服务: user-service (156 个Java文件)
  🎯 找到端点: POST /api/login
  🔗 HTTP调用: RestTemplate -> auth-service (POST http://auth-service/verify)
  
============================================================
🔍 发现外部服务调用: auth-service
   上下文: RestTemplate POST http://auth-service/verify
============================================================
请输入 'auth-service' 的代码路径 (输入 'skip' 跳过, 'quit' 退出): /projects/auth-service
✅ 已添加服务: auth-service -> /projects/auth-service

📦 分析服务: auth-service (89 个Java文件)
  🔗 Feign调用: UserClient -> user-service
  
============================================================
🔍 发现外部服务调用: user-service
   上下文: Feign: UserClient
============================================================
请输入 'user-service' 的代码路径: skip
跳过服务: user-service

  📨 MQ生产: Kafka -> user-events
  
============================================================
📨 发现MQ Topic: user-events (Kafka)
============================================================
请输入消费 'user-events' 的服务名: notification-service
请输入 'notification-service' 的代码路径: /projects/notification-service
✅ 已添加消费者: notification-service

  💾 数据库: MyBatis
  ⚡ Redis缓存

============================================================
✅ 分析完成!
   节点数: 12
   边数: 11
   输出文件: /path/to/flow-trace.drawio
============================================================

📊 发现的服务:
   - user-service: /projects/user-service
   - auth-service: /projects/auth-service
   - notification-service: /projects/notification-service
```

## 工作流程

```
1. 解析入口点
   └── 定位服务代码目录

2. Java代码分析
   ├── 解析入口类/方法
   ├── 追踪方法调用链
   └── 识别服务边界调用

3. 跨服务递归
   ├── HTTP调用 → 目标服务
   ├── RPC调用 → 目标服务
   └── MQ调用 → 消费者服务

4. 数据库层分析
   ├── MyBatis Mapper
   ├── JPA Repository
   └── JDBC Template

5. 流程图生成
   └── 输出 draw.io 文件
```

## 识别的调用模式

### HTTP调用

- `RestTemplate.getForObject()`
- `RestTemplate.postForObject()`
- `FeignClient` 接口调用
- `WebClient` 调用
- `OkHttp` / `HttpClient`

### RPC调用

- Dubbo `@Reference`
- gRPC Stub 调用
- Thrift RPC

### 消息队列

- Kafka `@KafkaListener`
- RabbitMQ `@RabbitListener`
- RocketMQ `@RocketMQMessageListener`
- ActiveMQ `@JmsListener`

### 数据库

- MyBatis `@Mapper`
- JPA `@Repository`
- JDBC `JdbcTemplate`
- Redis `RedisTemplate`

## 输出示例

生成的流程图包含：

1. **服务节点** - 矩形，标注服务名
2. **方法节点** - 圆角矩形，标注类.方法
3. **数据库节点** - 圆柱形，标注表名/操作
4. **MQ节点** - 平行四边形，标注Topic/Queue
5. **调用边** - 箭头，标注调用类型

## 配置

在 `~/.agents/skills/flow-trace/config.yaml` 配置服务仓库路径：

```yaml
# 服务仓库映射
repositories:
  user-service: /path/to/user-service
  order-service: /path/to/order-service
  payment-service: /path/to/payment-service

# 通用配置
settings:
  default_depth: 5
  default_format: drawio
  
  # 代码目录
  source_pattern: "src/main/java/**/*.java"
  
  # 资源目录（MyBatis XML等）
  resource_pattern: "src/main/resources/**/*.xml"
```

## 依赖

需要 Python 3.8+ 和以下库：

```bash
pip install javalang tree-sitter tree-sitter-java
```

## 注意事项

1. **多仓库需要配置路径映射**
   如果服务在不同仓库，需要在config.yaml中配置每个服务的代码路径。

2. **动态调用无法分析**
   反射调用、动态代理等运行时行为无法静态分析。

3. **配置文件解析**
   Spring配置文件中的服务URL会被解析用于定位目标服务。

4. **MQ消费者发现**
   需要扫描所有服务才能找到MQ消费者，建议预先配置服务列表。

---

## 实现

运行 `/flow-trace` 时，执行以下步骤：

1. **解析入口**：根据服务名找到代码目录，定位入口类/方法
2. **AST分析**：使用tree-sitter-java解析Java代码
3. **调用追踪**：递归分析方法体中的调用
4. **边界检测**：识别跨服务、数据库、MQ调用
5. **递归扩展**：对跨服务调用，加载目标服务代码继续分析
6. **图生成**：收集所有节点和边，生成draw.io XML

详见 `scripts/trace_flow.py`。