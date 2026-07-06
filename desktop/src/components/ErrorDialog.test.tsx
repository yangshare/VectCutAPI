import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { ApiError } from '../api/errorMessages';
import ErrorDialog, { stringifyErrorDetails } from './ErrorDialog';

describe('ErrorDialog', () => {
  it('renders friendly loop-limit copy, technical details, copy action, and close action', () => {
    const error: ApiError = {
      code: 'R_LOOP_TOO_MANY',
      message: 'loop count exceeds limit',
      details: { loop_count: 12 },
    };

    const html = renderToStaticMarkup(<ErrorDialog error={error} onClose={() => undefined} />);

    expect(html).toContain('视频素材不足');
    expect(html).toContain('视频时长远小于配音时长');
    expect(html).toContain('增加视频片段');
    expect(html).toContain('缩短配音时长');
    expect(html).toContain('使用更长素材');
    expect(html).toContain('技术详情');
    expect(html).toContain('R_LOOP_TOO_MANY');
    expect(html).toContain('loop_count');
    expect(html).toContain('复制错误信息');
    expect(html).toContain('关闭');
  });

  it('stringifies unusual error details without crashing render', () => {
    const error = {
      code: 'R_GENERATE_FAILED',
      message: 'failed',
      details: { count: BigInt(1) },
    };

    expect(() => stringifyErrorDetails(error as unknown as ApiError)).not.toThrow();
    expect(stringifyErrorDetails(error as unknown as ApiError)).toContain('[unserializable error details]');
  });
});
