#!/usr/bin/env python3
"""
flow-trace 流程记录脚本

用于跨微服务调用链分析过程中持久化每个服务的分析结果，
解决长对话中模型遗忘问题。

用法:
    python flow_trace_record.py save <service> <entry> <json_result>           # 保存服务分析结果
    python flow_trace_record.py save --file <service> <entry> <file_path>      # 从文件读取结果保存
    python flow_trace_record.py list                                           # 列出所有已分析服务
    python flow_trace_record.py get <service>                                  # 获取某个服务的结果
    python flow_trace_record.py summary                                        # 汇总所有服务流程
    python flow_trace_record.py clear                                          # 清空记录
    python flow_trace_record.py context                                        # 输出关键上下文prompt
    python flow_trace_record.py config                                         # 显示配置的服务路径
"""

import json
import os
import re
import sys
import yaml
from pathlib import Path
from datetime import datetime

# 记录存储路径
RECORD_DIR = Path.home() / ".flow-trace-records"
# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"


def load_config():
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️ 配置文件读取失败: {e}")
        return {}


def get_configured_services():
    """获取已配置的服务路径"""
    config = load_config()
    repositories = config.get("repositories") or {}
    # 过滤掉空值和注释
    return {k: v for k, v in repositories.items() if v and not str(v).startswith("#")}


def show_config():
    """显示配置的服务路径"""
    services = get_configured_services()
    
    print("\n" + "=" * 60)
    print("📁 已配置的服务路径")
    print("=" * 60)
    
    if not services:
        print("\n⚠️ 未在 config.yaml 中配置任何服务路径")
        print(f"   配置文件: {CONFIG_FILE}")
        print("\n   配置示例:")
        print("   repositories:")
        print("     user-service: /path/to/user-service")
        print("     order-service: /path/to/order-service")
    else:
        print(f"\n已配置 {len(services)} 个服务:\n")
        for service, path in services.items():
            exists = "✅" if Path(path).exists() else "❌"
            print(f"  {exists} {service}: {path}")
        
        # 检查路径是否存在
        missing = [s for s, p in services.items() if not Path(p).exists()]
        if missing:
            print(f"\n⚠️ 以下服务路径不存在: {', '.join(missing)}")


def ensure_dir():
    """确保存储目录存在"""
    RECORD_DIR.mkdir(parents=True, exist_ok=True)


def validate_service_name(name: str) -> str:
    """验证服务名，防止路径遍历"""
    if not name or not re.match(r'^[a-zA-Z0-9_\-.]+$', name):
        raise ValueError(f"无效的服务名: {name!r} (仅允许字母、数字、_-.)")
    if '..' in name or '/' in name or '\\' in name:
        raise ValueError(f"服务名包含非法字符: {name!r}")
    return name


def save_record(service: str, entry: str, result_raw: str):
    """保存服务分析结果（直接保存原始输出）"""
    try:
        validate_service_name(service)
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    ensure_dir()
    
    record = {
        "service": service,
        "entry": entry,
        "result_raw": result_raw,  # 直接保存原始输出
        "timestamp": datetime.now().isoformat()
    }
    
    record_file = RECORD_DIR / f"{service}.json"
    try:
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"❌ 保存失败: {e}")
        return
    
    print(f"✅ 已保存服务 [{service}] 的分析结果")
    print(f"   入口点: {entry}")
    print(f"   文件: {record_file}")
    
    # 🛑 强制输出询问菜单
    print("\n" + "=" * 60)
    print("🛑 分析完成！现在必须展示询问菜单！")
    print("=" * 60)
    print("""
════════════════════════════════════════════════════════
📍 请选择下一步操作：
════════════════════════════════════════════════════════

1. 分析其他入口点
2. 深入分析某个节点
3. 追踪未分析的下游服务
4. 补充遗漏的异步链路
5. 配置/更新服务目录
6. 结束探索，生成图表
7. 仅输出JSON，不生成图表

请选择 (1/2/3/4/5/6/7):
""")


def list_records():
    """列出所有已分析的服务"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("📝 暂无已分析的服务记录")
        return
    
    print(f"\n📝 已分析的服务 ({len(records)} 个):")
    print("=" * 50)
    
    services_info = []
    for record_file in sorted(records):
        try:
            with open(record_file, encoding="utf-8") as f:
                record = json.load(f)
            service = record.get("service", record_file.stem)
            entry = record.get("entry", "未知")
            timestamp = record.get("timestamp", "")
            downstream = extract_downstream(record.get("result_raw", ""))
            services_info.append({
                "service": service,
                "entry": entry,
                "downstream": downstream,
                "timestamp": timestamp
            })
            print(f"  • {service}")
            print(f"    入口: {entry}")
            if downstream:
                print(f"    下游: {', '.join(downstream)}")
            print()
        except Exception as e:
            print(f"  • {record_file.stem} (读取失败: {e})")
    
    # 输出服务关系摘要
    print("=" * 50)
    print("🔗 服务调用关系:")
    all_services = set()
    all_downstream = set()
    for info in services_info:
        all_services.add(info["service"])
        all_downstream.update(info["downstream"])
    
    unanalyzed = all_downstream - all_services
    if unanalyzed:
        print(f"  ⚠️ 未分析的服务: {', '.join(sorted(unanalyzed))}")


def get_record(service: str):
    """获取某个服务的分析结果"""
    ensure_dir()
    
    record_file = RECORD_DIR / f"{service}.json"
    if not record_file.exists():
        print(f"❌ 服务 [{service}] 的记录不存在")
        return
    
    try:
        with open(record_file, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ 读取失败: {e}")
        return
    
    print(f"\n📋 服务 [{service}] 分析结果:")
    print("=" * 60)
    print(f"入口点: {record.get('entry')}")
    print(f"时间: {record.get('timestamp')}")
    print("\n分析结果（原始输出）:")
    print("=" * 60)
    print(record.get("result_raw", "无内容"))


def summary():
    """汇总所有服务的流程（直接输出所有原始内容给模型）"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("❌ 暂无已分析的服务记录，无法汇总")
        return
    
    print("\n" + "=" * 60)
    print("📊 跨微服务调用链汇总")
    print("=" * 60)
    
    # 输出所有服务的原始分析结果
    for record_file in sorted(records):
        try:
            with open(record_file, encoding="utf-8") as f:
                record = json.load(f)
            
            service = record.get("service")
            entry = record.get("entry")
            result_raw = record.get("result_raw", "")
            
            print(f"\n{'='*60}")
            print(f"服务: {service}")
            print(f"入口点: {entry}")
            print(f"{'='*60}")
            print(result_raw)
        except Exception as e:
            print(f"\n⚠️ 读取 {record_file.stem} 失败: {e}")
    
    print("\n" + "=" * 60)
    print("以上是所有已分析服务的原始结果")
    print("请根据这些内容生成最终的调用链图表")
    print("=" * 60)


def extract_downstream(result_raw) -> list:
    """从原始分析文本中提取下游服务列表"""
    downstream = set()
    
    text = result_raw if isinstance(result_raw, str) else ""
    if not text:
        # 兼容旧格式：如果是 dict，尝试旧的递归提取
        if isinstance(result_raw, dict):
            return _extract_downstream_from_dict(result_raw)
        return sorted(downstream)
    
    # 匹配 "下游服务:" 或 "downstream:" 后面的服务名列表
    m = re.search(r'(?:下游服务|downstream)[：:]\s*(.+)', text, re.IGNORECASE)
    if m:
        names = re.split(r'[,，、\s]+', m.group(1).strip())
        downstream.update(n.strip() for n in names if n.strip())
    
    # 匹配 "→ 服务名" 模式
    arrows = re.findall(r'→\s*([a-zA-Z0-9_\-.]+)', text)
    downstream.update(arrows)
    
    # 匹配 "调用 xxx-service" / "请求 xxx-service" 模式
    calls = re.findall(r'(?:调用|请求|调用服务|请求服务|call|invoke)\s+([a-zA-Z0-9_\-.]+(?:-service)?)', text, re.IGNORECASE)
    downstream.update(calls)
    
    return sorted(downstream)


def _extract_downstream_from_dict(obj: dict) -> list:
    """旧格式兼容：从 dict 结构中递归提取下游服务"""
    downstream = set()
    
    def _extract(o):
        if isinstance(o, dict):
            for key in ("service", "target_service", "downstream"):
                if key in o:
                    v = o[key]
                    if isinstance(v, list):
                        downstream.update(v)
                    elif isinstance(v, str):
                        downstream.add(v)
            for v in o.values():
                _extract(v)
        elif isinstance(o, list):
            for item in o:
                _extract(item)
    
    _extract(obj)
    return sorted(downstream)


def extract_calls(result_raw) -> list:
    """从分析结果中提取调用链"""
    calls = []
    
    # 如果是旧格式 dict，保持兼容
    if isinstance(result_raw, dict):
        obj = result_raw
    elif isinstance(result_raw, str):
        return calls  # 文本格式暂不提取结构化调用链
    else:
        return calls
    
    def _extract(obj, path=""):
        if isinstance(obj, dict):
            call_info = {}
            if "service" in obj:
                call_info["from"] = obj.get("service")
            if "target_service" in obj:
                call_info["to"] = obj["target_service"]
            if "type" in obj:
                call_info["type"] = obj["type"]
            if "method" in obj:
                call_info["method"] = obj["method"]
            
            if "from" in call_info and "to" in call_info:
                calls.append(call_info)
            
            for v in obj.values():
                _extract(v)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item)
    
    _extract(obj)
    return calls


def clear_records():
    """清空所有记录"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("📝 暂无记录需要清空")
        return
    
    count = 0
    for record_file in records:
        try:
            record_file.unlink()
            count += 1
        except OSError as e:
            print(f"⚠️ 删除 {record_file.name} 失败: {e}")
    
    print(f"✅ 已清空 {count} 条记录")


def context_prompt():
    """输出关键上下文 prompt，供模型使用"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    configured = get_configured_services()
    
    print("\n" + "=" * 60)
    print("🔴 FLOW-TRACE 上下文")
    print("=" * 60)
    
    # 🛑 如果有旧记录，提醒清空
    if records:
        print(f"\n⚠️ 发现 {len(records)} 条上次的分析记录！")
        print("   如果是新的一次分析，请先清空旧记录：")
        print("   ```bash")
        print("   python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py clear")
        print("   ```")
        print("\n   如果是继续上次的分析，可以忽略此提醒。")
        print("\n" + "-" * 60)
    
    # 显示配置的服务路径
    if configured:
        print("\n📁 已配置的服务路径:")
        for service, path in configured.items():
            print(f"  • {service}: {path}")
    else:
        print("\n⚠️ 未配置服务路径")
    
    # 显示已分析的服务
    if records:
        print("\n📝 已分析的服务:")
        all_services = set()
        all_downstream = set()
        
        for record_file in sorted(records):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
                service = record.get("service")
                entry = record.get("entry")
                downstream = extract_downstream(record.get("result_raw", ""))
                all_services.add(service)
                all_downstream.update(downstream)
                print(f"  • {service}: {entry}")
            except:
                pass
        
        # 找出未分析的服务
        unanalyzed = all_downstream - all_services
        if unanalyzed:
            print(f"\n⚠️ 未分析的服务: {', '.join(sorted(unanalyzed))}")
            unanalyzed_with_config = [s for s in unanalyzed if s in configured]
            if unanalyzed_with_config:
                print(f"   ✅ 已配置路径: {', '.join(unanalyzed_with_config)}")
    else:
        print("\n📝 暂无已分析的服务")


def export_markdown(output_path: str = None):
    """导出调用链分析结果到 Markdown 文件"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("❌ 暂无已分析的服务记录，无法导出")
        return
    
    # 收集所有服务数据
    all_raw_results = []
    
    for record_file in sorted(records):
        try:
            with open(record_file, encoding="utf-8") as f:
                record = json.load(f)
            all_raw_results.append({
                "service": record.get("service"),
                "entry": record.get("entry"),
                "result_raw": record.get("result_raw", ""),
                "timestamp": record.get("timestamp")
            })
        except Exception as e:
            print(f"⚠️ 读取 {record_file.stem} 失败: {e}")
    
    if not all_raw_results:
        print("❌ 没有有效数据可导出")
        return
    
    # 生成 Markdown 内容
    md_content = f"""# 跨微服务调用链分析

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📋 已分析服务

"""
    for r in all_raw_results:
        md_content += f"- **{r['service']}**: {r['entry']}\n"
    
    md_content += "\n---\n\n"
    
    # 输出每个服务的原始分析结果
    for r in all_raw_results:
        md_content += f"""## 服务: {r['service']}

**入口点**: {r['entry']}

**分析时间**: {r['timestamp']}

### 分析结果

{r['result_raw']}

---\n\n"""
    
    # 确定输出路径
    if not output_path:
        output_path = "./flow-trace-output.md"
    
    # 写入文件
    try:
        output_file = Path(output_path)
        output_file.write_text(md_content, encoding="utf-8")
        print(f"\n✅ 已导出到: {output_file.absolute()}")
        print(f"   服务数: {len(all_raw_results)}")
    except OSError as e:
        print(f"❌ 导出失败: {e}")


def generate_mermaid_diagram(services: dict, calls: list) -> str:
    """生成 Mermaid 时序图"""
    lines = ["sequenceDiagram"]
    
    # 添加参与者
    participants = set()
    for call in calls:
        if call.get('from'):
            participants.add(call['from'])
        if call.get('to'):
            participants.add(call['to'])
    
    for p in sorted(participants):
        lines.append(f"    participant {p}")
    
    # 添加调用关系
    for call in calls:
        from_svc = call.get('from', '?')
        to_svc = call.get('to', '?')
        call_type = call.get('type', 'call')
        method = call.get('method', '')
        
        label = f"{call_type}"
        if method:
            label = f"{method}"
        
        lines.append(f"    {from_svc}->>{to_svc}: {label}")
    
    return "\n".join(lines)


def preview_and_export():
    """预览并导出（需要用户确认）"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("❌ 暂无已分析的服务记录")
        return
    
    # 先展示预览
    print("\n" + "=" * 60)
    print("📊 图表预览")
    print("=" * 60)
    
    # 收集数据
    all_services = {}
    all_calls = []
    
    for record_file in sorted(records):
        try:
            with open(record_file, encoding="utf-8") as f:
                record = json.load(f)
            service = record.get("service")
            result_raw = record.get("result_raw", "")
            all_services[service] = {
                "entry": record.get("entry"),
                "downstream": extract_downstream(result_raw)
            }
            all_calls.extend(extract_calls(result_raw))
        except:
            pass
    
    # 输出预览
    print(f"\n已分析服务: {len(all_services)} 个")
    print(f"调用链: {len(all_calls)} 条")
    
    # 输出 Mermaid 预览
    mermaid = generate_mermaid_diagram(all_services, all_calls)
    print("\n```mermaid")
    print(mermaid)
    print("```")
    
    # 询问用户确认
    print("\n" + "=" * 60)
    print("📊 图表已生成预览，是否输出到文件？")
    print("=" * 60)
    print("\n输出路径（默认: ./flow-trace-output.md）:")
    print("或输入 'cancel' 取消:")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "save":
        if len(sys.argv) < 3:
            print("用法: python flow_trace_record.py save <service> <entry> <result>")
            print("       python flow_trace_record.py save --file <service> <entry> <file_path>")
            return
        if sys.argv[2] == "--file":
            # 从文件读取结果，避免 shell 转义问题
            if len(sys.argv) < 6:
                print("用法: python flow_trace_record.py save --file <service> <entry> <file_path>")
                return
            svc, entry, file_path = sys.argv[3], sys.argv[4], sys.argv[5]
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                print(f"❌ 读取文件失败: {e}")
                return
            save_record(svc, entry, content)
        else:
            if len(sys.argv) < 5:
                print("用法: python flow_trace_record.py save <service> <entry> <result>")
                return
            save_record(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == "list":
        list_records()
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("用法: python flow_trace_record.py get <service>")
            return
        try:
            validate_service_name(sys.argv[2])
        except ValueError as e:
            print(f"❌ {e}")
            return
        get_record(sys.argv[2])
    
    elif command == "summary":
        summary()
    
    elif command == "clear":
        clear_records()
    
    elif command == "context":
        context_prompt()
    
    elif command == "config":
        show_config()
    
    elif command == "preview":
        preview_and_export()
    
    elif command == "export":
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        export_markdown(output_path)
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
