import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildMaterialFillResult,
  collectSlotFill,
  formatSlotFillValue,
  getMaterialFillStatus,
} from './MaterialFill';
import type { Slot } from '../types';

function makeSlot(slot_id: string, type: Slot['type']): Slot {
  return {
    slot_id,
    type,
    track_name: 'Track',
    segment_index: 0,
  };
}

function installVectcutApi() {
  vi.stubGlobal('window', {
    vectcut: {
      selectVideoFile: vi.fn(),
      selectAudioFile: vi.fn(),
      selectImageFile: vi.fn(),
      selectSrtFile: vi.fn(),
      readTextFile: vi.fn(),
      probeMedia: vi.fn(),
    },
  });
}

describe('MaterialFill readiness', () => {
  beforeEach(() => {
    installVectcutApi();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('keeps confirmation disabled until every selected slot has material', () => {
    const partial = getMaterialFillStatus(1, 2, false);

    expect(partial.canConfirm).toBe(false);
    expect(partial.buttonLabel).toBe('确认素材（已选 1 / 2）');
  });

  it('enables confirmation only when all slots are filled', () => {
    const complete = getMaterialFillStatus(2, 2, false);

    expect(complete.canConfirm).toBe(true);
    expect(complete.buttonLabel).toBe('确认素材（已选 2 / 2）');
  });

  it('keeps empty slot lists disabled', () => {
    const empty = getMaterialFillStatus(0, 0, false);

    expect(empty.canConfirm).toBe(false);
    expect(empty.buttonLabel).toBe('确认素材（已选 0 / 0）');
  });

  it('collects cover_image through the image picker, probes dimensions, and formats width and height', async () => {
    vi.mocked(window.vectcut.selectImageFile).mockResolvedValue('C:\\covers\\hero.png');
    vi.mocked(window.vectcut.probeMedia).mockResolvedValue({
      duration: 0,
      width: 1280,
      height: 720,
    });

    const fill = await collectSlotFill(makeSlot('cover_image_1', 'cover_image'));

    expect(window.vectcut.selectImageFile).toHaveBeenCalledOnce();
    expect(window.vectcut.selectSrtFile).not.toHaveBeenCalled();
    expect(window.vectcut.probeMedia).toHaveBeenCalledWith('C:\\covers\\hero.png');
    expect(fill).toEqual({
      kind: 'material',
      value: expect.objectContaining({
        slot_id: 'cover_image_1',
        path: 'C:\\covers\\hero.png',
        width: 1280,
        height: 720,
      }),
    });
    expect(formatSlotFillValue(fill)).toContain('1280 x 720');
  });

  it('collects subtitle content through readTextFile instead of submitting an SRT path', async () => {
    const srtContent = '1\n00:00:00,000 --> 00:00:01,000\n你好';
    vi.mocked(window.vectcut.selectSrtFile).mockResolvedValue('C:\\subs\\intro.srt');
    vi.mocked(window.vectcut.readTextFile).mockResolvedValue(srtContent);

    const fill = await collectSlotFill(makeSlot('subtitle_1', 'subtitle'));

    expect(window.vectcut.selectSrtFile).toHaveBeenCalledOnce();
    expect(window.vectcut.readTextFile).toHaveBeenCalledWith('C:\\subs\\intro.srt');
    expect(fill).toEqual({
      kind: 'subtitle',
      value: {
        slot_id: 'subtitle_1',
        srt_content: srtContent,
      },
    });
    expect(formatSlotFillValue(fill)).toBe('已读取字幕内容');
  });

  it('builds confirmation output with media, subtitles, and cover titles from filled slots', () => {
    const slots = [
      makeSlot('video_1', 'video'),
      makeSlot('subtitle_1', 'subtitle'),
      makeSlot('cover_image_1', 'cover_image'),
      makeSlot('cover_title_1', 'cover_title'),
    ];

    const result = buildMaterialFillResult(
      slots,
      {
        video_1: {
          kind: 'material',
          value: { slot_id: 'video_1', path: 'C:\\media\\clip.mp4', duration: 12, width: 1920, height: 1080 },
        },
        subtitle_1: {
          kind: 'subtitle',
          value: { slot_id: 'subtitle_1', srt_content: '1\n00:00:00,000 --> 00:00:01,000\nHi' },
        },
        cover_image_1: {
          kind: 'material',
          value: { slot_id: 'cover_image_1', path: 'C:\\covers\\hero.png', width: 1280, height: 720 },
        },
      },
      { cover_title_1: '  首屏标题  ' },
    );

    expect(result).toEqual({
      materials: [
        { slot_id: 'video_1', path: 'C:\\media\\clip.mp4', duration: 12, width: 1920, height: 1080 },
        { slot_id: 'cover_image_1', path: 'C:\\covers\\hero.png', width: 1280, height: 720 },
      ],
      subtitles: [
        { slot_id: 'subtitle_1', srt_content: '1\n00:00:00,000 --> 00:00:01,000\nHi' },
      ],
      coverTitles: [
        { slot_id: 'cover_title_1', text: '首屏标题' },
      ],
    });
  });
});
