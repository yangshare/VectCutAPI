"""run_all.py — 原 example.py 的 if __name__ == "__main__" 入口已废弃。

各 demo 脚本可单独运行，例如：
    python -m examples.text_demo
    python -m examples.video_demo
    python -m examples.audio_demo
    python -m examples.image_demo
    python -m examples.sticker_demo
    python -m examples.effect_demo
    python -m examples.draft_demo

阶段5 拆分后保留此文件作为入口参考，不再执行原 main 块中的调用。
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 原 example.py 的 main 块（2343–2377）包含大量注释掉的 test 调用和
# 一个激活的 test_subtitle_01()。各 demo 可独立运行，此处不再统一调用。
#
# 如需运行特定 demo，直接在命令行执行对应模块即可。

if __name__ == "__main__":
    print("VectCutAPI examples — 请直接运行对应 demo 模块，例如：")
    print("    python -m examples.text_demo")
    print("    python -m examples.video_demo")
    print("    python -m examples.audio_demo")
    print("    python -m examples.image_demo")
    print("    python -m examples.sticker_demo")
    print("    python -m examples.effect_demo")
    print("    python -m examples.draft_demo")
