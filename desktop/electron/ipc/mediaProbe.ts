import { app, type IpcMain } from 'electron';
import { existsSync } from 'fs';
import { join } from 'path';
import ffmpeg from 'fluent-ffmpeg';
import ffprobePath from 'ffprobe-static';
import type { ProbeResult } from '../../src/types';

const ffprobeActualPath = app.isPackaged
  ? join(
      process.resourcesPath,
      'ffprobe',
      'bin',
      process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe',
    )
  : ffprobePath.path;

ffmpeg.setFfprobePath(ffprobeActualPath);

export function probeMedia(filePath: string): Promise<ProbeResult> {
  if (typeof filePath !== 'string' || filePath.trim().length === 0) {
    return Promise.reject(new Error('媒体文件路径不能为空'));
  }

  if (!existsSync(filePath)) {
    return Promise.reject(new Error(`文件不存在：${filePath}`));
  }

  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(filePath, (err, data) => {
      if (err) {
        const message = err instanceof Error ? err.message : String(err);
        reject(new Error(`ffprobe 失败：${message}`));
        return;
      }

      const streams = Array.isArray(data?.streams) ? data.streams : [];
      const rawDuration = data?.format?.duration;
      const duration = Number(rawDuration);
      const videoStream = streams.find((stream) => stream.codec_type === 'video');
      resolve({
        duration: Number.isFinite(duration) ? duration : 0,
        width: videoStream?.width,
        height: videoStream?.height,
      });
    });
  });
}

export function registerMediaProbeHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('mediaProbe:probe', (_event, filePath: string) => probeMedia(filePath));
}
