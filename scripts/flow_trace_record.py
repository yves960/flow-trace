#!/usr/bin/env python3
"""
flow-trace 流程记录脚本

用于跨微服务调用链分析过程中持久化每个服务的分析结果，
解决长对话中模型遗忘问题。

用法:
    python flow_trace_record.py save <service> <entry> <json_result>   # 保存服务分析结果
    python flow_trace_record.py list                                    # 列出所有已分析服务
    python flow_trace_record.py get <service>                           # 获取某个服务的结果
    python flow_trace_record.py summary                                 # 汇总所有服务流程
    python flow_trace_record.py clear                                   # 清空记录
    python flow_trace_record.py context                                 # 输出关键上下文prompt
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 记录存储路径
RECORD_DIR = Path.home() / ".flow-trace-records"


def ensure_dir():
    """确保存储目录存在"""
    RECORD_DIR.mkdir(parents=True, exist_ok=True)


def save_record(service: str, entry: str, result_json: str):
    """保存服务分析结果"""
    ensure_dir()
    
    try:
        result = json.loads(result_json) if result_json.startswith("{") or result_json.startswith("[") else {"raw": result_json}
    except json.JSONDecodeError:
        result = {"raw": result_json}
    
    record = {
        "service": service,
        "entry": entry,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    
    record_file = RECORD_DIR / f"{service}.json"
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存服务 [{service}] 的分析结果")
    print(f"   入口点: {entry}")
    print(f"   文件: {record_file}")


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
            downstream = extract_downstream(record.get("result", {}))
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
    
    with open(record_file, encoding="utf-8") as f:
        record = json.load(f)
    
    print(f"\n📋 服务 [{service}] 分析结果:")
    print("=" * 50)
    print(f"入口点: {record.get('entry')}")
    print(f"时间: {record.get('timestamp')}")
    print("\n分析结果:")
    print(json.dumps(record.get("result"), ensure_ascii=False, indent=2))


def summary():
    """汇总所有服务的流程"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("📝 暂无已分析的服务记录，无法汇总")
        return
    
    print("\n" + "=" * 60)
    print("📊 跨微服务调用链汇总")
    print("=" * 60)
    
    all_services = {}
    all_calls = []
    
    for record_file in sorted(records):
        try:
            with open(record_file, encoding="utf-8") as f:
                record = json.load(f)
            
            service = record.get("service")
            entry = record.get("entry")
            result = record.get("result", {})
            
            all_services[service] = {
                "entry": entry,
                "downstream": extract_downstream(result),
                "timestamp": record.get("timestamp")
            }
            
            # 提取调用链
            calls = extract_calls(result)
            all_calls.extend(calls)
            
        except Exception as e:
            print(f"⚠️ 读取 {record_file.stem} 失败: {e}")
    
    # 输出服务列表
    print(f"\n已分析服务 ({len(all_services)} 个):")
    for svc, info in all_services.items():
        downstream = info.get("downstream", [])
        ds_str = f" → {', '.join(downstream)}" if downstream else ""
        print(f"  {svc}: {info['entry']}{ds_str}")
    
    # 输出服务关系图（Mermaid）
    print("\n🔗 服务调用关系图 (Mermaid):")
    print("```mermaid")
    print("flowchart LR")
    for svc, info in all_services.items():
        for ds in info.get("downstream", []):
            print(f"    {svc} --> {ds}")
    print("```")
    
    # 输出完整时序图数据
    print("\n📋 完整调用链 JSON:")
    summary_data = {
        "services": all_services,
        "total_calls": len(all_calls),
        "calls": all_calls[:20]  # 只显示前20条，避免太长
    }
    if len(all_calls) > 20:
        summary_data["_note"] = f"还有 {len(all_calls) - 20} 条调用未显示"
    
    print(json.dumps(summary_data, ensure_ascii=False, indent=2))


def extract_downstream(result: dict) -> list:
    """从分析结果中提取下游服务列表"""
    downstream = set()
    
    def _extract(obj):
        if isinstance(obj, dict):
            # 检查常见的下游服务字段
            if "service" in obj:
                downstream.add(obj["service"])
            if "target_service" in obj:
                downstream.add(obj["target_service"])
            if "downstream" in obj:
                ds = obj["downstream"]
                if isinstance(ds, list):
                    downstream.update(ds)
                elif isinstance(ds, str):
                    downstream.add(ds)
            if "calls" in obj:
                _extract(obj["calls"])
            # 递归
            for v in obj.values():
                _extract(v)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item)
    
    _extract(result)
    return sorted(downstream)


def extract_calls(result: dict) -> list:
    """从分析结果中提取调用链"""
    calls = []
    
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
    
    _extract(result)
    return calls


def clear_records():
    """清空所有记录"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    if not records:
        print("📝 暂无记录需要清空")
        return
    
    for record_file in records:
        record_file.unlink()
    
    print(f"✅ 已清空 {len(records)} 条记录")


def context_prompt():
    """输出关键上下文 prompt，供模型使用"""
    ensure_dir()
    
    records = list(RECORD_DIR.glob("*.json"))
    
    print("\n" + "=" * 60)
    print("🔴 FLOW-TRACE 上下文提醒")
    print("=" * 60)
    
    if records:
        print("\n📝 已分析的服务:")
        for record_file in sorted(records):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
                service = record.get("service")
                entry = record.get("entry")
                downstream = extract_downstream(record.get("result", {}))
                print(f"  • {service}: {entry}")
                if downstream:
                    print(f"    下游 → {', '.join(downstream)}")
            except:
                pass
        
        # 找出未分析的服务
        all_services = set()
        all_downstream = set()
        for record_file in records:
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
                all_services.add(record.get("service"))
                all_downstream.update(extract_downstream(record.get("result", {})))
            except:
                pass
        
        unanalyzed = all_downstream - all_services
        if unanalyzed:
            print(f"\n⚠️ 发现未分析的服务: {', '.join(sorted(unanalyzed))}")
            print("   建议继续分析这些服务")
    else:
        print("\n📝 暂无已分析的服务")
    
    print("\n" + "=" * 60)
    print("🔴 每次分析完成后必须执行:")
    print("=" * 60)
    print("""
    python ~/.agents/skills/flow-trace/scripts/flow_trace_record.py save <服务名> <入口点> '<JSON结果>'
    
    然后展示探索询问菜单：
    
    ════════════════════════════════════════════════════════
    📍 分析完成！请选择下一步操作：
    ════════════════════════════════════════════════════════
    
    1. 分析其他入口点
    2. 深入分析某个节点
    3. 追踪未分析的下游服务
    4. 配置/更新服务目录
    5. 批量配置服务目录
    6. 结束探索，生成图表
    7. 仅输出JSON，不生成图表
    
    请选择 (1/2/3/4/5/6/7):
""")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "save":
        if len(sys.argv) < 5:
            print("用法: python flow_trace_record.py save <service> <entry> <json_result>")
            return
        save_record(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == "list":
        list_records()
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("用法: python flow_trace_record.py get <service>")
            return
        get_record(sys.argv[2])
    
    elif command == "summary":
        summary()
    
    elif command == "clear":
        clear_records()
    
    elif command == "context":
        context_prompt()
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()