/** 错误码 -> 用户友好提示映射（与后端 errors.py ERROR_CODES 对齐）。 */
export const ERROR_MESSAGES: Record<string, string> = {
  // 模板错误 (T_xxx)
  T_NOT_FOUND: '模板不存在，请重新导入母版',
  T_INVALID_ZIP: '母版 ZIP 文件格式无效，请检查是否为完整的剪映草稿文件夹',
  T_TOO_LARGE: '母版文件过大（超过 50MB），请精简母版内容',
  T_NO_DRAFT_CONTENT: 'ZIP 中缺少 draft_content.json 文件，请确认是否为剪映草稿',
  T_INVALID_ID: '模板 ID 非法',
  // 槽位错误 (S_xxx)
  S_NOT_FOUND: '槽位配置不存在，请重新配置',
  S_TRACK_NOT_FOUND: '母版中找不到指定轨道，母版可能已被修改，请重新导入',
  S_SEGMENT_NOT_FOUND: '母版中找不到指定片段，母版可能已被修改，请重新导入',
  S_TYPE_MISMATCH: '槽位类型与轨道类型不匹配，请检查配置',
  S_INVALID_SLOT: '槽位 ID 在母版中不存在',
  // 生成错误 (R_xxx)
  R_MISSING_SLOT: '有必填槽位未填写，请检查素材是否完整',
  R_INVALID_PATH: '素材路径格式无效，请选择有效的本地文件',
  R_INVALID_DURATION: '素材时长异常（可能为 0 或过大），请检查文件是否损坏',
  R_LOOP_TOO_MANY: '视频时长远小于配音时长，请增加更多视频片段',
  R_SRT_PARSE_ERROR: 'SRT 字幕文件格式错误，请检查时间轴格式',
  R_GENERATE_FAILED: '草稿生成失败，请查看详细错误信息',
  R_EMPTY_VIDEO: '视频槽位为空，无法生成草稿',
  R_ZERO_DURATION: '素材总时长为 0',
  R_TASK_NOT_FOUND: '草稿任务不存在或已过期，请重新生成',
  R_INVALID_TASK: 'task_id 非法',
  // 通用
  INTERNAL_ERROR: '服务器内部错误，请稍后重试或联系技术支持',
  NETWORK_ERROR: '网络连接失败，请检查网络或服务器地址',
  RESPONSE_FORMAT_ERROR: '服务器响应格式异常，请稍后重试',
  LOCAL_SAVE_ERROR: '保存文件失败，请重新选择保存位置',
};

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** 把后端错误转成用户可读的提示。 */
export function getUserFriendlyError(error: ApiError): string {
  const base = ERROR_MESSAGES[error.code] || error.message;
  if (error.details && Object.keys(error.details).length > 0) {
    const detailsText = Object.entries(error.details)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n');
    return `${base}\n\n详细信息：\n${detailsText}`;
  }
  return base;
}

function isApiError(error: unknown): error is ApiError {
  return Boolean(
    error
      && typeof error === 'object'
      && 'code' in error
      && typeof (error as { code: unknown }).code === 'string'
      && 'message' in error
      && typeof (error as { message: unknown }).message === 'string',
  );
}

function hasMessage(error: unknown): error is { message: string } {
  return Boolean(
    error
      && typeof error === 'object'
      && 'message' in error
      && typeof (error as { message: unknown }).message === 'string',
  );
}

export function formatUserFacingError(error: unknown): string {
  if (isApiError(error)) {
    return getUserFriendlyError(error);
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (hasMessage(error)) {
    return error.message;
  }

  if (error && typeof error === 'object') {
    try {
      const serialized = JSON.stringify(error);
      return serialized || '操作失败，请重试';
    } catch {
      return '操作失败，请重试';
    }
  }

  return String(error);
}
