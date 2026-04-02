#!/usr/bin/env python3
"""
Flow Trace - 微服务调用链分析工具 (交互式版本)

用法:
    python trace_flow.py --entry "user-service:UserController.login" --service-path /path/to/user-service

无需预配置，运行时动态询问未知服务的路径。
"""

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class NodeType(Enum):
    SERVICE = "service"
    ENDPOINT = "endpoint"
    METHOD = "method"
    DATABASE = "database"
    MQ = "mq"
    CACHE = "cache"


@dataclass
class Node:
    id: str
    name: str
    type: NodeType
    service: str
    detail: str = ""


@dataclass
class Edge:
    source: str
    target: str
    label: str = ""


class InteractiveFlowTracer:
    """交互式微服务调用链追踪器"""
    
    def __init__(self, initial_service: str, initial_path: str, max_depth: int = 5):
        self.services = {initial_service: initial_path}
        self.max_depth = max_depth
        self.nodes = {}
        self.edges = []
        self.visited = set()
        self.asked_services = set()  # 已询问过的服务
        
    def ask_service_path(self, service_name: str, context: str = "") -> Optional[str]:
        """询问用户服务路径"""
        if service_name in self.asked_services:
            return None  # 已经问过了，用户可能不知道
        
        self.asked_services.add(service_name)
        
        print(f"\n{'='*60}")
        print(f"🔍 发现外部服务调用: {service_name}")
        if context:
            print(f"   上下文: {context}")
        print(f"{'='*60}")
        
        while True:
            try:
                path = input(f"请输入 '{service_name}' 的代码路径 (输入 'skip' 跳过, 'quit' 退出): ").strip()
                
                if path.lower() == 'quit':
                    print("退出追踪...")
                    sys.exit(0)
                
                if path.lower() == 'skip':
                    print(f"跳过服务: {service_name}")
                    return None
                
                path_obj = Path(path)
                if not path_obj.exists():
                    print(f"❌ 路径不存在: {path}")
                    retry = input("重试? (y/n): ").strip().lower()
                    if retry != 'y':
                        return None
                    continue
                
                # 验证是否是Java项目
                java_dir = path_obj / "src" / "main" / "java"
                if not java_dir.exists():
                    print(f"⚠️  警告: 未找到 src/main/java 目录，可能不是标准Java项目")
                    proceed = input("继续使用此路径? (y/n): ").strip().lower()
                    if proceed != 'y':
                        continue
                
                print(f"✅ 已添加服务: {service_name} -> {path}")
                return path
                
            except KeyboardInterrupt:
                print("\n已取消")
                return None
    
    def trace(self, entry: str) -> tuple[dict, list]:
        """追踪入口点"""
        if ':' not in entry:
            raise ValueError(f"Invalid entry: {entry}. Format: service:Class.method")
        
        service, method_ref = entry.split(':', 1)
        
        if service not in self.services:
            path = self.ask_service_path(service)
            if path:
                self.services[service] = path
            else:
                raise ValueError(f"无法获取服务路径: {service}")
        
        # 创建服务节点
        self._add_node(Node(
            id=f"svc:{service}",
            name=service,
            type=NodeType.SERVICE,
            service=service,
        ))
        
        print(f"\n🚀 开始追踪: {entry}")
        print(f"   服务路径: {self.services[service]}")
        
        # 开始追踪
        self._trace_service(service, method_ref, depth=0)
        
        return self.nodes, self.edges
    
    def _get_java_files(self, service: str) -> list:
        """获取服务的Java文件列表"""
        if service not in self.services:
            return []
        
        service_path = Path(self.services[service])
        java_dir = service_path / "src" / "main" / "java"
        
        if java_dir.exists():
            return list(java_dir.glob("**/*.java"))
        
        # 回退到根目录搜索
        return list(service_path.glob("**/*.java"))
    
    def _trace_service(self, service: str, method_ref: str, depth: int):
        """追踪服务"""
        if depth > self.max_depth:
            print(f"{'  '*depth}⚠️ 达到最大深度 {self.max_depth}，停止追踪")
            return
        
        key = f"{service}:{method_ref}"
        if key in self.visited:
            return
        self.visited.add(key)
        
        java_files = self._get_java_files(service)
        if not java_files:
            print(f"{'  '*depth}⚠️ 未找到Java文件: {service}")
            return
        
        print(f"{'  '*depth}📦 分析服务: {service} ({len(java_files)} 个Java文件)")
        
        # 解析入口
        if method_ref.startswith('/'):
            self._trace_api(service, java_files, method_ref, depth)
        elif '.' in method_ref:
            class_name, method_name = method_ref.split('.', 1) if '.' in method_ref else (method_ref, None)
            self._trace_class(service, java_files, class_name, method_name, depth)
        elif method_ref == '*':
            # 分析所有Controller
            self._trace_all_controllers(service, java_files, depth)
        else:
            self._trace_class(service, java_files, method_ref, None, depth)
    
    def _trace_all_controllers(self, service: str, java_files: list, depth: int):
        """分析所有Controller"""
        for java_file in java_files:
            content = java_file.read_text(encoding='utf-8', errors='ignore')
            if '@RestController' in content or '@Controller' in content:
                class_match = re.search(r'class\s+(\w+)', content)
                if class_match:
                    self._trace_class(service, java_files, class_match.group(1), None, depth)
    
    def _trace_api(self, service: str, java_files: list, path: str, depth: int):
        """追踪API路径"""
        for java_file in java_files:
            content = java_file.read_text(encoding='utf-8', errors='ignore')
            
            if '@RestController' not in content and '@Controller' not in content:
                continue
            
            base_path = ""
            base_match = re.search(r'@RequestMapping\s*\([^)]*["\']([^"\']+)["\']', content)
            if base_match:
                base_path = base_match.group(1)
            
            pattern = r'@(Get|Post|Put|Delete|Patch)Mapping\s*\([^)]*["\']([^"\']+)["\']'
            for match in re.finditer(pattern, content):
                http_method = match.group(1).upper()
                endpoint_path = base_path + match.group(2)
                
                if path == endpoint_path or endpoint_path.startswith(path.rstrip('*')):
                    after = content[match.end():match.end()+300]
                    method_match = re.search(r'public\s+\w+(?:<[^>]+>)?\s+(\w+)\s*\(', after)
                    method_name = method_match.group(1) if method_match else "handle"
                    
                    class_match = re.search(r'class\s+(\w+)', content)
                    class_name = class_match.group(1) if class_match else java_file.stem
                    
                    node = Node(
                        id=f"ep:{service}:{endpoint_path}",
                        name=f"{http_method} {endpoint_path}",
                        type=NodeType.ENDPOINT,
                        service=service,
                        detail=f"{class_name}.{method_name}",
                    )
                    self._add_node(node)
                    self._add_edge(f"svc:{service}", node.id, http_method)
                    
                    print(f"{'  '*(depth+1)}🎯 找到端点: {http_method} {endpoint_path}")
                    
                    self._trace_method(service, java_files, content, class_name, method_name, depth + 1)
    
    def _trace_class(self, service: str, java_files: list, class_name: str, method_name: Optional[str], depth: int):
        """追踪类"""
        for java_file in java_files:
            if java_file.stem == class_name or java_file.name.endswith(f"{class_name}.java"):
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                self._trace_method(service, java_files, content, class_name, method_name, depth)
                return
        
        print(f"{'  '*depth}⚠️ 未找到类: {class_name}")
    
    def _trace_method(self, service: str, java_files: list, content: str, class_name: str, method_name: Optional[str], depth: int):
        """追踪方法"""
        if method_name:
            pattern = rf'public\s+\w+(?:<[^>]+>)?\s+{method_name}\s*\([^)]*\)\s*\{{'
            match = re.search(pattern, content)
            if not match:
                return
            
            method_content = self._extract_method_body(content, match.end())
            self._analyze_method_body(service, class_name, method_name, method_content, content, depth)
        else:
            pattern = r'public\s+\w+(?:<[^>]+>)?\s+(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(pattern, content):
                m_name = match.group(1)
                if m_name in ['get', 'set', 'toString', 'hashCode', 'equals', 'clone']:
                    continue
                method_content = self._extract_method_body(content, match.end())
                self._analyze_method_body(service, class_name, m_name, method_content, content, depth)
    
    def _extract_method_body(self, content: str, start: int) -> str:
        """提取方法体"""
        brace_count = 1
        end = start
        while brace_count > 0 and end < len(content):
            if content[end] == '{':
                brace_count += 1
            elif content[end] == '}':
                brace_count -= 1
            end += 1
        return content[start:end-1]
    
    def _analyze_method_body(self, service: str, class_name: str, method_name: str, body: str, class_content: str, depth: int):
        """分析方法体"""
        node_id = f"method:{service}:{class_name}.{method_name}"
        self._add_node(Node(
            id=node_id,
            name=f"{class_name}.{method_name}",
            type=NodeType.METHOD,
            service=service,
        ))
        self._add_edge(f"svc:{service}", node_id)
        
        # HTTP调用
        self._find_http_calls(service, node_id, body, depth)
        
        # Feign调用
        self._find_feign_calls(service, node_id, class_content, body, depth)
        
        # MQ调用
        self._find_mq_calls(service, node_id, body)
        
        # 数据库调用
        self._find_db_calls(service, node_id, body)
        
        # Redis调用
        self._find_redis_calls(service, node_id, body)
    
    def _find_http_calls(self, service: str, source: str, body: str, depth: int):
        """查找HTTP调用"""
        patterns = [
            (r'restTemplate\.(get|post|put|delete)\w*\s*\(\s*["\']([^"\']+)["\']', 'RestTemplate'),
            (r'webClient\.(get|post|put|delete)\(\).*\.uri\(\s*["\']([^"\']+)["\']', 'WebClient'),
        ]
        
        found_services = set()
        
        for pattern, client in patterns:
            for match in re.finditer(pattern, body, re.DOTALL):
                http_method = match.group(1).upper()
                url = match.group(2)
                
                target_service = self._extract_service_from_url(url)
                
                if target_service and target_service not in found_services:
                    found_services.add(target_service)
                    
                    print(f"{'  '*(depth+1)}🔗 HTTP调用: {client} -> {target_service} ({http_method} {url})")
                    
                    # 检查是否已有路径
                    if target_service not in self.services:
                        path = self.ask_service_path(target_service, f"{client} {http_method} {url}")
                        if path:
                            self.services[target_service] = path
                    
                    if target_service in self.services:
                        target_id = f"svc:{target_service}"
                        self._add_node(Node(
                            id=target_id,
                            name=target_service,
                            type=NodeType.SERVICE,
                            service=target_service,
                        ))
                        self._add_edge(source, target_id, f"{client}:{http_method}")
                        
                        if depth < self.max_depth:
                            self._trace_service(target_service, "*", depth + 1)
    
    def _find_feign_calls(self, service: str, source: str, class_content: str, body: str, depth: int):
        """查找Feign调用"""
        # 查找Feign接口
        feign_pattern = r'@FeignClient\s*\([^)]*(?:name|value)\s*=\s*["\']([^"\']+)["\']'
        feign_clients = {}
        
        # 扫描当前服务的所有Feign接口
        java_files = self._get_java_files(service)
        for java_file in java_files:
            content = java_file.read_text(encoding='utf-8', errors='ignore')
            match = re.search(feign_pattern, content)
            if match:
                feign_clients[java_file.stem] = match.group(1)
        
        # 查找方法体中的调用
        for client_name, target_service in feign_clients.items():
            pattern = rf'{client_name}\.\w+\s*\('
            if re.search(pattern, body):
                print(f"{'  '*(depth+1)}🔗 Feign调用: {client_name} -> {target_service}")
                
                if target_service not in self.services:
                    path = self.ask_service_path(target_service, f"Feign: {client_name}")
                    if path:
                        self.services[target_service] = path
                
                if target_service in self.services:
                    target_id = f"svc:{target_service}"
                    self._add_node(Node(
                        id=target_id,
                        name=target_service,
                        type=NodeType.SERVICE,
                        service=target_service,
                    ))
                    self._add_edge(source, target_id, "Feign")
                    
                    if depth < self.max_depth:
                        self._trace_service(target_service, "*", depth + 1)
    
    def _find_mq_calls(self, service: str, source: str, body: str):
        """查找MQ调用"""
        patterns = [
            (r'kafkaTemplate\.send\s*\(\s*["\']([^"\']+)["\']', 'Kafka'),
            (r'rabbitTemplate\.convertAndSend\s*\(\s*["\']([^"\']+)["\']', 'RabbitMQ'),
            (r'rocketMQTemplate\.\w+Send\s*\(\s*["\']([^"\']+)["\']', 'RocketMQ'),
        ]
        
        for pattern, mq_type in patterns:
            for match in re.finditer(pattern, body):
                topic = match.group(1)
                
                mq_id = f"mq:{topic}"
                self._add_node(Node(
                    id=mq_id,
                    name=topic,
                    type=NodeType.MQ,
                    service=mq_type,
                    detail=f"{mq_type} Topic",
                ))
                self._add_edge(source, mq_id, mq_type)
                
                print(f"{'  '*3}📨 MQ生产: {mq_type} -> {topic}")
                
                # 询问消费者服务
                self._find_mq_consumer(topic, mq_type)
    
    def _find_mq_consumer(self, topic: str, mq_type: str):
        """查找MQ消费者"""
        # 询问用户消费者服务
        print(f"\n{'='*60}")
        print(f"📨 发现MQ Topic: {topic} ({mq_type})")
        print(f"{'='*60}")
        
        while True:
            consumer = input(f"请输入消费 '{topic}' 的服务名 (输入 'done' 结束): ").strip()
            
            if consumer.lower() == 'done' or not consumer:
                break
            
            if consumer not in self.services:
                path = self.ask_service_path(consumer, f"{mq_type} Consumer of {topic}")
                if not path:
                    continue
            
            if consumer in self.services:
                consumer_id = f"consumer:{consumer}:{topic}"
                self._add_node(Node(
                    id=consumer_id,
                    name=f"{consumer}",
                    type=NodeType.METHOD,
                    service=consumer,
                    detail=f"{mq_type} Consumer",
                ))
                self._add_edge(f"mq:{topic}", consumer_id, "consume")
                
                print(f"✅ 已添加消费者: {consumer}")
    
    def _find_db_calls(self, service: str, source: str, body: str):
        """查找数据库调用"""
        patterns = [
            (r'\w+Mapper\.\w+\s*\(', 'MyBatis'),
            (r'\w+Repository\.\w+\s*\(', 'JPA'),
            (r'jdbcTemplate\.\w+\s*\(', 'JDBC'),
            (r'mongoTemplate\.\w+\s*\(', 'MongoDB'),
        ]
        
        found = set()
        for pattern, db_type in patterns:
            for match in re.finditer(pattern, body):
                if db_type not in found:
                    found.add(db_type)
                    db_id = f"db:{service}:{db_type}"
                    self._add_node(Node(
                        id=db_id,
                        name=db_type,
                        type=NodeType.DATABASE,
                        service=service,
                        detail=f"Database ({db_type})",
                    ))
                    self._add_edge(source, db_id, db_type)
                    print(f"{'  '*3}💾 数据库: {db_type}")
    
    def _find_redis_calls(self, service: str, source: str, body: str):
        """查找Redis调用"""
        patterns = [
            r'redisTemplate\.\w+',
            r'stringRedisTemplate\.\w+',
            r'@Cacheable|@CachePut|@CacheEvict',
        ]
        
        for pattern in patterns:
            if re.search(pattern, body):
                redis_id = f"redis:{service}"
                self._add_node(Node(
                    id=redis_id,
                    name="Redis",
                    type=NodeType.CACHE,
                    service=service,
                ))
                self._add_edge(source, redis_id, "Redis")
                print(f"{'  '*3}⚡ Redis缓存")
                break
    
    def _extract_service_from_url(self, url: str) -> Optional[str]:
        """从URL提取服务名"""
        if '://' in url:
            url = url.split('://', 1)[1]
        
        # 常见模式
        patterns = [
            r'/api/(\w+)',
            r'/(\w+)-service',
            r'/(\w+)/api',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                name = match.group(1)
                # 过滤通用词
                if name not in ['api', 'v1', 'v2', 'public', 'internal']:
                    return name
        
        return None
    
    def _add_node(self, node: Node):
        if node.id not in self.nodes:
            self.nodes[node.id] = node
    
    def _add_edge(self, source: str, target: str, label: str = ""):
        if not any(e.source == source and e.target == target for e in self.edges):
            self.edges.append(Edge(source=source, target=target, label=label))


def generate_drawio(nodes: dict, edges: list, title: str = "Flow Trace") -> str:
    """生成DrawIO XML"""
    
    colors = {
        NodeType.SERVICE: ("#DAE8FC", "#6C8EBF"),
        NodeType.ENDPOINT: ("#FFF2CC", "#D6B656"),
        NodeType.METHOD: ("#D5E8D4", "#82B366"),
        NodeType.DATABASE: ("#F5F5F5", "#666666"),
        NodeType.MQ: ("#E1D5E7", "#9673A6"),
        NodeType.CACHE: ("#F8CECC", "#B85450"),
    }
    
    # 自动布局
    layout = {}
    y_positions = {NodeType.SERVICE: 50, NodeType.ENDPOINT: 150, NodeType.METHOD: 250, NodeType.MQ: 400, NodeType.DATABASE: 500, NodeType.CACHE: 500}
    counters = {}
    
    for node in nodes.values():
        t = node.type
        if t not in counters:
            counters[t] = 0
        layout[node.id] = (100 + counters[t] * 180, y_positions.get(t, 300))
        counters[t] += 1
    
    xml = [
        '<mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageWidth="1169" pageHeight="827">',
        '<root>',
        '<mxCell id="0"/>',
        '<mxCell id="1" parent="0"/>',
        f'<mxCell id="title" value="{title}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=18;fontStyle=1" vertex="1" parent="1"><mxGeometry x="400" y="10" width="200" height="30" as="geometry"/></mxCell>',
    ]
    
    for node_id, node in nodes.items():
        pos = layout.get(node_id, (0, 0))
        fill, stroke = colors.get(node.type, ("#FFFFFF", "#000000"))
        
        if node.type == NodeType.DATABASE:
            style = f"shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor={fill};strokeColor={stroke};"
            w, h = 80, 80
        elif node.type == NodeType.MQ:
            style = f"shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor={fill};strokeColor={stroke};"
            w, h = 120, 50
        elif node.type == NodeType.SERVICE:
            style = f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontStyle=1;fontSize=14;"
            w, h = 140, 50
        else:
            style = f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            w, h = 140, 40
        
        value = node.name
        if node.detail:
            value = f"{node.name}<br/><font size='1'>{node.detail}</font>"
        
        xml.append(f'<mxCell id="n{node_id}" value="{value}" style="{style}" vertex="1" parent="1"><mxGeometry x="{pos[0]}" y="{pos[1]}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    
    for i, edge in enumerate(edges):
        style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
        xml.append(f'<mxCell id="e{i}" value="{edge.label}" style="{style}" edge="1" parent="1" source="n{edge.source}" target="n{edge.target}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    
    xml.extend(['</root>', '</mxGraphModel>'])
    return '\n'.join(xml)


def main():
    parser = argparse.ArgumentParser(description='交互式微服务调用链追踪')
    parser.add_argument('--entry', '-e', required=True, help='入口点: service:Class.method 或 service:/api/path')
    parser.add_argument('--service-path', '-p', help='入口服务的代码路径（可选，运行时会询问）')
    parser.add_argument('--output', '-o', default='flow-trace.drawio', help='输出文件')
    parser.add_argument('--depth', '-d', type=int, default=5, help='最大追踪深度')
    
    args = parser.parse_args()
    
    # 解析入口服务
    if ':' not in args.entry:
        print("❌ 入口格式错误。格式: service:Class.method 或 service:/api/path")
        sys.exit(1)
    
    service = args.entry.split(':', 1)[0]
    
    # 获取入口服务路径
    service_path = args.service_path
    if not service_path:
        print(f"\n{'='*60}")
        print(f"🚀 开始追踪: {args.entry}")
        print(f"{'='*60}")
        service_path = input(f"请输入 '{service}' 的代码路径: ").strip()
    
    if not Path(service_path).exists():
        print(f"❌ 路径不存在: {service_path}")
        sys.exit(1)
    
    # 开始追踪
    tracer = InteractiveFlowTracer(
        initial_service=service,
        initial_path=service_path,
        max_depth=args.depth,
    )
    
    nodes, edges = tracer.trace(args.entry)
    
    # 生成流程图
    xml = generate_drawio(nodes, edges, title=f"Flow: {args.entry}")
    Path(args.output).write_text(xml)
    
    print(f"\n{'='*60}")
    print(f"✅ 分析完成!")
    print(f"   节点数: {len(nodes)}")
    print(f"   边数: {len(edges)}")
    print(f"   输出文件: {Path(args.output).absolute()}")
    print(f"{'='*60}")
    
    # 列出发现的服务
    print(f"\n📊 发现的服务:")
    for svc, path in tracer.services.items():
        print(f"   - {svc}: {path}")


if __name__ == '__main__':
    main()