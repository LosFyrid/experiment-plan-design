# ACE Framework Analysis Scripts

这个目录包含用于查询和分析ACE框架观测数据的脚本。

## 脚本概览

### 1. query_runs.py - 查询运行记录

查询和过滤ACE框架的运行记录。

**用法示例**：
```bash
# 列出所有runs
python query_runs.py

# 查询特定日期的runs
python query_runs.py --date 20251022

# 查询特定run的详细信息
python query_runs.py --run-id 143052_abc123

# 查询特定组件的runs
python query_runs.py --component generator

# 显示最近5次运行
python query_runs.py --latest 5

# 显示详细JSON输出
python query_runs.py --details
```

**输出信息**：
- Run ID
- 日期
- 包含的组件（Generator/Reflector/Curator）
- 总耗时
- LLM调用次数

---

### 2. query_llm_calls.py - 查询LLM调用

查询和分析所有LLM API调用。

**用法示例**：
```bash
# 列出所有LLM调用
python query_llm_calls.py

# 查询特定日期的LLM调用
python query_llm_calls.py --date 20251022

# 查询特定组件的LLM调用
python query_llm_calls.py --component generator

# 查询特定run的LLM调用
python query_llm_calls.py --run-id 143052_abc123

# 只显示成功的调用
python query_llm_calls.py --status success

# 查询特定调用的详细信息
python query_llm_calls.py --call-id 143052_abc123_generator

# 导出特定调用的prompts到文件
python query_llm_calls.py --export-prompt 143052_abc123_generator --output prompt.txt

# 分析token使用情况
python query_llm_calls.py --analyze-tokens

# 显示详细JSON输出
python query_llm_calls.py --details
```

**输出信息**：
- Call ID
- 组件名称
- 模型名称
- 状态（success/error/in_progress）
- Token数量
- 调用耗时

---

### 3. analyze_performance.py - 性能分析

分析ACE框架的性能指标。

**用法示例**：
```bash
# 分析特定run的性能
python analyze_performance.py --run-id 143052_abc123

# 分析特定日期的所有runs
python analyze_performance.py --date 20251022

# 比较多个runs的性能
python analyze_performance.py --date 20251022 --compare

# 识别性能瓶颈（默认top 5）
python analyze_performance.py --bottlenecks

# 识别top 10性能瓶颈
python analyze_performance.py --bottlenecks --top 10

# 分析LLM调用效率
python analyze_performance.py --llm-efficiency
```

**分析维度**：
- **时间分解**：各组件和操作的耗时统计
- **LLM统计**：调用次数、token使用、平均耗时
- **瓶颈识别**：最耗时的操作（跨多个runs聚合）
- **效率分析**：tokens/秒、平均调用时长

---

### 4. analyze_playbook_evolution.py - Playbook进化分析

追踪Playbook随时间的演化。

**用法示例**：
```bash
# 列出所有playbook版本
python analyze_playbook_evolution.py --list-versions

# 比较两个版本
python analyze_playbook_evolution.py --compare v_20251022_143052 v_20251022_153245

# 显示增长统计
python analyze_playbook_evolution.py --growth-stats

# 追踪特定bullet的演化
python analyze_playbook_evolution.py --track-bullet mat-00001
```

**分析维度**：
- **版本列表**：所有playbook快照及其元数据
- **版本比较**：识别新增、删除、修改的bullets
- **增长统计**：playbook规模变化、分区分布、质量指标
- **Bullet追踪**：单个bullet在各版本中的变化历史

---

## 日志架构

观测系统使用以下目录结构：

```
logs/
├── runs/                    # 按run组织的日志
│   └── {date}/
│       └── run_{run_id}/
│           ├── generator.jsonl
│           ├── reflector.jsonl
│           ├── curator.jsonl
│           └── performance.json
├── llm_calls/              # 按组件组织的LLM调用
│   └── {date}/
│       ├── generator/
│       │   └── {call_id}.json
│       ├── reflector/
│       │   └── {call_id}.json
│       └── curator/
│           └── {call_id}.json
└── playbook_versions/      # Playbook版本历史
    └── v_{timestamp}_{run_id}.json
```

**关键概念**：
- **run_id**: 格式为 `{HHMMSS}_{random6chars}`，用于关联单次ACE循环的所有日志
- **JSONL格式**: 每行一个JSON事件，便于流式处理和增量分析
- **双重索引**: 日志既可按run查询，也可按组件/日期查询

---

## 常见分析场景

### 场景1：调试特定run

```bash
# 1. 查看run概况
python query_runs.py --run-id 143052_abc123

# 2. 查看该run的所有LLM调用
python query_llm_calls.py --run-id 143052_abc123

# 3. 分析该run的性能
python analyze_performance.py --run-id 143052_abc123

# 4. 导出某个LLM调用的prompts进行检查
python query_llm_calls.py --export-prompt 143052_abc123_generator_round1 --output debug_prompt.txt
```

### 场景2：性能优化

```bash
# 1. 识别整体瓶颈
python analyze_performance.py --bottlenecks --top 10

# 2. 比较一天内的runs，找出异常慢的
python analyze_performance.py --date 20251022 --compare

# 3. 分析LLM调用效率
python analyze_performance.py --llm-efficiency

# 4. 查看特定组件的token使用
python query_llm_calls.py --component generator --analyze-tokens
```

### 场景3：Playbook质量追踪

```bash
# 1. 查看playbook增长趋势
python analyze_playbook_evolution.py --growth-stats

# 2. 比较更新前后的变化
python analyze_playbook_evolution.py --compare v_old v_new

# 3. 追踪问题bullet的演化
python analyze_playbook_evolution.py --track-bullet err-00023

# 4. 列出所有版本，找出关键节点
python analyze_playbook_evolution.py --list-versions
```

### 场景4：Token成本分析

```bash
# 1. 分析总体token使用
python query_llm_calls.py --analyze-tokens

# 2. 按组件分解token成本
python query_llm_calls.py --component generator --analyze-tokens
python query_llm_calls.py --component reflector --analyze-tokens
python query_llm_calls.py --component curator --analyze-tokens

# 3. 查看特定日期的token消耗
python query_llm_calls.py --date 20251022 --analyze-tokens

# 4. 识别高token调用
python query_llm_calls.py --details | jq 'sort_by(.tokens.total) | reverse | .[0:5]'
```

---

## 输出格式

所有脚本支持两种输出格式：

1. **表格格式**（默认）：人类可读的表格输出
2. **JSON格式**（`--details`）：机器可读的完整数据

示例：
```bash
# 表格格式（易读）
python query_runs.py --latest 5

# JSON格式（可用于进一步处理）
python query_runs.py --latest 5 --details > runs.json
```

---

## 依赖项

这些脚本是纯Python 3.8+实现，只使用标准库，无需额外依赖。

---

## 集成到工作流

### CI/CD集成

可以在CI中运行性能回归检测：

```bash
# 在CI中运行
python analyze_performance.py --run-id $CI_RUN_ID --llm-efficiency

# 检查token使用是否超出阈值
TOKENS=$(python query_llm_calls.py --run-id $CI_RUN_ID --analyze-tokens | jq '.total_tokens')
if [ $TOKENS -gt 100000 ]; then
  echo "Token usage exceeded threshold!"
  exit 1
fi
```

### 定期报告

使用cron定期生成报告：

```bash
# 每天生成性能报告
0 0 * * * python analyze_performance.py --date $(date +%Y%m%d) --compare > /reports/daily_perf.txt

# 每周生成playbook增长报告
0 0 * * 0 python analyze_playbook_evolution.py --growth-stats > /reports/weekly_growth.txt
```

---

## 扩展开发

要添加新的分析脚本：

1. 在此目录创建新的`.py`文件
2. 使用相同的目录结构访问日志：`get_logs_dir()`
3. 遵循相同的CLI参数约定（`--date`, `--run-id`, `--details`）
4. 更新此README

示例骨架：
```python
#!/usr/bin/env python3
"""Your analysis script description."""

import json
import argparse
from pathlib import Path

def get_logs_dir() -> Path:
    project_root = Path(__file__).parent.parent.parent
    return project_root / "logs"

def main():
    parser = argparse.ArgumentParser(description="Your analysis")
    parser.add_argument("--date", help="Filter by date")
    parser.add_argument("--details", action="store_true")
    # ... your arguments

    args = parser.parse_args()
    # ... your logic

if __name__ == "__main__":
    main()
```

---

## 故障排除

**问题：找不到日志文件**
- 确保已经运行过ACE框架生成日志
- 检查`logs/`目录是否存在
- 验证日期格式是否正确（YYYYMMDD）

**问题：JSON解析错误**
- JSONL文件可能未完全写入（run中断）
- 使用`--details`查看原始JSON输出进行调试

**问题：性能报告为空**
- 确保run已完成（`PerformanceMonitor.save_report()`已调用）
- 检查`performance.json`是否存在于run目录

---

## 反馈与改进

如果需要新的分析功能，请在项目issue中提出。常见需求：
- 可视化（绘图）
- Web界面
- 实时监控
- 告警系统
