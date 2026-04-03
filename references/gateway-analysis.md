# 网关分析详细说明

边缘网关是API入口，通过配置文件定义路由规则，不写业务代码。

## 支持的网关类型

| 网关 | 配置文件 | 识别方式 |
|------|----------|----------|
| Spring Cloud Gateway | `application.yml` / `RouteDefinition` | Java配置或YAML |
| Kong | `kong.yml` / Admin API | YAML/JSON |
| APISIX | `apisix.yaml` / Admin API | YAML |
| Nginx | `nginx.conf` | 配置文件 |
| Envoy | `envoy.yaml` | YAML |

## 网关分析流程

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

## 网关分析关键点

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

## Spring Cloud Gateway 配置分析

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

## Kong 配置分析

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

## APISIX 配置分析

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

## Nginx 配置分析

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

## 网关输出格式

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