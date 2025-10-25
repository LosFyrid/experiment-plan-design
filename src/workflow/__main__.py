"""让 workflow.task_worker 可以作为模块运行

用法:
    python -m workflow.task_worker <task_id>
    python -m workflow.task_worker <task_id> --resume
"""

from workflow.task_worker import main

if __name__ == "__main__":
    main()
