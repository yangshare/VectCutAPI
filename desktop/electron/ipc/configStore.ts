import type { IpcMain } from 'electron';
import { mkdir, readFile, rename, unlink, writeFile } from 'fs/promises';
import { homedir } from 'os';
import { join } from 'path';
import type { UserConfig } from '../../src/types';

export const DEFAULT_SERVER_URL = 'https://api.vectcut.com';
let configWriteQueue: Promise<void> = Promise.resolve();
let tempFileCounter = 0;

export function getDefaultServerUrl(): string {
  return DEFAULT_SERVER_URL;
}

function getConfigPaths() {
  const configDir = join(homedir(), '.vectcut');

  return {
    configDir,
    configFile: join(configDir, 'config.json'),
  };
}

function normalizeUserConfig(value: unknown): UserConfig {
  if (!value || typeof value !== 'object') {
    return {};
  }

  const rawConfig = value as Partial<Record<keyof UserConfig, unknown>>;
  const config: UserConfig = {};

  if (typeof rawConfig.serverUrl === 'string') {
    config.serverUrl = rawConfig.serverUrl;
  }

  if (typeof rawConfig.jianyingDraftDir === 'string') {
    config.jianyingDraftDir = rawConfig.jianyingDraftDir;
  }

  return config;
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && 'code' in error;
}

function enqueueConfigWrite<T>(operation: () => Promise<T>): Promise<T> {
  const result = configWriteQueue.then(operation, operation);
  configWriteQueue = result.then(
    () => undefined,
    () => undefined,
  );

  return result;
}

function createTempConfigFilePath(configFile: string): string {
  tempFileCounter += 1;

  return `${configFile}.${process.pid}.${Date.now()}.${tempFileCounter}.${Math.random()
    .toString(36)
    .slice(2)}.tmp`;
}

async function writeConfigFileAtomically(configFile: string, content: string): Promise<void> {
  const tempFile = createTempConfigFilePath(configFile);

  try {
    await writeFile(tempFile, content, 'utf-8');
    await rename(tempFile, configFile);
  } catch (error) {
    await unlink(tempFile).catch(() => undefined);
    throw error;
  }
}

export async function getUserConfig(): Promise<UserConfig> {
  const { configFile } = getConfigPaths();
  let content: string;

  try {
    content = await readFile(configFile, 'utf-8');
  } catch (error) {
    if (isNodeError(error) && error.code === 'ENOENT') {
      return {};
    }

    throw error;
  }

  try {
    return normalizeUserConfig(JSON.parse(content));
  } catch (error) {
    if (error instanceof SyntaxError) {
      return {};
    }

    throw error;
  }
}

export async function setUserConfig(patch: Partial<UserConfig>): Promise<UserConfig> {
  return enqueueConfigWrite(async () => {
    const { configDir, configFile } = getConfigPaths();
    const merged = normalizeUserConfig({
      ...(await getUserConfig()),
      ...normalizeUserConfig(patch),
    });

    await mkdir(configDir, { recursive: true });
    await writeConfigFileAtomically(configFile, JSON.stringify(merged, null, 2));

    return merged;
  });
}

export async function getServerUrl(): Promise<string> {
  const config = await getUserConfig();

  return config.serverUrl || getDefaultServerUrl();
}

export function registerConfigStoreHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('config:get', () => getUserConfig());
  ipcMain.handle('config:set', (_event, patch: Partial<UserConfig>) => setUserConfig(patch));
}
