"""VectCutAPI HTTP server package（挂载全部 feature router）。"""
from __future__ import annotations

from vectcut.server.http.app import app

# 挂载全部 feature router（与 Flask 路由路径逐字对齐，无前缀）
# routers 导入 vectcut.server._helpers 而非 app.py，无循环依赖
from vectcut.features.draft.router import router as draft_router
from vectcut.features.video.router import router as video_router
from vectcut.features.audio.router import router as audio_router
from vectcut.features.text.router import router as text_router
from vectcut.features.image.router import router as image_router
from vectcut.features.effect.router import router as effect_router
from vectcut.features.metadata.router import router as metadata_router

app.include_router(draft_router)
app.include_router(video_router)
app.include_router(audio_router)
app.include_router(text_router)
app.include_router(image_router)
app.include_router(effect_router)
app.include_router(metadata_router)
