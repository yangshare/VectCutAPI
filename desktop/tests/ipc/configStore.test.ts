import { mkdir, mkdtemp, readFile, rm, writeFile } from 'fs/promises';
import os from 'os';
import { dirname, join } from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getDefaultServerUrl,
  getServerUrl,
  getUserConfig,
  setUserConfig,
  registerConfigStoreHandlers,
} from '../../electron/ipc/configStore';

type Handler = (_event?: unknown, ...args: unknown[]) => unknown;

function createFakeIpcMain() {
  const handlers = new Map<string, Handler>();

  return {
    ipcMain: {
      handle: vi.fn((channel: string, handler: Handler) => {
        handlers.set(channel, handler);
      }),
    },
    handlers,
  };
}

describe('configStore', () => {
  let tempHome: string;
  let originalHome: string | undefined;
  let originalUserProfile: string | undefined;

  beforeEach(async () => {
    tempHome = await mkdtemp(join(os.tmpdir(), 'vectcut-config-'));
    originalHome = process.env.HOME;
    originalUserProfile = process.env.USERPROFILE;
    process.env.HOME = tempHome;
    process.env.USERPROFILE = tempHome;
  });

  afterEach(async () => {
    vi.doUnmock('fs/promises');

    if (originalHome === undefined) {
      delete process.env.HOME;
    } else {
      process.env.HOME = originalHome;
    }

    if (originalUserProfile === undefined) {
      delete process.env.USERPROFILE;
    } else {
      process.env.USERPROFILE = originalUserProfile;
    }

    await rm(tempHome, { recursive: true, force: true });
  });

  it('returns an empty config when the config file does not exist', async () => {
    await expect(getUserConfig()).resolves.toEqual({});
  });

  it('returns the default server URL when serverUrl is not configured', async () => {
    await expect(getServerUrl()).resolves.toBe(getDefaultServerUrl());
  });

  it('merges config patches and persists pretty JSON', async () => {
    await expect(setUserConfig({
      serverUrl: 'https://local.vectcut.test',
      basicAuthUsername: 'deploy',
    })).resolves.toEqual({
      serverUrl: 'https://local.vectcut.test',
      basicAuthUsername: 'deploy',
    });

    const merged = await setUserConfig({
      jianyingDraftDir: 'D:\\Jianying\\Drafts',
      basicAuthPassword: 'secret',
    });

    expect(merged).toEqual({
      serverUrl: 'https://local.vectcut.test',
      jianyingDraftDir: 'D:\\Jianying\\Drafts',
      basicAuthUsername: 'deploy',
      basicAuthPassword: 'secret',
    });

    const configPath = join(tempHome, '.vectcut', 'config.json');
    await expect(readFile(configPath, 'utf-8')).resolves.toBe(
      JSON.stringify(merged, null, 2),
    );
  });

  it('serializes concurrent config updates so patches are not lost', async () => {
    await Promise.all([
      setUserConfig({ serverUrl: 'https://concurrent.vectcut.test' }),
      setUserConfig({ jianyingDraftDir: 'D:\\Jianying\\Concurrent' }),
      setUserConfig({ basicAuthUsername: 'admin', basicAuthPassword: 'pw' }),
    ]);

    await expect(getUserConfig()).resolves.toEqual({
      serverUrl: 'https://concurrent.vectcut.test',
      jianyingDraftDir: 'D:\\Jianying\\Concurrent',
      basicAuthUsername: 'admin',
      basicAuthPassword: 'pw',
    });
  });

  it('writes through a same-directory temp file before renaming over config.json', async () => {
    vi.resetModules();

    const writeFileSpy = vi.fn<typeof import('fs/promises').writeFile>();
    const renameSpy = vi.fn<typeof import('fs/promises').rename>();

    vi.doMock('fs/promises', async () => {
      const actual = await vi.importActual<typeof import('fs/promises')>('fs/promises');
      writeFileSpy.mockImplementation(actual.writeFile);
      renameSpy.mockImplementation(actual.rename);

      return {
        ...actual,
        writeFile: writeFileSpy,
        rename: renameSpy,
      };
    });

    const { setUserConfig: setUserConfigWithMockedFs } = await import(
      '../../electron/ipc/configStore'
    );

    await setUserConfigWithMockedFs({ serverUrl: 'https://atomic.vectcut.test' });

    const configPath = join(tempHome, '.vectcut', 'config.json');
    const tempPath = writeFileSpy.mock.calls[0]?.[0] as string;

    expect(writeFileSpy).toHaveBeenCalledOnce();
    expect(tempPath).not.toBe(configPath);
    expect(dirname(tempPath)).toBe(dirname(configPath));
    expect(renameSpy).toHaveBeenCalledWith(tempPath, configPath);
    await expect(readFile(configPath, 'utf-8')).resolves.toBe(
      JSON.stringify({ serverUrl: 'https://atomic.vectcut.test' }, null, 2),
    );
  });

  it('returns an empty config when config JSON is invalid', async () => {
    const configPath = join(tempHome, '.vectcut', 'config.json');
    await mkdir(join(tempHome, '.vectcut'), { recursive: true });
    await writeFile(configPath, '{not valid json', 'utf-8');

    await expect(getUserConfig()).resolves.toEqual({});
  });

  it('rejects non-missing-file read errors instead of hiding them', async () => {
    const configPath = join(tempHome, '.vectcut', 'config.json');
    await mkdir(configPath, { recursive: true });

    await expect(getUserConfig()).rejects.toThrow();
  });

  it('filters unknown config fields when reading and writing', async () => {
    const patch = {
      serverUrl: 'https://filtered.vectcut.test',
      unknown: 'x',
    } as Partial<Parameters<typeof setUserConfig>[0]> & { unknown: string };

    await expect(setUserConfig(patch)).resolves.toEqual({
      serverUrl: 'https://filtered.vectcut.test',
    });

    const configPath = join(tempHome, '.vectcut', 'config.json');
    const persisted = JSON.parse(await readFile(configPath, 'utf-8'));
    expect(persisted).toEqual({
      serverUrl: 'https://filtered.vectcut.test',
    });
  });

  it('treats a null patch as a no-op update', async () => {
    await setUserConfig({ jianyingDraftDir: 'D:\\Jianying\\Drafts' });

    await expect(setUserConfig(null as never)).resolves.toEqual({
      jianyingDraftDir: 'D:\\Jianying\\Drafts',
    });

    const configPath = join(tempHome, '.vectcut', 'config.json');
    const persisted = JSON.parse(await readFile(configPath, 'utf-8'));
    expect(persisted).toEqual({
      jianyingDraftDir: 'D:\\Jianying\\Drafts',
    });
  });

  it('registers config:get and config:set handlers', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();

    registerConfigStoreHandlers(ipcMain as never);

    expect(ipcMain.handle).toHaveBeenCalledTimes(2);
    expect(ipcMain.handle.mock.calls.map(([channel]) => channel)).toEqual([
      'config:get',
      'config:set',
    ]);

    await expect(handlers.get('config:set')?.(undefined, { serverUrl: 'https://ipc.test' }))
      .resolves.toEqual({ serverUrl: 'https://ipc.test' });
    await expect(handlers.get('config:get')?.()).resolves.toEqual({
      serverUrl: 'https://ipc.test',
    });
  });
});
