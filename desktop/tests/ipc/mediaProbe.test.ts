import { mkdtemp, rm, writeFile } from 'fs/promises';
import os from 'os';
import { join } from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { ffprobeMock, setFfprobePathMock } = vi.hoisted(() => ({
  ffprobeMock: vi.fn(),
  setFfprobePathMock: vi.fn(),
}));

vi.mock('electron', () => ({
  app: {
    isPackaged: false,
  },
}));

vi.mock('ffprobe-static', () => ({
  default: {
    path: 'mock-ffprobe-path',
  },
}));

vi.mock('fluent-ffmpeg', () => ({
  default: {
    setFfprobePath: setFfprobePathMock,
    ffprobe: ffprobeMock,
  },
}));

import { probeMedia } from '../../electron/ipc/mediaProbe';

describe('probeMedia', () => {
  let tempDir: string;

  beforeEach(async () => {
    ffprobeMock.mockReset();
    tempDir = await mkdtemp(join(os.tmpdir(), 'media-probe-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it('rejects when the media file does not exist', async () => {
    const filePath = join(tempDir, 'missing.mp4');

    await expect(probeMedia(filePath)).rejects.toThrow(`文件不存在：${filePath}`);
    expect(ffprobeMock).not.toHaveBeenCalled();
  });

  it.each(['', '   ', null, { path: 'video.mp4' }])(
    'rejects an invalid media file path before probing %#',
    async (filePath) => {
      const result = probeMedia(filePath as unknown as string);

      await expect(result).rejects.toThrow('媒体文件路径不能为空');
      expect(ffprobeMock).not.toHaveBeenCalled();
    },
  );

  it('returns duration and first video stream dimensions', async () => {
    const filePath = join(tempDir, 'video.mp4');
    await writeFile(filePath, 'mock video content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(null, {
        format: { duration: 12.5 },
        streams: [
          { codec_type: 'audio' },
          { codec_type: 'video', width: 1920, height: 1080 },
        ],
      });
    });

    await expect(probeMedia(filePath)).resolves.toEqual({
      duration: 12.5,
      width: 1920,
      height: 1080,
    });
    expect(setFfprobePathMock).toHaveBeenCalledWith('mock-ffprobe-path');
    expect(ffprobeMock).toHaveBeenCalledWith(filePath, expect.any(Function));
  });

  it('returns undefined dimensions when streams are missing', async () => {
    const filePath = join(tempDir, 'audio.mp3');
    await writeFile(filePath, 'mock audio content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(null, {
        format: { duration: 8 },
      });
    });

    await expect(probeMedia(filePath)).resolves.toEqual({
      duration: 8,
      width: undefined,
      height: undefined,
    });
  });

  it('returns undefined dimensions when no video stream exists', async () => {
    const filePath = join(tempDir, 'audio.mp3');
    await writeFile(filePath, 'mock audio content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(null, {
        format: { duration: 8 },
        streams: [{ codec_type: 'audio' }],
      });
    });

    await expect(probeMedia(filePath)).resolves.toEqual({
      duration: 8,
      width: undefined,
      height: undefined,
    });
  });

  it.each([undefined, null])(
    'returns defaults when ffprobe returns nullish data %#',
    async (probeData) => {
      const filePath = join(tempDir, 'video.mp4');
      await writeFile(filePath, 'mock video content');
      ffprobeMock.mockImplementation((_path, callback) => {
        callback(null, probeData);
      });

      await expect(probeMedia(filePath)).resolves.toEqual({
        duration: 0,
        width: undefined,
        height: undefined,
      });
    },
  );

  it('normalizes string duration to a number', async () => {
    const filePath = join(tempDir, 'video.mp4');
    await writeFile(filePath, 'mock video content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(null, {
        format: { duration: '30.5' },
        streams: [{ codec_type: 'video', width: 1280, height: 720 }],
      });
    });

    await expect(probeMedia(filePath)).resolves.toEqual({
      duration: 30.5,
      width: 1280,
      height: 720,
    });
  });

  it.each([
    {},
    { format: {} },
    { format: { duration: 'not-a-number' } },
    { format: { duration: Infinity } },
  ])('falls back to 0 for missing or invalid duration %#', async (probeData) => {
    const filePath = join(tempDir, 'video.mp4');
    await writeFile(filePath, 'mock video content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(null, {
        ...probeData,
        streams: [{ codec_type: 'video', width: 1280, height: 720 }],
      });
    });

    await expect(probeMedia(filePath)).resolves.toEqual({
      duration: 0,
      width: 1280,
      height: 720,
    });
  });

  it('rejects when ffprobe fails', async () => {
    const filePath = join(tempDir, 'broken.mp4');
    await writeFile(filePath, 'mock video content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback(new Error('invalid data'));
    });

    await expect(probeMedia(filePath)).rejects.toThrow('ffprobe 失败：invalid data');
  });

  it('rejects with a stable message when ffprobe fails with a non-Error value', async () => {
    const filePath = join(tempDir, 'broken.mp4');
    await writeFile(filePath, 'mock video content');
    ffprobeMock.mockImplementation((_path, callback) => {
      callback('invalid data');
    });

    await expect(probeMedia(filePath)).rejects.toThrow('ffprobe 失败：invalid data');
  });
});

describe('mediaProbe module loading', () => {
  it('uses the packaged ffprobe resource path when the app is packaged', async () => {
    const packagedSetFfprobePathMock = vi.fn();
    const resourcesPath = join(os.tmpdir(), 'vectcut-resources');
    const originalResourcesPath = process.resourcesPath;

    vi.resetModules();
    vi.doMock('electron', () => ({
      app: {
        isPackaged: true,
      },
    }));
    vi.doMock('ffprobe-static', () => ({
      default: {
        path: 'dev-ffprobe-path',
      },
    }));
    vi.doMock('fluent-ffmpeg', () => ({
      default: {
        setFfprobePath: packagedSetFfprobePathMock,
        ffprobe: vi.fn(),
      },
    }));

    process.resourcesPath = resourcesPath;
    try {
      await import('../../electron/ipc/mediaProbe');

      expect(packagedSetFfprobePathMock).toHaveBeenCalledWith(
        join(
          resourcesPath,
          'ffprobe',
          'bin',
          process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe',
        ),
      );
    } finally {
      process.resourcesPath = originalResourcesPath;
      vi.doUnmock('electron');
      vi.doUnmock('ffprobe-static');
      vi.doUnmock('fluent-ffmpeg');
    }
  });
});
