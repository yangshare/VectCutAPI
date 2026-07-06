import type { IpcMain } from 'electron';
import { execFile } from 'child_process';
import { existsSync } from 'fs';
import { mkdir, stat } from 'fs/promises';
import os from 'os';
import { basename, extname, join } from 'path';
import { promisify } from 'util';
import { getUserConfig } from './configStore';
import type { UserConfig } from '../../src/types';

const execFileAsync = promisify(execFile);

export function detectDraftDir(): string | null {
  const candidate =
    process.platform === 'win32'
      ? join(os.homedir(), 'AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft')
      : join(os.homedir(), 'Movies/JianyingPro/User Data/Projects/com.lveditor.draft');

  return existsSync(candidate) ? candidate : null;
}

export async function detectVersion(): Promise<string | null> {
  // MVP placeholder; real Jianying version discovery is planned separately.
  return '10.5.0';
}

export function isVersionSupported(version: string): boolean {
  return /^10\.[0-9]\.\d+$/.test(version);
}

export async function importDraft(zipPath: string, draftDir: string): Promise<{ draftDir: string }> {
  let zipStats;
  try {
    zipStats = await stat(zipPath);
  } catch (error) {
    const nodeError = error as NodeJS.ErrnoException;
    if (nodeError.code === 'ENOENT') {
      throw new Error(`导入文件不存在：${zipPath}`);
    }
    throw error;
  }

  if (!zipStats.isFile()) {
    throw new Error(`导入路径不是文件：${zipPath}`);
  }

  if (extname(zipPath).toLowerCase() !== '.zip') {
    throw new Error(`仅支持 .zip 草稿包：${zipPath}`);
  }

  await mkdir(draftDir, { recursive: true });

  const zipBaseName = basename(zipPath).replace(/\.zip$/i, '') || 'imported_draft';
  const targetDir = await createUniqueDraftDir(draftDir, zipBaseName);

  if (process.platform === 'win32') {
    await execFileAsync('powershell.exe', [
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      'Expand-Archive -LiteralPath $args[0] -DestinationPath $args[1] -Force',
      zipPath,
      targetDir,
    ]);
  } else {
    await execFileAsync('unzip', ['-o', zipPath, '-d', targetDir]);
  }

  return { draftDir: targetDir };
}

type ConfigReader = () => Promise<UserConfig>;
type DraftDirDetector = () => string | null;

export async function getConfiguredOrDetectedDraftDir(
  readConfig: ConfigReader = getUserConfig,
  detector: DraftDirDetector = detectDraftDir,
): Promise<string | null> {
  const config = await readConfig();
  const configuredDir = config.jianyingDraftDir?.trim();
  if (configuredDir) {
    return configuredDir;
  }

  return detector();
}

async function createUniqueDraftDir(draftDir: string, baseName: string): Promise<string> {
  for (let index = 0; ; index++) {
    const candidate = join(draftDir, index === 0 ? baseName : `${baseName}_${index}`);
    try {
      await mkdir(candidate);
      return candidate;
    } catch (error) {
      const nodeError = error as NodeJS.ErrnoException;
      if (nodeError.code !== 'EEXIST') {
        throw error;
      }
    }
  }
}

export function registerJianyingHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('jianying:detectDraftDir', () => detectDraftDir());
  ipcMain.handle('jianying:detectVersion', () => detectVersion());
  ipcMain.handle('jianying:importDraft', async (_event, zipPath: string) => {
    const draftDir = await getConfiguredOrDetectedDraftDir();
    if (!draftDir) {
      throw new Error('未找到剪映草稿目录，请在设置中手动指定');
    }

    return importDraft(zipPath, draftDir);
  });
}
