# 需求规格：仅上传 draft_content 的母版导入模型

- 日期：2026-07-07
- 状态：待评审
- 范围：修正 template_filling 与 Electron 桌面端的母版导入模型
- 相关文档：
  - `docs/superpowers/specs/2026-07-04-solution2-desktop-client.md`
  - `docs/superpowers/plans/2026-07-05-solution1-docker-deployment.md`
  - `docs/superpowers/plans/2026-07-05-solution2-backend-template-filling.md`
  - `docs/superpowers/plans/2026-07-05-solution2-desktop-client.md`
  - `desktop/docs/e2e-verification.md`

## 1. 背景

真实母版验证显示，当前“客户端打包整个剪映草稿目录 ZIP 上传”的方案不适合目标场景。

已验证的本机母版：

| 母版 | 草稿目录大小 | 打包 ZIP | draft_content 状态 | 现有链路结果 |
| --- | ---: | ---: | --- | --- |
| `@模板【双楠】` | 398.87MB | 227.16MB | 加密，可由 `videoeditor.dll` 解密 | 密文导入失败；明文只扫出 1 个 subtitle，且 `track_name=""` 导致渲染失败 |
| `书亦青黛` | 415.51MB | 238.86MB | 加密，可由 `videoeditor.dll` 解密 | 密文导入失败；明文扫出 35 video + 1 subtitle + 1 audio，但全部 `track_name=""` 导致渲染失败 |

当前链路的直接问题：

- 桌面端 `readZipFile` 默认限制 100MB，真实母版 ZIP 会被客户端拦截。
- 后端 `max_template_zip_mb` 默认 50MB，真实母版 ZIP 会被服务端拦截。
- 真实剪映 `draft_content.json` 是加密格式，后端目前不会自动解密。
- 即使解密，真实模板里轨道名常为空，现有 `track_name` 定位模型不可靠。

产品目标已经明确：**新草稿不依赖母版原素材，母版只提供布局、样式、时间轴结构；生成时所有素材由用户重新填入。**

因此母版导入阶段不应上传 `Resources/`、原视频、原图片、原 BGM 或整个草稿目录。

素材填充阶段也不是“上传素材文件”模型。桌面端让用户在本机选择新素材，并在客户端读取素材元数据；服务端接收的是本机绝对路径和已探测元数据，用这些字段组装新的草稿 JSON。

## 2. 目标

1. 客户端母版导入阶段只上传单个 `draft_content.json` 文件，不再上传草稿目录 ZIP。
2. 服务端负责识别 `draft_content.json` 是明文还是密文；密文由服务端用剪映 `videoeditor.dll` 解密。
3. 后端保存解密后的明文模板 JSON，用于槽位扫描、槽位配置和后续渲染。
4. 后端生成新草稿时不依赖母版附件；所有会引用媒体文件的槽位必须由用户新素材替换，替换值是客户端传入的本机素材路径和素材元数据。
5. 新草稿下载仍可继续使用 ZIP，因为下载的是生成结果包，不是母版上传包。
6. 真实剪映空轨道名场景必须可定位、可保存、可渲染，不能再依赖 `track.name` 作为唯一定位字段。
7. 服务端默认不访问用户素材文件，只校验路径字符串和元数据结构；最终由打开剪映草稿的客户端机器负责解析这些本机路径。

## 3. 非目标

- 不上传母版 `Resources/` 目录。
- 不上传用户新素材文件；客户端只提交新素材路径和素材元数据。
- 不保留母版原素材引用作为兜底。
- 不在客户端调用剪映 DLL 解密。
- 不要求服务端访问客户端本机素材路径。
- 不保证生成草稿能在另一台没有相同素材路径的机器上打开；跨机器打开需要额外的素材同步或路径映射方案。
- 不要求 Docker/Linux 环境支持密文解密；无 DLL 时应明确报错。
- 不在本规格内完成批量套版、任务队列、素材库管理。
- 不在本规格内实现完整 cover 替换算法；但接口和槽位模型必须为 cover 留出位置。

## 4. 核心决策

### 4.1 母版导入不再使用 ZIP

新的母版导入数据流：

```
用户选择剪映母版草稿目录
  -> 客户端读取 <draft_dir>/draft_content.json 原始 bytes
  -> 客户端 POST 单文件到后端
  -> 后端 json.loads 尝试明文解析
  -> 失败时调用服务端 DLL 解密
  -> 解密后再次 json.loads
  -> 保存明文 draft_content
  -> 扫描槽位
```

ZIP 只保留在生成结果下载阶段：

```
render_draft
  -> 生成新的 draft_content.json + 最小必要草稿元文件
  -> 打包生成草稿 ZIP
  -> 客户端下载并导入剪映草稿目录
```

### 4.2 解密放服务端

原因：

- 客户端机器未必安装可用的剪映 DLL。
- Electron 客户端直接调用原生 DLL 的部署和安全边界复杂。
- 服务端可以统一配置 DLL 路径、统一错误码、统一日志脱敏。

服务端运行模式：

| 场景 | 行为 |
| --- | --- |
| 上传明文 JSON | 永远可导入，不依赖 DLL |
| 上传密文且配置 DLL | 解密后导入 |
| 上传密文但未配置 DLL | 返回 `T_ENCRYPTED_DRAFT_UNSUPPORTED` |
| DLL 配置错误或解密失败 | 返回 `T_DECRYPT_FAILED` |
| 解密后仍不是合法 JSON | 返回 `T_INVALID_DRAFT_CONTENT` |

### 4.3 所有母版素材引用必须替换或移除

因为不上传母版资源，新草稿不能依赖母版的本地资源路径或 `Resources/...` 文件。

渲染前必须做引用完整性检查：

- 如果 video/audio/bgm/image/cover 原素材引用仍存在，且没有对应新素材替换，渲染应失败。
- 失败错误应列出未替换引用对应的槽位或 material id。
- 不允许静默生成会在剪映里丢素材的草稿。

### 4.4 新素材用客户端路径和元数据传给服务端

新素材数据流：

```
用户在桌面端选择 G:\剪映剪辑\小说素材\素材\视频\clip_001.mp4
  -> 客户端读取素材元数据：类型、时长、宽高、fps、文件大小等
  -> 客户端提交槽位配置：slot_id + material_path + metadata
  -> 服务端校验 metadata 字段完整、类型匹配、时间单位合法
  -> 服务端把 material_path 和 metadata 写入新的 draft_content
  -> 生成草稿 ZIP
```

关键约束：

- 服务端不默认访问客户端传入的路径，不需要 `ffprobe` 用户素材文件。
- 客户端探测结果是生成草稿的素材事实来源。
- 服务端只做结构校验和业务校验，例如必填字段、类型匹配、时长单位、宽高范围、路径字符串格式。
- 生成草稿应引用用户选择的本机素材路径，不把用户素材复制到模板目录。
- 如果客户端提交的元数据不准确，服务端无法通过读文件兜底纠正，生成草稿可能在剪映中表现异常；因此客户端素材探测必须有自动化测试和真实素材验收。

### 4.5 槽位定位不能依赖 track_name

真实母版中大量轨道 `name=""`。新槽位定位必须使用稳定 locator。

建议槽位模型：

```jsonc
{
  "slot_id": "video_track0_seg12",
  "type": "video",
  "name": "视频槽位 12",
  "locator": {
    "scope": "root",
    "track_index": 0,
    "track_id": "optional-track-id",
    "track_type": "video",
    "segment_index": 12,
    "segment_id": "optional-segment-id",
    "material_id": "optional-material-id"
  },
  "required": true
}
```

兼容策略：

- 新接口返回 `locator`。
- 旧字段 `track_name` 可暂时保留给旧客户端，但不得作为渲染唯一依据。
- `slot_resolver` 优先用 `locator.track_id` / `track_index` / `segment_id`，最后才回退 `track_name`。

## 5. 新 API 设计

### 5.1 导入 draft_content 单文件

```http
POST /api/template/import-draft-content?template_id={template_id}
Content-Type: multipart/form-data

file = draft_content.json
```

选择 multipart 单文件而不是 JSON body，原因：

- 同时支持明文和密文 bytes。
- 避免大 JSON body 编码、转义、代理限制问题。
- 客户端只需读取文件 bytes，不需要理解内容格式。

成功响应：

```json
{
  "success": true,
  "output": {
    "template_id": "shuyi_qingdai",
    "slots": [
      {
        "slot_id": "video_track0_seg0",
        "type": "video",
        "name": "视频槽位 0",
        "locator": {
          "scope": "root",
          "track_index": 0,
          "track_type": "video",
          "segment_index": 0,
          "segment_id": "..."
        },
        "required": true
      }
    ],
    "message": "模板 shuyi_qingdai 导入成功，共 37 个槽位"
  },
  "error": null
}
```

失败响应仍使用统一信封：

```json
{
  "success": false,
  "output": null,
  "error": {
    "code": "T_ENCRYPTED_DRAFT_UNSUPPORTED",
    "message": "服务端未配置剪映解密 DLL，无法导入加密 draft_content.json"
  }
}
```

### 5.2 旧 ZIP 导入接口处理

保留 `POST /api/template/import`，但降级为兼容接口：

- 继续支持旧测试和旧客户端。
- 文档标记为 legacy。
- 新桌面端不再调用它。
- 若 ZIP 内只有 `draft_content.json`，可复用新导入逻辑。
- 不再把全量草稿 ZIP 作为推荐路径。

### 5.3 渲染请求中的素材引用

槽位配置和渲染请求中的新素材使用路径引用和客户端探测元数据，不上传素材二进制。

示例：

```json
{
  "template_id": "shuyi_qingdai",
  "slots": {
    "video_track0_seg0": {
      "kind": "path",
      "path": "G:\\剪映剪辑\\小说素材\\素材\\视频\\clip.mp4",
      "metadata": {
        "media_type": "video",
        "duration_us": 8200000,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "file_size": 12582912,
        "format": "mp4"
      }
    },
    "audio_track0_seg0": {
      "kind": "path",
      "path": "G:\\剪映剪辑\\小说素材\\素材\\音乐\\bgm.m4a",
      "metadata": {
        "media_type": "audio",
        "duration_us": 39997000,
        "file_size": 3840000,
        "format": "m4a"
      }
    },
    "subtitle__0": {
      "kind": "text",
      "text": "字幕内容"
    }
  }
}
```

服务端收到路径和元数据后只做 JSON 组装前校验：

- `path` 是非空字符串，并保留 Windows 路径原文。
- `metadata.media_type` 与槽位类型匹配。
- video/audio 必须有正数 `duration_us`。
- video/image 必须有正数 `width` 和 `height`。
- 可选字段如 `fps`、`file_size`、`format` 类型合法。

任一检查失败时返回 `R_INVALID_MATERIAL_METADATA`，不进入草稿生成。

## 6. 配置设计

新增配置字段：

```jsonc
{
  "jianying_decrypt_dll_path": "${JY_VIDEOEDITOR_DLL_PATH}",
  "max_draft_content_mb": "${MAX_DRAFT_CONTENT_MB}"
}
```

默认值：

- `jianying_decrypt_dll_path`: 空字符串。
- `max_draft_content_mb`: 20。

`.env.example` 新增：

```env
JY_VIDEOEDITOR_DLL_PATH=C:\Users\Administrator\AppData\Local\JianyingPro\Apps\8.9.0.13361\videoeditor.dll
MAX_DRAFT_CONTENT_MB=20
```

未配置 DLL 时：

- 明文 JSON 导入不受影响。
- 密文导入返回 `T_ENCRYPTED_DRAFT_UNSUPPORTED`。

## 7. 服务端模块设计

### 7.1 解密模块

新增模块：

`vectcut/features/template_filling/draft_content_decryptor.py`

职责：

- 从配置读取 DLL 路径。
- 检查运行平台是否 Windows。
- 加载 DLL 并调用剪映 `EncryptUtils::decrypt`。
- 返回解密后的 bytes。
- 不做业务解析，不保存文件。

接口：

```python
def decrypt_draft_content(cipher: bytes, dll_path: str) -> bytes:
    ...
```

注意：

- 不允许硬编码本机管理员路径。
- DLL ordinal 不同版本可能变化，必须封装版本差异并给出明确错误。
- 日志不得输出原始 draft_content 内容。

### 7.2 导入模块

新增或重构服务函数：

```python
def import_draft_content(template_id: str, content: bytes) -> ImportTemplateResponse:
    ...
```

流程：

1. 校验 `template_id`。
2. 校验文件大小。
3. 尝试按 UTF-8 JSON 解析。
4. 解析失败时尝试解密。
5. 解密后再次 JSON 解析。
6. 明文 JSON 规范化写入模板存储目录。
7. 扫描槽位并返回。

### 7.3 存储

建议存储结构：

```
data/templates/<template_id>/
  draft_content.json        # 明文、规范化后的模板 JSON
  template_meta.json        # 来源信息、导入时间、是否解密、hash
data/template_configs/<template_id>_slots.json
data/generated_drafts/<draft_id>.zip
```

`template_meta.json` 示例：

```json
{
  "template_id": "shuyi_qingdai",
  "source": "draft_content",
  "encrypted_input": true,
  "draft_content_sha256": "...",
  "imported_at": "2026-07-07T12:00:00Z"
}
```

## 8. 桌面端变更

### 8.1 Packer 改名和职责变更

当前 `packer.ts` 负责压缩整个母版文件夹。新模型下它不再打 ZIP。

建议改为：

- `templateReader.ts`
- `readDraftContentFile(folderPath) -> { filePath, bytes, sizeMB }`

验证：

- 母版路径必须是目录。
- 目录下必须存在 `draft_content.json`。
- `draft_content.json` 必须是文件。
- 大小不得超过客户端读取上限，例如 20MB。

### 8.2 API client 新方法

新增：

```typescript
export async function importDraftContentTemplate(
  templateId: string,
  draftContentPath: string,
): Promise<ImportTemplateResult>
```

行为：

- 通过 preload 读取 `draft_content.json` bytes。
- multipart 上传到 `/api/template/import-draft-content`。
- 继续复用 Basic Auth、serverUrl 动态读取、统一 envelope 解析。

### 8.3 素材路径和元数据传递

桌面端选择新素材时，把本机绝对路径和客户端探测元数据写入槽位配置。

要求：

- 文件选择器返回 Windows 绝对路径。
- 客户端读取素材元数据，但不上传新素材 bytes。
- 客户端必须在提交前完成媒体探测；探测失败的素材不能进入渲染请求。
- 服务端只校验路径和元数据的结构，不通过读取素材文件做兜底探测。
- 如果生成草稿要在另一台机器打开，界面应提示素材路径必须在目标机器同样可用。

### 8.4 UI 文案

导入页文案从：

- “选择剪映草稿文件夹，客户端会打包后提交到服务端解析”

改为：

- “选择剪映草稿文件夹，客户端只读取 `draft_content.json` 并提交给服务端解析母版结构”

错误文案：

- 文件缺失：`该目录缺少 draft_content.json，请确认选择的是剪映草稿目录`
- 文件过大：`draft_content.json 超过大小限制`
- 服务端无法解密：`服务端未配置剪映解密能力，请联系部署人员配置 videoeditor.dll`

## 9. 渲染与最小草稿包

导入阶段不上传附件后，生成阶段必须明确“最小可打开草稿包”。

需要验证的最小包候选：

```
generated_draft/
  draft_content.json
  draft_meta_info.json
  draft_virtual_store.json
  draft_settings
  draft_cover.jpg              # 可选，若生成封面
  attachment_pc_common.json    # 通过剪映打开验收决定是否保留
  attachment_editing.json      # 通过剪映打开验收决定是否保留
```

验收方式：

1. 用真实母版 `书亦青黛` 导入。
2. 替换至少 1 个 video、1 个 audio、1 个 subtitle。
3. 生成最小草稿包。
4. 客户端导入剪映草稿目录。
5. 打开剪映确认草稿可见、可打开、无红色丢失素材提示。

若最小包缺文件导致剪映不可打开，则逐项加入必要元文件，并把最终集合写入文档和测试 fixture。

## 10. 错误码

新增错误码：

| code | 场景 |
| --- | --- |
| `T_DRAFT_CONTENT_TOO_LARGE` | 上传的 `draft_content.json` 超过 `max_draft_content_mb` |
| `T_INVALID_DRAFT_CONTENT` | 明文解析失败，或解密后仍不是合法 JSON |
| `T_ENCRYPTED_DRAFT_UNSUPPORTED` | 输入是密文，但服务端未配置解密 DLL |
| `T_DECRYPT_FAILED` | DLL 存在但解密失败 |
| `S_INVALID_LOCATOR` | 槽位 locator 无法定位到轨道或片段 |
| `R_INVALID_MATERIAL_METADATA` | 客户端提交的新素材路径或元数据缺失、类型不匹配、数值非法 |
| `R_UNREPLACED_MATERIAL` | 渲染时仍存在未替换的母版素材引用 |

## 11. 验收标准

### 11.1 自动化验收

- `npm test` 通过。
- `npx tsc --noEmit -p tsconfig.json` 通过。
- `npx tsc --noEmit -p tsconfig.node.json` 通过。
- `python -m pytest tests/features/template_filling -q` 通过。
- 新增服务端测试覆盖：
  - 明文 `draft_content.json` 导入成功。
  - 密文但无 DLL 返回 `T_ENCRYPTED_DRAFT_UNSUPPORTED`。
  - mock 解密成功后导入成功。
  - 超大小返回 `T_DRAFT_CONTENT_TOO_LARGE`。
  - 空 `track.name` 仍能生成可渲染 locator。
  - 渲染请求使用本机素材路径和客户端探测元数据时，服务端不读取素材文件也能生成草稿 JSON。
  - 素材元数据缺失、类型不匹配、数值非法时返回 `R_INVALID_MATERIAL_METADATA`。

### 11.2 真实母版验收

以本机已验证的两个母版作为样本：

- `D:\Program Files (x86)\JianyingPro Drafts\@模板【双楠】`
- `D:\Program Files (x86)\JianyingPro Drafts\书亦青黛`

最低通过标准：

1. 客户端不再创建 200MB+ 草稿 ZIP。
2. 客户端只上传 `draft_content.json`。
3. 服务端可导入密文 `draft_content.json`，并保存明文模板。
4. `书亦青黛` 至少扫描出 35 个 video、1 个 audio、1 个 subtitle，并且槽位 locator 全部可回查。
5. 客户端从 `G:\剪映剪辑\小说素材\素材` 选择一个 video、一个 audio 和字幕文本或字幕文件路径，提交给服务端的是路径和客户端探测元数据，不是素材文件。
6. 服务端不读取这些素材文件，只用路径和元数据组装草稿 JSON，且不再因空 `track_name` 失败。
7. 下载 ZIP 后导入剪映草稿目录，剪映能看到并打开新草稿。

完整通过标准：

- 支持 video/audio/bgm/subtitle/cover_image/cover_title 5 类槽位。
- 所有母版原素材引用要么被新素材替换，要么渲染前明确报错。
- 生成草稿在剪映中打开后，不出现母版素材丢失提示。

## 12. 安全与隐私

- 不上传母版资源文件，降低素材隐私与版权风险。
- `draft_content.json` 和渲染请求都可能包含本机路径、素材文件名、素材元数据、设备信息；日志必须脱敏。
- 解密后的明文模板 JSON 属于用户数据，存储目录应沿用业务数据卷和备份策略。
- 错误响应不得返回完整 JSON 内容。
- 服务端 DLL 路径不得在错误信息里暴露完整敏感目录；日志可记录脱敏路径。
- 用户新素材路径也属于敏感信息；错误响应可返回文件名和槽位，不应返回完整目录树。

## 13. 迁移策略

阶段 1：新增接口，不删除旧 ZIP 接口。

- 桌面端改用新接口。
- 旧测试继续跑。
- 文档标记旧 ZIP 导入为 legacy。

阶段 2：服务端支持密文解密。

- Windows 开发/本地部署优先。
- Docker/Linux 未配置 DLL 时返回明确错误。

阶段 3：重构槽位 locator。

- 新导入结果返回 `locator`。
- 后端保存槽位配置时保留 locator。
- 渲染优先按 locator 定位。

阶段 4：验证最小草稿包。

- 用真实剪映打开验证。
- 固化最小文件集合。

## 14. 待评审问题

1. 服务端是否接受 Windows-only 解密能力作为 MVP 前提？
2. `max_draft_content_mb` 默认 20MB 是否足够覆盖真实母版？
3. 旧 ZIP 导入接口是否保留到下一个大版本再删除？
4. 未替换母版素材引用是直接报错，还是允许用户选择“移除未替换片段”？
5. 最小草稿包是否要优先只验证 Windows 剪映 8.9/10.x？

## 15. 结论

母版导入模型应从“上传完整草稿目录 ZIP”改为“上传单个 `draft_content.json`”。服务端负责解密和结构解析，后端渲染负责确保所有素材引用被新素材替换。这个方向符合产品目标，也直接解决真实母版上传体积、母版素材隐私和客户端 DLL 依赖问题。
