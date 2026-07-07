import type { IpcMain } from 'electron';
import { execFile } from 'child_process';
import { existsSync } from 'fs';
import { mkdir, readdir, readFile, stat } from 'fs/promises';
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

export function parseJianyingVersionFromIni(content: string): string | null {
  for (const line of content.split(/\r?\n/)) {
    const match = /^\s*last_version\s*=\s*([^;#\s]+)/i.exec(line);
    const version = normalizeVersionValue(match?.[1]);
    if (version) {
      return version;
    }
  }

  return null;
}

export function parseJianyingVersionFromPacketXml(content: string): string | null {
  return normalizeVersionValue(parseXmlValue(content, 'full_appver'))
    ?? normalizeVersionValue(parseXmlValue(content, 'appver'));
}

export function selectLatestVersion(versions: string[]): string | null {
  const validVersions = versions
    .map((version) => ({ version: version.trim(), parts: parseVersionParts(version) }))
    .filter((entry): entry is { version: string; parts: number[] } => entry.parts !== null);

  if (validVersions.length === 0) {
    return null;
  }

  validVersions.sort((left, right) => compareVersionParts(right.parts, left.parts));
  return validVersions[0].version;
}

export async function detectVersionFromAppsDir(appsDir: string): Promise<string | null> {
  const iniContent = await readTextOrNull(join(appsDir, 'Configure.ini'));
  const iniVersion = iniContent ? parseJianyingVersionFromIni(iniContent) : null;
  if (iniVersion) {
    return iniVersion;
  }

  const packetXmlContent = await readTextOrNull(join(appsDir, 'JianyingProPacket.xml'));
  const packetXmlVersion = packetXmlContent ? parseJianyingVersionFromPacketXml(packetXmlContent) : null;
  if (packetXmlVersion) {
    return packetXmlVersion;
  }

  try {
    const entries = await readdir(appsDir, { withFileTypes: true });
    return selectLatestVersion(entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name));
  } catch {
    return null;
  }
}

export async function detectVersion(): Promise<string | null> {
  try {
    if (process.platform === 'win32') {
      return detectVersionFromWindowsLocalAppData(process.env.LOCALAPPDATA);
    }

    if (process.platform === 'darwin') {
      return detectVersionFromMacApplications();
    }

    return null;
  } catch {
    return null;
  }
}

export function isVersionSupported(version: string): boolean {
  const match = /^(\d+)\.(\d+)\.\d+(?:\.\d+)*$/.exec(version.trim());
  if (!match) {
    return false;
  }

  const major = Number.parseInt(match[1], 10);
  const minor = Number.parseInt(match[2], 10);
  return major === 10 && minor >= 0 && minor <= 9;
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

function parseXmlValue(content: string, tagName: string): string | null {
  const match = new RegExp(`<${tagName}\\b[^>]*\\bvalue\\s*=\\s*["']([^"']+)["'][^>]*>`, 'i').exec(content);
  return match?.[1]?.trim() || null;
}

function normalizeVersionValue(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  return parseVersionParts(trimmed) ? trimmed : null;
}

function parseVersionParts(version: string): number[] | null {
  const trimmed = version.trim();
  if (!/^\d+\.\d+\.\d+(?:\.\d+)*$/.test(trimmed)) {
    return null;
  }

  return trimmed.split('.').map((part) => Number.parseInt(part, 10));
}

function compareVersionParts(left: number[], right: number[]): number {
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index++) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference !== 0) {
      return difference;
    }
  }

  return 0;
}

async function readTextOrNull(filePath: string): Promise<string | null> {
  try {
    return await readFile(filePath, 'utf8');
  } catch {
    return null;
  }
}

function detectVersionFromWindowsLocalAppData(localAppData: string | undefined): Promise<string | null> {
  const baseDir = localAppData?.trim() || join(os.homedir(), 'AppData', 'Local');
  return detectVersionFromAppsDir(join(baseDir, 'JianyingPro', 'Apps'));
}

async function detectVersionFromMacApplications(): Promise<string | null> {
  const candidates = [
    join('/Applications', 'JianyingPro.app', 'Contents', 'Info.plist'),
    join(os.homedir(), 'Applications', 'JianyingPro.app', 'Contents', 'Info.plist'),
  ];

  for (const candidate of candidates) {
    const content = await readTextOrNull(candidate);
    const version = content ? parseVersionFromInfoPlist(content) : null;
    if (version) {
      return version;
    }
  }

  return null;
}

export function parseVersionFromInfoPlist(content: string): string | null {
  return normalizeVersionValue(parsePlistStringValue(content, 'CFBundleShortVersionString'))
    ?? normalizeVersionValue(parsePlistStringValue(content, 'CFBundleVersion'));
}

function parsePlistStringValue(content: string, key: string): string | null {
  const match = new RegExp(`<key>\\s*${key}\\s*</key>\\s*<string>\\s*([^<]+)\\s*</string>`, 'i').exec(content);
  return match?.[1]?.trim() || null;
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
