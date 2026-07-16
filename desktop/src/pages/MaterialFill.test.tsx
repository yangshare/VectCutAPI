import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildMaterialFillResult,
  collectSlotFill,
  fitVideoMaterialsToDuration,
  formatSlotFillValue,
  getVideoCoverageError,
  getMaterialFillStatus,
  sortVideoPaths,
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
      selectVideoFiles: vi.fn(),
      selectVideoDirectory: vi.fn(),
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

  it('collects a video directory in natural file-name order', async () => {
    vi.mocked(window.vectcut.selectVideoDirectory).mockResolvedValue({
      directory: 'C:\\clips',
      files: [
        'C:\\clips\\010.mp4',
        'C:\\clips\\002.mp4',
        'C:\\clips\\001.mp4',
      ],
    });
    vi.mocked(window.vectcut.probeMedia).mockImplementation(async (path) => ({
      duration: path.includes('010') ? 10 : 2,
      width: 1080,
      height: 1920,
    }));
    const fill = await collectSlotFill(makeSlot('video_track0', 'video'));

    expect(fill).toEqual({
      kind: 'video-track',
      value: {
        slot_id: 'video_track0',
        directory: 'C:\\clips',
        materials: [
          expect.objectContaining({ path: 'C:\\clips\\001.mp4' }),
          expect.objectContaining({ path: 'C:\\clips\\002.mp4' }),
          expect.objectContaining({ path: 'C:\\clips\\010.mp4' }),
        ],
      },
    });
    expect(formatSlotFillValue(fill)).toContain('目录内 3 个视频');
  });

  it('rejects a directory without supported videos', async () => {
    vi.mocked(window.vectcut.selectVideoDirectory).mockResolvedValue({
      directory: 'C:\\clips',
      files: [],
    });

    await expect(collectSlotFill(makeSlot('video_track0', 'video'))).rejects.toThrow(
      '所选目录中没有支持的视频文件',
    );
    expect(window.vectcut.probeMedia).not.toHaveBeenCalled();
  });

  it('takes videos from the directory until they cover the audio duration', () => {
    const materials = [
      { path: 'C:\\clips\\001.mp4', duration: 3 },
      { path: 'C:\\clips\\002.mp4', duration: 4 },
      { path: 'C:\\clips\\003.mp4', duration: 5 },
      { path: 'C:\\clips\\004.mp4', duration: 6 },
    ];

    const fit = fitVideoMaterialsToDuration(materials, 10);

    expect(fit.materials.map((material) => material.path)).toEqual([
      'C:\\clips\\001.mp4',
      'C:\\clips\\002.mp4',
      'C:\\clips\\003.mp4',
    ]);
    expect(fit.selectedSourceDuration).toBe(12);
    expect(fit.shortage).toBe(0);
  });

  it('reports how much video duration is missing', () => {
    const slots = [makeSlot('video_track0', 'video'), makeSlot('audio_track1', 'audio')];
    const fills = {
      video_track0: {
        kind: 'video-track' as const,
        value: {
          slot_id: 'video_track0',
          directory: 'C:\\clips',
          materials: [{ path: 'C:\\clips\\001.mp4', duration: 3 }],
        },
      },
      audio_track1: {
        kind: 'material' as const,
        value: { slot_id: 'audio_track1', path: 'C:\\voice.mp3', duration: 5.5 },
      },
    };

    expect(getVideoCoverageError(slots, fills, 5.5)).toBe('视频目录总时长不足，还差 2.50 秒');
  });

  it('sorts numbered video names naturally without mutating the selection', () => {
    const paths = ['C:\\clips\\10.mp4', 'C:\\clips\\2.mp4', 'C:\\clips\\1.mp4'];

    expect(sortVideoPaths(paths)).toEqual([
      'C:\\clips\\1.mp4',
      'C:\\clips\\2.mp4',
      'C:\\clips\\10.mp4',
    ]);
    expect(paths[0]).toBe('C:\\clips\\10.mp4');
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

  it('builds confirmation output with media, subtitles, text slots, and cover titles from filled slots', () => {
    const slots = [
      makeSlot('video_1', 'video'),
      makeSlot('subtitle_1', 'subtitle'),
      {
        ...makeSlot('text_title_1', 'subtitle'),
        track_type: 'text',
        segment_count: 1,
      },
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
      { text_title_1: '  每次改这里  ' },
    );

    expect(result).toEqual({
      materials: [
        { slot_id: 'video_1', path: 'C:\\media\\clip.mp4', duration: 12, width: 1920, height: 1080 },
        { slot_id: 'cover_image_1', path: 'C:\\covers\\hero.png', width: 1280, height: 720 },
      ],
      subtitles: [
        { slot_id: 'subtitle_1', srt_content: '1\n00:00:00,000 --> 00:00:01,000\nHi' },
      ],
      textSlots: [
        { slot_id: 'text_title_1', text: '每次改这里' },
      ],
      coverTitles: [
        { slot_id: 'cover_title_1', text: '首屏标题' },
      ],
    });
  });

  it('submits only the directory videos needed to cover the audio track', () => {
    const slots = [makeSlot('video_track0', 'video'), makeSlot('audio_track1', 'audio')];
    const result = buildMaterialFillResult(
      slots,
      {
        video_track0: {
          kind: 'video-track',
          value: {
            slot_id: 'video_track0',
            directory: 'C:\\clips',
            materials: [
              { path: 'C:\\clips\\001.mp4', duration: 3 },
              { path: 'C:\\clips\\002.mp4', duration: 4 },
              { path: 'C:\\clips\\003.mp4', duration: 5 },
              { path: 'C:\\clips\\004.mp4', duration: 6 },
            ],
          },
        },
        audio_track1: {
          kind: 'material',
          value: { slot_id: 'audio_track1', path: 'C:\\voice.mp3', duration: 10 },
        },
      },
      {},
    );

    expect(result.materials[0]).toEqual({
      slot_id: 'video_track0',
      directory: 'C:\\clips',
      materials: [
        { path: 'C:\\clips\\001.mp4', duration: 3 },
        { path: 'C:\\clips\\002.mp4', duration: 4 },
        { path: 'C:\\clips\\003.mp4', duration: 5 },
      ],
    });
  });
});
