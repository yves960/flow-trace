# 输出格式详细说明

## 追踪路径JSON

### 标准同步调用

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

### 多层异步流程链

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

## 节点类型

| type | 说明 | 图形 |
|------|------|------|
| `service` | 服务节点 | 矩形 |
| `endpoint` | API端点 | 圆角矩形 |
| `method` | 方法 | 圆角矩形 |
| `http` | HTTP调用 | 菱形 |
| `rpc` | RPC调用 | 菱形 |
| `mq` | 消息队列 | 平行四边形 |
| `database` | 数据库 | 圆柱 |

## 时序图数据格式

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
      }
    ]
  }
}
```

## 步骤类型

| type | 说明 | 时序图箭头 |
|------|------|-----------|
| `sync` | 同步调用 | 实线箭头 |
| `async` | 异步调用 | 虚线箭头 |
| `http` | HTTP请求 | 线+标注 |
| `rpc` | RPC调用 | 实线+标注 |
| `mq` | 消息发送 | 虚线+标注 |
| `db` | 数据库操作 | 实线+圆柱 |
| `return` | 返回 | 虚线箭头 |