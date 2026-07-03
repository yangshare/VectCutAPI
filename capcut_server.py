from flask import Flask

from settings.local import PORT

# —— 业务路由收敛为声明式 Blueprint（draft/video/audio/text/image/effect）——
from vectcut.features.draft.flask_router import bp as draft_bp
from vectcut.features.video.flask_router import bp as video_bp
from vectcut.features.audio.flask_router import bp as audio_bp
from vectcut.features.text.flask_router import bp as text_bp
from vectcut.features.image.flask_router import bp as image_bp
from vectcut.features.effect.flask_router import bp as effect_bp
# —— 元数据查询路由（阶段 1 收敛为声明式 Blueprint，含 /metadata/{kind} 与 11 旧别名）——
from vectcut.features.metadata.flask_router import bp as metadata_bp

app = Flask(__name__)
app.register_blueprint(draft_bp)
app.register_blueprint(video_bp)
app.register_blueprint(audio_bp)
app.register_blueprint(text_bp)
app.register_blueprint(image_bp)
app.register_blueprint(effect_bp)
app.register_blueprint(metadata_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
