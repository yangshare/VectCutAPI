import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import type { AxiosRequestConfig } from 'axios';
import type { ImportTemplateResult, RenderDraftResult } from '../../src/api/client';

const axiosRequest = vi.fn();

vi.mock('axios', () => ({
  default: {
    request: axiosRequest,
  },
}));

const zipBytes = new Uint8Array([1, 2, 3, 4]).buffer;

function installVectcutApi(serverUrl?: string) {
  vi.stubGlobal('window', {
    vectcut: {
      readZipFile: vi.fn().mockResolvedValue(zipBytes),
      writeZipFile: vi.fn().mockResolvedValue(undefined),
      selectDraftSavePath: vi.fn().mockResolvedValue('D:\\downloads\\draft.zip'),
      getUserConfig: vi.fn().mockResolvedValue(serverUrl ? { serverUrl } : {}),
    },
  });
}

describe('api client', () => {
  beforeEach(() => {
    vi.resetModules();
    axiosRequest.mockReset();
    installVectcutApi('https://api.one.test');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('imports a template by reading the zip through window.vectcut and posting multipart form data', async () => {
    const { importTemplate } = await import('../../src/api/client');
    const slots = [
      { slot_id: 'video-1', type: 'video', track_name: 'Video', segment_index: 0 },
    ];
    axiosRequest.mockResolvedValueOnce({
      data: {
        success: true,
        output: { template_id: 'tpl-1', slots, message: 'imported' },
        error: null,
      },
    });

    const result = await importTemplate('tpl 1', 'D:\\drafts\\template.zip');

    expect(result).toEqual({ template_id: 'tpl-1', slots, message: 'imported' });
    expect(window.vectcut.readZipFile).toHaveBeenCalledWith('D:\\drafts\\template.zip');
    expect(axiosRequest).toHaveBeenCalledOnce();

    const request = axiosRequest.mock.calls[0][0] as AxiosRequestConfig;
    expect(request.method).toBe('post');
    expect(request.baseURL).toBe('https://api.one.test');
    expect(request.url).toBe('/api/template/import?template_id=tpl%201');
    expect(request.data).toBeInstanceOf(FormData);
    const file = Array.from((request.data as FormData).entries())
      .find(([name]) => name === 'file')?.[1] as File;
    expect(file.name).toBe('tpl 1.zip');
  });

  it('throws backend ApiError objects for failed import envelopes', async () => {
    const { importTemplate } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: {
        success: false,
        output: null,
        error: { code: 'T_INVALID_ZIP', message: 'invalid zip' },
      },
    });

    await expect(importTemplate('tpl-1', 'D:\\drafts\\bad.zip')).rejects.toEqual({
      code: 'T_INVALID_ZIP',
      message: 'invalid zip',
    });
  });

  it('preserves backend ApiError envelopes from rejected axios responses', async () => {
    const { importTemplate } = await import('../../src/api/client');
    axiosRequest.mockRejectedValueOnce({
      response: {
        data: {
          success: false,
          output: null,
          error: { code: 'T_INVALID_ZIP', message: 'bad' },
        },
      },
    });

    await expect(importTemplate('tpl-1', 'D:\\drafts\\bad.zip')).rejects.toEqual({
      code: 'T_INVALID_ZIP',
      message: 'bad',
    });
  });

  it('prefers backend envelopes over axios error codes on rejected API responses', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockRejectedValueOnce({
      code: 'ERR_BAD_REQUEST',
      message: 'Request failed with status code 404',
      response: {
        data: {
          success: false,
          output: null,
          error: {
            code: 'T_NOT_FOUND',
            message: 'template missing',
            details: { template_id: 'tpl1' },
          },
        },
      },
    });

    await expect(saveSlotConfig('tpl1', [])).rejects.toEqual({
      code: 'T_NOT_FOUND',
      message: 'template missing',
      details: { template_id: 'tpl1' },
    });
  });

  it('throws response format errors when an API response is not an envelope', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({ data: { ok: true } });

    await expect(saveSlotConfig('tpl-1', [])).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it.each([
    ['missing output', { success: true, error: null }],
    ['null output', { success: true, output: null, error: null }],
  ])('throws response format errors for successful envelopes with %s', async (_name, envelope) => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({ data: envelope });

    await expect(saveSlotConfig('tpl-1', [])).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it('renders a draft and returns the task id output', async () => {
    const { renderDraft } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: {
        success: true,
        output: {
          draft_id: 'draft-1',
          download_url: '/api/template/download/draft-1',
          warnings: ['trimmed'],
        },
        error: null,
      },
    });

    const result = await renderDraft(
      'tpl-1',
      [{ slot_id: 'video-1', path: 'D:\\media\\v.mp4', duration: 10 }],
      [{ slot_id: 'subtitle_1', srt_content: '1\n00:00:00,000 --> 00:00:01,000\nHi' }],
      { slot_id: 'cover_title_1', text: '标题' },
    );

    expect(result).toEqual({
      task_id: 'draft-1',
      draft_zip_path: '/api/template/download/draft-1',
      warnings: ['trimmed'],
      message: 'ok',
    });
    const request = axiosRequest.mock.calls[0][0] as AxiosRequestConfig;
    expect(request).toEqual(expect.objectContaining({
      method: 'post',
      baseURL: 'https://api.one.test',
      url: '/api/template/render',
    }));
    expect(request.data).toEqual({
      template_id: 'tpl-1',
      slot_values: {
        'video-1': { slot_id: 'video-1', path: 'D:\\media\\v.mp4', duration: 10 },
        subtitle_1: {
          slot_id: 'subtitle_1',
          srt_content: '1\n00:00:00,000 --> 00:00:01,000\nHi',
        },
        cover_title_1: { slot_id: 'cover_title_1', text: '标题' },
      },
      output_draft_name: expect.any(String),
    });
    expect(request.data.output_draft_name).toContain('tpl-1');
  });

  it('posts slot config using the current backend slots contract and adapts slot_count', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: { success: true, output: { slot_count: 2, message: 'saved' }, error: null },
    });

    const result = await saveSlotConfig('tpl-1', [
      { slot_id: 'video-1', type: 'video', track_name: 'Video', segment_index: 0 },
      { slot_id: 'audio-1', type: 'audio', track_name: 'Audio', segment_index: 1 },
    ]);

    expect(result).toEqual({ saved_count: 2, message: 'saved' });
    expect(axiosRequest).toHaveBeenCalledWith(expect.objectContaining({
      method: 'post',
      url: '/api/template/slot-config',
      data: {
        template_id: 'tpl-1',
        slots: [
          {
            slot_id: 'video-1',
            name: 'video-1',
            type: 'video',
            track_name: 'Video',
            segment_index: 0,
            required: true,
          },
          {
            slot_id: 'audio-1',
            name: 'audio-1',
            type: 'audio',
            track_name: 'Audio',
            segment_index: 1,
            required: true,
          },
        ],
      },
    }));
  });

  it('throws response format errors when slot config output has no count', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: { success: true, output: { message: 'saved' }, error: null },
    });

    await expect(saveSlotConfig('tpl-1', [])).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it('throws response format errors when slot config output message is invalid', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: { success: true, output: { slot_count: 1, message: null }, error: null },
    });

    await expect(saveSlotConfig('tpl-1', [])).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it.each([
    ['draft_id', { download_url: '/api/template/download/draft-1', warnings: [] }],
    ['download_url', { draft_id: 'draft-1', warnings: [] }],
    ['warnings array', { draft_id: 'draft-1', download_url: '/api/template/download/draft-1', warnings: 'bad' }],
  ])('throws response format errors when render output has invalid %s', async (_field, output) => {
    const { renderDraft } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: { success: true, output, error: null },
    });

    await expect(renderDraft('tpl-1', [])).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it('throws backend ApiError objects for failed render envelopes', async () => {
    const { renderDraft } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      data: {
        success: false,
        output: null,
        error: { code: 'R_LOOP_TOO_MANY', message: 'too short' },
      },
    });

    await expect(renderDraft('tpl-1', [])).rejects.toEqual({
      code: 'R_LOOP_TOO_MANY',
      message: 'too short',
    });
  });

  it('uses the latest serverUrl on each request instead of caching baseURL permanently', async () => {
    const { saveSlotConfig } = await import('../../src/api/client');
    const getUserConfig = vi.mocked(window.vectcut.getUserConfig);
    getUserConfig
      .mockResolvedValueOnce({ serverUrl: 'https://api.one.test' })
      .mockResolvedValueOnce({ serverUrl: 'https://api.two.test' });
    axiosRequest.mockResolvedValue({
      data: { success: true, output: { saved_count: 1, message: 'ok' }, error: null },
    });

    await saveSlotConfig('tpl-1', [
      { slot_id: 'video-1', type: 'video', track_name: 'Video', segment_index: 0 },
    ]);
    await saveSlotConfig('tpl-1', [
      { slot_id: 'audio-1', type: 'audio', track_name: 'Audio', segment_index: 0 },
    ]);

    expect((axiosRequest.mock.calls[0][0] as AxiosRequestConfig).baseURL).toBe('https://api.one.test');
    expect((axiosRequest.mock.calls[1][0] as AxiosRequestConfig).baseURL).toBe('https://api.two.test');
  });

  it('parses JSON error envelopes from arraybuffer downloads without Buffer', async () => {
    const { downloadDraft } = await import('../../src/api/client');
    const envelope = {
      success: false,
      output: null,
      error: { code: 'R_TASK_NOT_FOUND', message: 'missing task' },
    };
    axiosRequest.mockResolvedValueOnce({
      headers: { 'content-type': 'application/json; charset=utf-8' },
      data: new TextEncoder().encode(JSON.stringify(envelope)).buffer,
    });

    await expect(downloadDraft('task-1', 'D:\\downloads\\draft.zip')).rejects.toEqual({
      code: 'R_TASK_NOT_FOUND',
      message: 'missing task',
    });
  });

  it('throws a response format ApiError when JSON download errors cannot be parsed', async () => {
    const { downloadDraft } = await import('../../src/api/client');
    axiosRequest.mockResolvedValueOnce({
      headers: { 'content-type': 'application/json' },
      data: new TextEncoder().encode('{not json').buffer,
    });

    await expect(downloadDraft('task-1', 'D:\\downloads\\draft.zip')).rejects.toMatchObject({
      code: 'RESPONSE_FORMAT_ERROR',
    });
  });

  it('preserves JSON error envelopes from rejected arraybuffer downloads', async () => {
    const { downloadDraft } = await import('../../src/api/client');
    const envelope = {
      success: false,
      output: null,
      error: { code: 'R_TASK_NOT_FOUND', message: 'missing task' },
    };
    axiosRequest.mockRejectedValueOnce({
      response: {
        headers: { 'content-type': 'application/json' },
        data: new TextEncoder().encode(JSON.stringify(envelope)).buffer,
      },
    });

    await expect(downloadDraft('task-1', 'D:\\downloads\\draft.zip')).rejects.toEqual({
      code: 'R_TASK_NOT_FOUND',
      message: 'missing task',
    });
  });

  it('writes successful draft downloads through the controlled preload API', async () => {
    const { downloadDraft } = await import('../../src/api/client');
    const data = new Uint8Array([0x50, 0x4b, 1, 2]).buffer;
    axiosRequest.mockResolvedValueOnce({
      headers: { 'content-type': 'application/zip' },
      data,
    });

    const result = await downloadDraft('task-1', 'D:\\downloads\\draft.zip');

    expect(result).toBe('D:\\downloads\\draft.zip');
    expect(window.vectcut.writeZipFile).toHaveBeenCalledWith('D:\\downloads\\draft.zip', data);
  });

  it('throws a local save ApiError when preload write rejects', async () => {
    const { downloadDraft } = await import('../../src/api/client');
    const data = new Uint8Array([0x50, 0x4b]).buffer;
    vi.mocked(window.vectcut.writeZipFile).mockRejectedValueOnce(new Error('ZIP 保存路径未授权'));
    axiosRequest.mockResolvedValueOnce({
      headers: { 'content-type': 'application/zip' },
      data,
    });

    await expect(downloadDraft('task-1', 'D:\\downloads\\draft.zip')).rejects.toEqual({
      code: 'LOCAL_SAVE_ERROR',
      message: 'ZIP 保存路径未授权',
    });
  });

  it('does not import electron configStore from the renderer API client', async () => {
    const fs = await import('fs/promises');
    const source = await fs.readFile(new URL('../../src/api/client.ts', import.meta.url), 'utf-8');

    expect(source).not.toContain('electron/ipc/configStore');
  });

  it('does not use Node fs dynamic imports from the renderer API client', async () => {
    const fs = await import('fs/promises');
    const source = await fs.readFile(new URL('../../src/api/client.ts', import.meta.url), 'utf-8');

    expect(source).not.toContain('fs/promises');
    expect(source).not.toContain('new Function');
  });

  it('defines Task 8 result interfaces with required fields only', async () => {
    const fs = await import('fs/promises');
    const source = await fs.readFile(new URL('../../src/api/client.ts', import.meta.url), 'utf-8');

    expect(source).toContain('message: string;');
    expect(source).toContain('task_id: string;');
    expect(source).toContain('draft_zip_path: string;');
    expect(source).toContain('warnings: string[];');
    expect(source).not.toContain('message?: string;');
    expect(source).toContain('export interface RenderDraftResult');
  });

  it('defines subtitle and cover metadata using backend slot schemas', async () => {
    const fs = await import('fs/promises');
    const source = await fs.readFile(new URL('../../src/types.ts', import.meta.url), 'utf-8');

    expect(source).toContain('export interface SubtitleMetadata');
    expect(source).toContain('slot_id: string;');
    expect(source).toContain('srt_content: string;');
    expect(source).toContain('export interface CoverTitleMetadata');
    expect(source).toContain('text: string;');
    expect(source).not.toContain('start_time: number;');
    expect(source).not.toContain('end_time: number;');
    expect(source).not.toContain('title: string;');
  });
});

describe('error message mapping', () => {
  it('returns Chinese user-friendly messages for known error codes', async () => {
    const { getUserFriendlyError } = await import('../../src/api/errorMessages');

    expect(getUserFriendlyError({ code: 'T_INVALID_ZIP', message: 'invalid zip' }))
      .toBe('母版 ZIP 文件格式无效，请检查是否为完整的剪映草稿文件夹');
  });

  it('appends details when provided', async () => {
    const { getUserFriendlyError } = await import('../../src/api/errorMessages');

    expect(getUserFriendlyError({
      code: 'R_LOOP_TOO_MANY',
      message: 'too short',
      details: { audio: 120, video: 10 },
    })).toBe('视频时长远小于配音时长，请增加更多视频片段\n\n详细信息：\naudio: 120\nvideo: 10');
  });

  it('falls back to backend messages for unknown error codes', async () => {
    const { getUserFriendlyError } = await import('../../src/api/errorMessages');

    expect(getUserFriendlyError({ code: 'NEW_ERROR', message: 'new backend error' }))
      .toBe('new backend error');
  });

  it('returns user-friendly messages for local save and response format errors', async () => {
    const { getUserFriendlyError } = await import('../../src/api/errorMessages');

    expect(getUserFriendlyError({ code: 'LOCAL_SAVE_ERROR', message: 'denied' }))
      .toBe('保存文件失败，请重新选择保存位置');
    expect(getUserFriendlyError({ code: 'RESPONSE_FORMAT_ERROR', message: 'bad json' }))
      .toBe('服务器响应格式异常，请稍后重试');
  });
});

describe('api client result types', () => {
  it('requires the Task 8 import template result fields', () => {
    expectTypeOf<ImportTemplateResult>().toEqualTypeOf<{
      template_id: string;
      slots: import('../../src/types').Slot[];
      message: string;
    }>();
  });

  it('requires the Task 8 render draft result fields', () => {
    expectTypeOf<RenderDraftResult>().toEqualTypeOf<{
      task_id: string;
      draft_zip_path: string;
      warnings: string[];
      message: string;
    }>();
  });
});
