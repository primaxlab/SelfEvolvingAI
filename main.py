"""
================================================================================
自我进化AI系统 (Self-Evolving AI System) - 终极版
================================================================================

集成65个模块的完整自我进化AI系统

使用方式：
  python main.py                    # 交互式运行
  python main.py --serve            # 启动API服务器
  python main.py --evolve           # 触发一次进化
  python main.py --status           # 查看系统状态
  python main.py --scan             # 扫描代码
  python main.py --modules          # 查看所有模块状态
  python main.py --report           # 生成完整报告
  python main.py --chat "消息"      # 单次对话
"""

import sys
import os
import argparse
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.evolution_loop import SelfEvolvingAI, create_evolution_ai


def interactive_mode(ai: SelfEvolvingAI):
    """交互式模式"""
    print("=" * 70)
    print("🧬 自我进化AI系统 v4.0 - 超级版（65模块+真实AI）")
    print("=" * 70)
    print("命令:")
    print("  quit         - 退出")
    print("  status       - 查看系统状态")
    print("  evolve       - 触发进化")
    print("  modules      - 查看所有模块状态")
    print("  learn <内容>  - 学习新知识")
    print("  goal <目标>   - 设定目标")
    print("  code <描述>   - 生成代码")
    print("  test <目标>   - 运行测试")
    print("  docs <目标>   - 生成文档")
    print("  memory       - 查看记忆状态")
    print("  tools        - 查看已注册工具")
    print("  gaps         - 查看知识空白")
    print("  report       - 生成完整报告")
    print("  providers    - 查看LLM提供商")
    print("  config <provider> <key> - 配置API Key")
    print("  stream <消息> - 流式对话")
    print("  exec <命令>  - 执行系统命令")
    print("  open <网址>   - 打开网站")
    print("  screenshot   - 截图")
    print("  search <关键词> - 搜索网页")
    print("  security     - 查看安全报告")
    print("  help         - 显示帮助")
    print("-" * 70)

    while True:
        try:
            user_input = input("\n你: ").strip()

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd == 'quit' or cmd == 'exit':
                print("再见！")
                break

            elif cmd == 'status':
                print(ai.generate_evolution_report())

            elif cmd == 'evolve':
                print("触发全面进化...")
                result = ai.evolve("manual")
                print(f"进化完成！代数: {ai.state.generation}")
                print(f"改进项: {len(result['improvements'])}")
                print(f"耗时: {result['duration']:.2f}s")
                for imp in result['improvements']:
                    print(f"  - {imp['type']}")

            elif cmd == 'modules':
                stats = ai.get_all_module_stats()
                print(f"\n全部 {len(stats)} 个模块状态:")
                print("-" * 50)
                for name, stat in stats.items():
                    if isinstance(stat, dict):
                        summary = ', '.join(f"{k}={v}" for k, v in list(stat.items())[:2])
                    else:
                        summary = str(stat)[:60]
                    print(f"  {name}: {summary}")

            elif cmd.startswith('learn '):
                content = user_input[6:]
                result = ai.learn_from_knowledge(content, source='user')
                print(f"学习完成！新增实体: {result.get('entities_added', 0)}")

            elif cmd.startswith('goal '):
                goal_desc = user_input[5:]
                result = ai.set_goal(goal_desc, goal_desc)
                print(f"目标已设定: {result['title']}")
                print(f"任务数量: {result['tasks_count']}")

            elif cmd.startswith('code '):
                desc = user_input[5:]
                result = ai.generate_code(desc)
                print(f"代码生成结果: {str(result)[:200]}")

            elif cmd.startswith('test '):
                target = user_input[5:]
                result = ai.run_tests(target)
                print(f"测试结果: {str(result)[:200]}")

            elif cmd.startswith('docs '):
                target = user_input[5:]
                result = ai.generate_docs(target)
                print(f"文档生成: {str(result)[:200]}")

            elif cmd == 'memory':
                summary = ai.memory.summarize()
                print(json.dumps(summary, ensure_ascii=False, indent=2))

            elif cmd == 'tools':
                tools = ai.tool_registry.list_tools()
                print(f"已注册工具: {len(tools)}")
                for t in tools:
                    print(f"  - {t['name']}: {t['description']}")

            elif cmd == 'gaps':
                gaps = ai.active_exploration.identify_gaps()
                print(json.dumps(gaps, ensure_ascii=False, indent=2) if isinstance(gaps, dict) else str(gaps))

            elif cmd == 'report':
                report = ai.generate_evolution_report()
                print(report)
                report_path = os.path.join(ai.storage_dir, 'report.txt')
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n报告已保存到: {report_path}")

            elif cmd == 'providers':
                stats = ai.llm.get_stats()
                print(f"\n可用提供商: {stats['available_providers']}")
                print(f"默认提供商: {stats['default_provider']}")
                print(f"对话历史: {stats['history_length']} 条")
                if stats['usage_stats']:
                    print("使用统计:")
                    for p, s in stats['usage_stats'].items():
                        print(f"  {p}: {s['requests']}次请求, {s['tokens']} tokens")

            elif cmd.startswith('config '):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 3:
                    provider = parts[1]
                    api_key = parts[2]
                    ai.llm.configure_provider(provider, api_key=api_key)
                    print(f"已配置 {provider}，当前默认: {ai.llm.default_provider}")
                else:
                    print("用法: config <provider> <api_key>")

            elif cmd.startswith('stream '):
                msg = user_input[7:]
                print("AI: ", end="", flush=True)
                for chunk in ai.llm.chat_stream(msg):
                    print(chunk, end="", flush=True)
                print()

            elif cmd.startswith('exec '):
                command = user_input[5:]
                result = ai.execute_command(command)
                if result.get("success"):
                    print(result.get("stdout", "")[:2000])
                else:
                    print(f"错误: {result.get('error', result.get('stderr', ''))}")

            elif cmd.startswith('open '):
                url = user_input[5:]
                result = ai.open_website(url)
                print(f"标题: {result.get('title', '')}")
                print(f"内容: {result.get('text_preview', '')[:500]}")

            elif cmd == 'screenshot':
                path = ai.take_screenshot()
                print(f"截图: {path}" if path else "截图失败(需要pyautogui)")

            elif cmd.startswith('search '):
                query = user_input[7:]
                result = ai.search(query)
                print(f"结果: {result.get('text_preview', '')[:500]}")

            elif cmd == 'security':
                report = ai.permissions.generate_report()
                print(json.dumps(report, indent=2, ensure_ascii=False))

            elif cmd == 'help':
                print("可用命令:")
                print("  quit/exit    - 退出")
                print("  status       - 查看系统状态")
                print("  evolve       - 触发进化")
                print("  modules      - 查看所有模块状态")
                print("  learn <内容>  - 学习新知识")
                print("  goal <目标>   - 设定目标")
                print("  code <描述>   - 生成代码")
                print("  test <目标>   - 运行测试")
                print("  docs <目标>   - 生成文档")
                print("  memory       - 查看记忆状态")
                print("  tools        - 查看已注册工具")
                print("  gaps         - 查看知识空白")
                print("  report       - 生成完整报告")
                print("  help         - 显示帮助")

            else:
                # 正常处理
                result = ai.process(user_input)
                print(f"\nAI: {result['answer']}")

                if result.get('needs_clarification'):
                    print("（我需要更多信息来更好地回答）")

                if result.get('reflection_insights'):
                    print(f"[反思洞察: {', '.join(str(i) for i in result['reflection_insights'][:2])}]")

                print(f"[置信度: {result['confidence']:.2f} | 领域: {result['domain']} | "
                      f"模块: {len(result.get('modules_used', []))} | "
                      f"耗时: {result['processing_time']:.3f}s]")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自我进化AI系统 - 超级版（64模块）')
    parser.add_argument('--project', default='.', help='项目目录')
    parser.add_argument('--serve', action='store_true', help='启动API服务器')
    parser.add_argument('--port', type=int, default=8000, help='API端口')
    parser.add_argument('--chat', type=str, default='', help='单次对话')
    parser.add_argument('--evolve', action='store_true', help='触发进化')
    parser.add_argument('--status', action='store_true', help='查看状态')
    parser.add_argument('--scan', action='store_true', help='扫描代码')
    parser.add_argument('--modules', action='store_true', help='查看所有模块状态')
    parser.add_argument('--report', action='store_true', help='生成报告')

    args = parser.parse_args()

    # 初始化AI
    ai = create_evolution_ai(args.project)

    if args.serve:
        from api_server import run_server
        run_server(port=args.port)

    elif args.chat:
        result = ai.process(args.chat)
        print(result['answer'])

    elif args.evolve:
        print("触发进化...")
        result = ai.evolve("manual")
        print(f"进化完成！代数: {ai.state.generation}")
        print(f"改进项: {len(result['improvements'])}")
        for imp in result['improvements']:
            print(f"  - {imp['type']}")

    elif args.status:
        print(ai.generate_evolution_report())

    elif args.scan:
        print("扫描项目代码...")
        result = ai.code_improver.scan_project()
        print(f"扫描文件: {result['files_scanned']}")
        print(f"发现问题: {result['total_issues']}")
        if result['total_issues'] > 0:
            print("\n前5个问题:")
            for issue in result['issues'][:5]:
                print(f"  [{issue['severity']}] {issue['file_path']}:{issue['line_number']}")
                print(f"    {issue['description']}")

    elif args.modules:
        stats = ai.get_all_module_stats()
        print(f"全部 {len(stats)} 个模块状态:")
        for name, stat in stats.items():
            print(f"  {name}: {stat}")

    elif args.report:
        report = ai.generate_evolution_report()
        report_path = os.path.join(ai.storage_dir, 'report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {report_path}")
        print(report)

    else:
        interactive_mode(ai)


if __name__ == "__main__":
    main()
