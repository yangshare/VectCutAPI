import { execFile } from 'child_process';
import { randomUUID } from 'crypto';
import type { IpcMain } from 'electron';
import { existsSync, statSync } from 'fs';
import { mkdir, readFile, stat } from 'fs/promises';
import os from 'os';
import { basename, join } from 'path';

export interface PackTemplateResult {
  zipPath: string;
  sizeMB: number;
}

export interface DraftContentReadResult {
  filePath: string;
  bytes: Buffer;
  sizeMB: number;
}

export interface PackCommand {
  command: string;
  args: string[];
  options?: {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
  };
}

export function validateTemplateFolder(folderPath: string): void {
  if (!existsSync(folderPath)) {
    throw new Error(`母版文件夹不存在：${folderPath}`);
  }

  const folderStats = statSync(folderPath);
  if (!folderStats.isDirectory()) {
    throw new Error(`母版路径不是文件夹：${folderPath}`);
  }

  const draftContentPath = join(folderPath, 'draft_content.json');
  if (!existsSync(draftContentPath)) {
    throw new Error('母版文件夹缺少 draft_content.json，请确认是剪映草稿目录');
  }

  const draftContentStats = statSync(draftContentPath);
  if (!draftContentStats.isFile()) {
    throw new Error(`draft_content.json 不是文件：${draftContentPath}`);
  }
}

export async function readDraftContentFile(
  folderPath: string,
  maxBytes = 20 * 1024 * 1024,
): Promise<DraftContentReadResult> {
  validateTemplateFolder(folderPath);

  const draftContentPath = join(folderPath, 'draft_content.json');
  const draftContentStats = await stat(draftContentPath);
  if (draftContentStats.size > maxBytes) {
    throw new Error('draft_content.json 超过大小限制');
  }

  return {
    filePath: draftContentPath,
    bytes: await readFile(draftContentPath),
    sizeMB: draftContentStats.size / 1024 / 1024,
  };
}

function createZipPath(folderPath: string, outputDir: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return join(outputDir, `${basename(folderPath)}-${timestamp}-${randomUUID()}.zip`);
}

export function buildPackCommand(
  platform: NodeJS.Platform,
  folderPath: string,
  zipPath: string,
): PackCommand {
  if (platform === 'win32') {
    return {
      command: 'powershell.exe',
      args: [
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        "$ErrorActionPreference = 'Stop'; Get-ChildItem -LiteralPath $env:VECTCUT_PACK_SOURCE -Force | Compress-Archive -DestinationPath $env:VECTCUT_PACK_DEST -Force",
      ],
      options: {
        env: {
          VECTCUT_PACK_SOURCE: folderPath,
          VECTCUT_PACK_DEST: zipPath,
        },
      },
    };
  }

  return {
    command: 'zip',
    args: ['-r', zipPath, '.'],
    options: { cwd: folderPath },
  };
}

function runCommand({ command, args, options }: PackCommand): Promise<void> {
  const execOptions = options?.env
    ? {
        ...options,
        env: { ...process.env, ...options.env },
      }
    : (options ?? {});

  return new Promise((resolve, reject) => {
    execFile(command, args, execOptions, (error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

export async function packTemplateFolder(
  folderPath: string,
  outputDir = os.tmpdir(),
): Promise<PackTemplateResult> {
  validateTemplateFolder(folderPath);
  await mkdir(outputDir, { recursive: true });

  const zipPath = createZipPath(folderPath, outputDir);
  await runCommand(buildPackCommand(process.platform, folderPath, zipPath));

  const zipStats = await stat(zipPath);
  return {
    zipPath,
    sizeMB: zipStats.size / 1024 / 1024,
  };
}

export function registerPackerHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('packer:pack', (_event, folderPath: string) => packTemplateFolder(folderPath));
  ipcMain.handle('packer:readDraftContent', (_event, folderPath: string) =>
    readDraftContentFile(folderPath));
}
