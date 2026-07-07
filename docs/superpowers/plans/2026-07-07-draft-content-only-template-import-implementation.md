# 仅上传 draft_content 的母版导入模型实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把母版导入从“客户端打包完整草稿 ZIP”改为“客户端只提交 `draft_content.json`，服务端解密/解析并用 locator 渲染”。

**架构：** 后端新增 `POST /api/template/import-draft-content`，保存明文 `draft_content.json` 后扫描槽位。槽位配置新增 `locator`，渲染优先按 locator 找轨道和片段，旧 `track_name` 字段只做兼容。桌面端读取母版目录根部 `draft_content.json` bytes 并调用新接口，素材仍由客户端探测元数据，服务端只组装 JSON。

**技术栈：** FastAPI、Pydantic、pyJianYingDraft、Vitest、Electron IPC、Axios。

---

## 文件结构

- 修改：`vectcut/core/config.py`
  - 增加 `jianying_decrypt_dll_path`、`max_draft_content_mb` 配置。
- 创建：`vectcut/features/template_filling/draft_content_decryptor.py`
  - 封装服务端解密入口，支持无 DLL 明确报错；MVP 允许测试中 mock。
- 修改：`vectcut/features/template_filling/storage.py`
  - 增加保存单个明文 `draft_content.json` 的 staging/commit 函数。
- 修改：`vectcut/features/template_filling/service.py`
  - 增加 `import_draft_content`。
  - `_scan_slots_from_template` 生成稳定 `locator`。
  - 渲染优先按 `locator` 定位轨道。
  - 生成草稿时不复制母版附件，只输出新的草稿 JSON 和最小目录。
- 修改：`vectcut/features/template_filling/slot_resolver.py`
  - 增加 locator 解析，保留旧 `track_name` 回退。
- 修改：`vectcut/features/template_filling/schemas.py`
  - `SlotConfig` 接收可选 `locator`。
- 修改：`vectcut/features/template_filling/router.py`
  - 增加 `/import-draft-content` multipart 单文件接口。
- 修改：`vectcut/features/template_filling/material_builder.py`
  - 统一素材元数据错误码为 `R_INVALID_MATERIAL_METADATA`。
- 修改：`desktop/electron/ipc/packer.ts`
  - 改为读取 `draft_content.json`，保留旧函数名兼容或新增 reader 函数。
- 修改：`desktop/electron/preload.ts`、`desktop/src/types.ts`、`desktop/src/api/client.ts`
  - 增加 `readDraftContentFile`/`importDraftContentTemplate` 类型和调用。
- 修改：`desktop/src/pages/TemplateManager.tsx`、`desktop/src/pages/SlotConfig.tsx`
  - 导入流程不再 pack ZIP，slot 配置传 `locator`。
- 测试：
  - `tests/features/template_filling/test_service.py`
  - `tests/features/template_filling/test_service_integration.py`
  - `tests/features/template_filling/test_slot_resolver.py`
  - `desktop/src/*.test.ts`
  - `desktop/electron/ipc/*.test.ts`

## 任务 1：后端单文件 draft_content 导入

- [ ] 编写失败测试：明文 `draft_content.json` bytes 可导入并保存为模板。
- [ ] 编写失败测试：超过 `max_draft_content_mb` 返回 `T_DRAFT_CONTENT_TOO_LARGE`。
- [ ] 编写失败测试：密文且无 DLL 返回 `T_ENCRYPTED_DRAFT_UNSUPPORTED`。
- [ ] 实现配置、解密模块、storage 保存、service 导入和 router 新端点。
- [ ] 运行：`python -m pytest tests/features/template_filling/test_service.py tests/features/template_filling/test_service_integration.py -q`。

## 任务 2：locator 槽位定位

- [ ] 编写失败测试：多个空 `track.name` 轨道扫描出唯一 slot_id 和 locator。
- [ ] 编写失败测试：slot 配置只有 locator、`track_name=""` 时渲染定位成功。
- [ ] 实现 `locator.track_index`/`segment_index` 优先定位，旧 `track_name` 回退。
- [ ] 运行：`python -m pytest tests/features/template_filling/test_slot_resolver.py tests/features/template_filling/test_service.py -q`。

## 任务 3：素材元数据错误码

- [ ] 编写失败测试：缺少 path/duration/width/height 时返回 `R_INVALID_MATERIAL_METADATA`。
- [ ] 修改 `material_builder.py`，保持不访问文件系统。
- [ ] 运行：`python -m pytest tests/features/template_filling -q`。

## 任务 4：桌面端 draft_content reader 和 API

- [ ] 编写失败测试：选择母版目录时只读取根部 `draft_content.json`，不压缩目录。
- [ ] 编写失败测试：API 调用 `/api/template/import-draft-content`，上传文件名为 `draft_content.json`。
- [ ] 实现 IPC/preload/types/api/client 更新。
- [ ] 运行：`cd desktop && npm test -- packer vectcut-api-types`。

## 任务 5：桌面端流程和类型收口

- [ ] 修改 `TemplateManager` 使用新导入函数。
- [ ] 修改 `SlotConfig` 保存 locator。
- [ ] 更新错误文案。
- [ ] 运行：`cd desktop && npm test`、`cd desktop && npx tsc --noEmit -p tsconfig.json`、`cd desktop && npx tsc --noEmit -p tsconfig.node.json`。

## 任务 6：最终验证

- [ ] 运行：`python -m pytest tests/features/template_filling -q`。
- [ ] 运行：`cd desktop && npm test`。
- [ ] 运行：`cd desktop && npm run build`。
- [ ] 运行：`git diff --check`。
