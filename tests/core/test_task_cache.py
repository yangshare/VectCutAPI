"""vectcut.core.task_cache 行为测试（迁自 save_task_cache.py）。"""
from vectcut.core.task_cache import create_task, get_task_status, update_task_field


def test_task_lifecycle():
    create_task("t1")
    update_task_field("t1", "status", "processing")
    assert get_task_status("t1")["status"] == "processing"
