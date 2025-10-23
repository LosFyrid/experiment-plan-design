# ACE Framework Examples

这个目录包含ACE框架的使用示例和演示脚本。

## 观测系统演示 (ace_observability_demo.py)

完整演示ACE框架的观测系统如何工作。

### 功能展示

这个演示脚本展示了以下内容：

1. **观测工具初始化**
   - LogsManager: 管理日志目录和run_id
   - StructuredLogger: 为每个组件创建结构化日志
   - PerformanceMonitor: 追踪性能指标
   - LLMCallTracker: 记录所有LLM API调用
   - PlaybookVersionTracker: 保存playbook版本快照

2. **ACE循环执行**
   - Generator: 生成实验方案（带完整日志）
   - Reflector: 分析方案并提取insights（带轮次追踪）
   - Curator: 更新playbook（带操作日志）

3. **日志生成**
   - 每个组件的JSONL事件日志
   - 完整的LLM请求/响应记录
   - 性能指标报告
   - Playbook版本快照

4. **日志查询**
   - 演示如何使用分析脚本查询日志
   - 展示生成的日志文件结构

### 运行演示

```bash
# 从项目根目录运行
python examples/ace_observability_demo.py
```

### 生成的日志文件

运行后会在`logs/`目录下生成以下文件：

```
logs/
├── runs/
│   └── {date}/
│       └── run_{run_id}/
│           ├── generator.jsonl      # Generator事件日志
│           ├── reflector.jsonl      # Reflector事件日志
│           ├── curator.jsonl        # Curator事件日志
│           └── performance.json     # 性能报告
├── llm_calls/
│   └── {date}/
│       ├── generator/
│       │   └── {call_id}.json      # Generator LLM调用
│       ├── reflector/
│       │   └── {call_id}.json      # Reflector LLM调用
│       └── curator/
│           └── {call_id}.json      # Curator LLM调用
└── playbook_versions/
    ├── v_{timestamp}_init.json     # 初始playbook版本
    └── v_{timestamp}_{run_id}.json # 更新后的版本
```

### 演示后的分析

运行完演示后，可以使用分析脚本查询日志。详见 `scripts/analysis/README.md`。

### 代码示例

这个演示展示了如何在代码中集成观测工具：

```python
# 1. 初始化观测工具
logs_manager = get_logs_manager()
run_id = logs_manager.start_run()

perf_monitor = create_performance_monitor(run_id=run_id)
generator_logger = create_generator_logger(run_id=run_id)
generator_llm_tracker = create_llm_call_tracker("generator", run_id=run_id)

# 2. 将观测工具传递给ACE组件
generator = PlanGenerator(
    playbook_manager=playbook_manager,
    llm_provider=llm_provider,
    config=GeneratorConfig(),
    logger=generator_logger,          # ← 结构化日志
    perf_monitor=perf_monitor,        # ← 性能监控
    llm_tracker=generator_llm_tracker # ← LLM调用追踪
)

# 3. 正常运行组件 - 日志会自动记录
result = generator.generate(requirements=requirements)

# 4. 保存最终报告
perf_monitor.end_run()
perf_monitor.save_report(run_id=run_id)
logs_manager.end_run()
```

### 参考文档

- **观测架构设计**: `docs/LOG_ARCHITECTURE.md`
- **分析脚本使用**: `scripts/analysis/README.md`
- **ACE框架架构**: `ARCHITECTURE.md`
