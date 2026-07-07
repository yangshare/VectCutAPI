import axios, { type AxiosRequestConfig } from 'axios';
import type {
  ApiEnvelope,
  CoverTitleMetadata,
  MaterialMetadata,
  Slot,
  SlotMapping,
  SubtitleMetadata,
  UserConfig,
} from '../types';
import type { ApiError } from './errorMessages';

const DEFAULT_SERVER_URL = 'https://api.vectcut.com';

export interface ImportTemplateResult {
  template_id: string;
  slots: Slot[];
  message: string;
}

export interface RenderDraftResult {
  task_id: string;
  draft_zip_path: string;
  warnings: string[];
  message: string;
}

interface SaveSlotConfigBackendResult {
  saved_count?: number;
  slot_count?: number;
  message: string;
}

interface RenderDraftBackendResult {
  draft_id: string;
  download_url: string;
  warnings?: string[];
}

interface ApiRequestContext {
  baseURL: string;
  auth?: {
    username: string;
    password: string;
  };
}

function normalizeServerUrl(serverUrl: string | undefined): string {
  const trimmed = serverUrl?.trim();
  return trimmed ? trimmed.replace(/\/+$/, '') : DEFAULT_SERVER_URL;
}

async function getRequestContext(): Promise<ApiRequestContext> {
  try {
    const config = await window.vectcut.getUserConfig();
    return buildRequestContext(config);
  } catch {
    return { baseURL: DEFAULT_SERVER_URL };
  }
}

function buildRequestContext(config: UserConfig): ApiRequestContext {
  const context: ApiRequestContext = {
    baseURL: normalizeServerUrl(config.serverUrl),
  };
  const auth = buildBasicAuth(config);
  if (auth) {
    context.auth = auth;
  }

  return context;
}

function buildBasicAuth(config: UserConfig): ApiRequestContext['auth'] {
  const username = config.basicAuthUsername?.trim() ?? '';
  const password = config.basicAuthPassword ?? '';
  if (!username && !password) {
    return undefined;
  }

  return { username, password };
}

export function extractError<T>(envelope: ApiEnvelope<T>): ApiError | null {
  if (envelope.success || !envelope.error) {
    return null;
  }

  if (typeof envelope.error === 'string') {
    return { code: 'UNKNOWN', message: envelope.error };
  }

  return envelope.error;
}

function unwrapEnvelope<T>(envelope: unknown): T {
  if (!isApiEnvelope(envelope)) {
    throw makeResponseFormatError('服务器响应缺少统一信封');
  }

  const error = extractError(envelope);
  if (error) {
    throw error;
  }

  if (!envelope.success) {
    throw { code: 'UNKNOWN', message: '请求失败' } satisfies ApiError;
  }

  if (!('output' in envelope) || envelope.output == null) {
    throw makeResponseFormatError('服务器响应缺少输出数据');
  }

  return envelope.output as T;
}

async function requestEnvelope<T>(config: AxiosRequestConfig): Promise<T> {
  const requestContext = await getRequestContext();

  try {
    const response = await axios.request<ApiEnvelope<T>>({
      ...config,
      ...requestContext,
    });

    return unwrapEnvelope(response.data);
  } catch (error) {
    const responseError = extractResponseError(error);
    if (responseError) {
      throw responseError;
    }

    if (isApiError(error)) {
      throw error;
    }

    throw { code: 'NETWORK_ERROR', message: 'Network request failed' } satisfies ApiError;
  }
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

function makeResponseFormatError(message: string): ApiError {
  return { code: 'RESPONSE_FORMAT_ERROR', message };
}

function extractResponseError(error: unknown): ApiError | null {
  if (!error || typeof error !== 'object' || !('response' in error)) {
    return null;
  }

  const response = (error as { response?: { data?: unknown } }).response;
  if (!response) {
    return null;
  }

  const envelope = parseResponseData(response.data);
  if (!isApiEnvelope(envelope)) {
    throw makeResponseFormatError('服务器错误响应格式异常');
  }

  const apiError = extractError(envelope);
  if (apiError) {
    return apiError;
  }

  throw makeResponseFormatError('服务器错误响应格式异常');
}

function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return Boolean(
    value
      && typeof value === 'object'
      && typeof (value as { success?: unknown }).success === 'boolean'
      && 'success' in value
      && 'error' in value,
  );
}

function isJsonContentType(headers: unknown): boolean {
  if (!headers || typeof headers !== 'object') {
    return false;
  }

  const value = (headers as Record<string, unknown>)['content-type']
    ?? (headers as Record<string, unknown>)['Content-Type'];

  return typeof value === 'string' && value.toLowerCase().includes('application/json');
}

function decodeJsonEnvelope<T>(data: ArrayBuffer): ApiEnvelope<T> {
  try {
    return JSON.parse(new TextDecoder().decode(data)) as ApiEnvelope<T>;
  } catch (error) {
    throw makeResponseFormatError(error instanceof Error ? error.message : 'Invalid JSON response');
  }
}

function parseResponseData(data: unknown): unknown {
  if (data instanceof ArrayBuffer) {
    return parseJsonText(new TextDecoder().decode(data));
  }

  if (data instanceof Uint8Array) {
    return parseJsonText(new TextDecoder().decode(data));
  }

  if (typeof data === 'string') {
    return parseJsonText(data);
  }

  return data;
}

function parseJsonText(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw makeResponseFormatError(error instanceof Error ? error.message : 'Invalid JSON response');
  }
}

/** 导入母版 ZIP，返回解析出的槽位列表。 */
export async function importTemplate(
  templateId: string,
  zipPath: string,
): Promise<ImportTemplateResult> {
  const zipContent = await window.vectcut.readZipFile(zipPath);
  const formData = new FormData();
  formData.append('file', new Blob([zipContent], { type: 'application/zip' }), `${templateId}.zip`);

  return requestEnvelope<ImportTemplateResult>({
    method: 'post',
    url: `/api/template/import?template_id=${encodeURIComponent(templateId)}`,
    data: formData,
  });
}

/** 导入母版 draft_content.json，返回解析出的槽位列表。 */
export async function importDraftContentTemplate(
  templateId: string,
  templateFolderPath: string,
): Promise<ImportTemplateResult> {
  const draftContent = await window.vectcut.readDraftContentFile(templateFolderPath);
  const formData = new FormData();
  formData.append(
    'file',
    new Blob([draftContent.bytes], { type: 'application/json' }),
    'draft_content.json',
  );

  return requestEnvelope<ImportTemplateResult>({
    method: 'post',
    url: `/api/template/import-draft-content?template_id=${encodeURIComponent(templateId)}`,
    data: formData,
  });
}

/** 保存模板槽位配置。 */
export async function saveSlotConfig(
  templateId: string,
  slotMappings: SlotMapping[],
): Promise<{ saved_count: number; message: string }> {
  const output = await requestEnvelope<SaveSlotConfigBackendResult>({
    method: 'post',
    url: '/api/template/slot-config',
    data: {
      template_id: templateId,
      slots: slotMappings.map((slot) => ({
        slot_id: slot.slot_id,
        name: slot.slot_id,
        type: slot.type,
        track_name: slot.track_name,
        segment_index: slot.segment_index,
        ...(slot.locator ? { locator: slot.locator } : {}),
        required: true,
      })),
    },
  });

  if (!isSaveSlotConfigBackendResult(output)) {
    throw makeResponseFormatError('槽位保存响应格式异常');
  }

  return {
    saved_count: output.saved_count ?? output.slot_count ?? 0,
    message: output.message,
  };
}

/** 根据槽位素材生成草稿任务。 */
export async function renderDraft(
  templateId: string,
  materials: MaterialMetadata[],
  subtitles?: SubtitleMetadata[],
  coverTitles?: CoverTitleMetadata[],
): Promise<RenderDraftResult> {
  const output = await requestEnvelope<RenderDraftBackendResult>({
    method: 'post',
    url: '/api/template/render',
    data: {
      template_id: templateId,
      slot_values: buildSlotValues(materials, subtitles, coverTitles),
      output_draft_name: `${templateId}-${Date.now()}`,
    },
  });

  if (!isRenderDraftBackendResult(output)) {
    throw makeResponseFormatError('草稿生成响应格式异常');
  }

  return {
    task_id: output.draft_id,
    draft_zip_path: output.download_url,
    warnings: output.warnings ?? [],
    message: 'ok',
  };
}

function isSaveSlotConfigBackendResult(value: unknown): value is SaveSlotConfigBackendResult {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const result = value as Partial<SaveSlotConfigBackendResult>;
  const count = result.saved_count ?? result.slot_count;
  return typeof result.message === 'string' && typeof count === 'number';
}

function isRenderDraftBackendResult(value: unknown): value is RenderDraftBackendResult {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const result = value as Partial<RenderDraftBackendResult>;
  return typeof result.draft_id === 'string'
    && typeof result.download_url === 'string'
    && (result.warnings === undefined || Array.isArray(result.warnings));
}

/** 下载生成后的草稿 ZIP 到本地路径。 */
export async function downloadDraft(taskId: string, savePath: string): Promise<string> {
  const requestContext = await getRequestContext();

  try {
    const response = await axios.request<ArrayBuffer>({
      method: 'get',
      ...requestContext,
      url: `/api/template/download/${encodeURIComponent(taskId)}`,
      responseType: 'arraybuffer',
    });

    if (isJsonContentType(response.headers)) {
      unwrapEnvelope(decodeJsonEnvelope<never>(response.data));
    }

    try {
      await window.vectcut.writeZipFile(savePath, response.data);
    } catch (error) {
      throw {
        code: 'LOCAL_SAVE_ERROR',
        message: error instanceof Error ? error.message : 'Local save failed',
      } satisfies ApiError;
    }
    return savePath;
  } catch (error) {
    const responseError = extractResponseError(error);
    if (responseError) {
      throw responseError;
    }

    if (isApiError(error)) {
      throw error;
    }

    throw { code: 'NETWORK_ERROR', message: 'Network request failed' } satisfies ApiError;
  }
}

function buildSlotValues(
  materials: MaterialMetadata[],
  subtitles?: SubtitleMetadata[],
  coverTitles?: CoverTitleMetadata[],
): Record<string, unknown> {
  const values: Record<string, unknown> = {};

  for (const material of materials) {
    values[material.slot_id] = material;
  }

  for (const subtitle of subtitles ?? []) {
    values[subtitle.slot_id] = subtitle;
  }

  for (const coverTitle of coverTitles ?? []) {
    values[coverTitle.slot_id] = coverTitle;
  }

  return values;
}
