import { mkdir, mkdtemp, writeFile } from 'fs/promises';
import os from 'os';
import { join } from 'path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  detectVersion,
  detectVersionFromAppsDir,
  getConfiguredOrDetectedDraftDir,
  importDraft,
  isVersionSupported,
  parseJianyingVersionFromIni,
  parseJianyingVersionFromPacketXml,
  parseVersionFromInfoPlist,
  selectLatestVersion,
} from '../../electron/ipc/jianyingDir';

const { execFileMock } = vi.hoisted(() => ({
  execFileMock: vi.fn((_file, _args, optionsOrCallback, maybeCallback) => {
    const callback = typeof optionsOrCallback === 'function' ? optionsOrCallback : maybeCallback;
    callback(null, '', '');
  }),
}));

vi.mock('child_process', () => ({
  execFile: execFileMock,
}));

describe('isVersionSupported', () => {
  it.each(['10.0.0', '10.5.3', '10.9.9', '10.9.10', '10.9.0.12345'])('supports %s', (version) => {
    expect(isVersionSupported(version)).toBe(true);
  });

  it.each(['11.0.0', '9.8.0', '10.10.0', '10.9.beta', '10.9.', '10.9', 'abc', ''])('rejects %s', (version) => {
    expect(isVersionSupported(version)).toBe(false);
  });
});

describe('Jianying version discovery', () => {
  it('parses last_version from Configure.ini', () => {
    expect(parseJianyingVersionFromIni('[jianyingpro]\nlast_version=8.9.0.13361\n')).toBe('8.9.0.13361');
  });

  it('parses full_appver from packet XML before appver', () => {
    expect(parseJianyingVersionFromPacketXml(`
      <root>
        <appver value="8.9.0" />
        <full_appver value="8.9.0.13361" />
      </root>
    `)).toBe('8.9.0.13361');
  });

  it('treats malformed ini and XML versions as parse failures', () => {
    expect(parseJianyingVersionFromIni('[jianyingpro]\nlast_version=not-a-version\n')).toBeNull();
    expect(parseJianyingVersionFromPacketXml('<full_appver value="not-a-version" /><appver value="also-bad" />')).toBeNull();
  });

  it('falls back to CFBundleVersion when CFBundleShortVersionString is malformed', () => {
    expect(parseVersionFromInfoPlist(`
      <plist>
        <dict>
          <key>CFBundleShortVersionString</key>
          <string>10.9.beta</string>
          <key>CFBundleVersion</key>
          <string>10.9.0.12345</string>
        </dict>
      </plist>
    `)).toBe('10.9.0.12345');
  });

  it('returns null when all Info.plist version fields are malformed', () => {
    expect(parseVersionFromInfoPlist(`
      <plist>
        <dict>
          <key>CFBundleShortVersionString</key>
          <string>10.9.beta</string>
          <key>CFBundleVersion</key>
          <string>10.9.</string>
        </dict>
      </plist>
    `)).toBeNull();
  });

  it('selects the latest semantic version from directory names', () => {
    expect(selectLatestVersion(['10.0.9', '10.9.10', '10.10.0', 'not-a-version', '9.9.99'])).toBe('10.10.0');
  });

  it('detects version from Apps dir with ini before XML before directory fallback', async () => {
    const appsDir = await mkdtemp(join(os.tmpdir(), 'jianying-apps-'));
    await mkdir(join(appsDir, '10.8.0.1'));
    await writeFile(join(appsDir, 'JianyingProPacket.xml'), '<appver value="10.7.0" /><full_appver value="10.7.0.999" />');
    await writeFile(join(appsDir, 'Configure.ini'), '[jianyingpro]\nlast_version=10.6.0.123\n');

    await expect(detectVersionFromAppsDir(appsDir)).resolves.toBe('10.6.0.123');
  });

  it('falls back from XML to version directories', async () => {
    const xmlAppsDir = await mkdtemp(join(os.tmpdir(), 'jianying-apps-'));
    await writeFile(join(xmlAppsDir, 'JianyingProPacket.xml'), '<appver value="10.7.0" /><full_appver value="10.7.0.999" />');
    await mkdir(join(xmlAppsDir, '10.8.0.1'));

    await expect(detectVersionFromAppsDir(xmlAppsDir)).resolves.toBe('10.7.0.999');

    const dirAppsDir = await mkdtemp(join(os.tmpdir(), 'jianying-apps-'));
    await mkdir(join(dirAppsDir, '10.7.9'));
    await mkdir(join(dirAppsDir, '10.8.0.1'));

    await expect(detectVersionFromAppsDir(dirAppsDir)).resolves.toBe('10.8.0.1');
  });

  it('falls back when higher-priority version files are malformed', async () => {
    const appsDir = await mkdtemp(join(os.tmpdir(), 'jianying-apps-'));
    await writeFile(join(appsDir, 'Configure.ini'), '[jianyingpro]\nlast_version=not-a-version\n');
    await writeFile(join(appsDir, 'JianyingProPacket.xml'), '<full_appver value="bad" /><appver value="10.7.0" />');

    await expect(detectVersionFromAppsDir(appsDir)).resolves.toBe('10.7.0');
  });

  it('returns null when no version source exists', async () => {
    const appsDir = await mkdtemp(join(os.tmpdir(), 'jianying-apps-'));

    await expect(detectVersionFromAppsDir(appsDir)).resolves.toBeNull();
  });

  it('detectVersion reads LOCALAPPDATA instead of returning the old fixed placeholder', async () => {
    const localAppData = await mkdtemp(join(os.tmpdir(), 'jianying-local-'));
    const previousLocalAppData = process.env.LOCALAPPDATA;
    const restorePlatform = stubProcessPlatform('win32');
    process.env.LOCALAPPDATA = localAppData;
    const appsDir = join(localAppData, 'JianyingPro', 'Apps');
    await mkdir(appsDir, { recursive: true });
    await writeFile(join(appsDir, 'Configure.ini'), '[jianyingpro]\nlast_version=10.8.0.2468\n');

    try {
      await expect(detectVersion()).resolves.toBe('10.8.0.2468');
    } finally {
      restoreLocalAppData(previousLocalAppData);
      restorePlatform();
    }
  });

  it('does not read Windows LOCALAPPDATA version sources on non-Windows platforms', async () => {
    const localAppData = await mkdtemp(join(os.tmpdir(), 'jianying-local-'));
    const previousLocalAppData = process.env.LOCALAPPDATA;
    const restorePlatform = stubProcessPlatform('linux');
    process.env.LOCALAPPDATA = localAppData;
    const appsDir = join(localAppData, 'JianyingPro', 'Apps');
    await mkdir(appsDir, { recursive: true });
    await writeFile(join(appsDir, 'Configure.ini'), '[jianyingpro]\nlast_version=10.8.0.2468\n');

    try {
      await expect(detectVersion()).resolves.toBeNull();
    } finally {
      restoreLocalAppData(previousLocalAppData);
      restorePlatform();
    }
  });
});

function restoreLocalAppData(previousValue: string | undefined): void {
  if (previousValue === undefined) {
    delete process.env.LOCALAPPDATA;
    return;
  }

  process.env.LOCALAPPDATA = previousValue;
}

function stubProcessPlatform(platform: NodeJS.Platform): () => void {
  const descriptor = Object.getOwnPropertyDescriptor(process, 'platform');
  Object.defineProperty(process, 'platform', {
    configurable: true,
    value: platform,
  });

  return () => {
    if (descriptor) {
      Object.defineProperty(process, 'platform', descriptor);
    }
  };
}

describe('importDraft', () => {
  beforeEach(() => {
    execFileMock.mockClear();
  });

  it('rejects a missing zip path', async () => {
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));

    await expect(importDraft(join(tempDir, 'missing.zip'), tempDir)).rejects.toThrow(/不存在/);
    expect(execFileMock).not.toHaveBeenCalled();
  });

  it('rejects a directory path', async () => {
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const zipPath = join(tempDir, 'draft.zip');
    await mkdir(zipPath);

    await expect(importDraft(zipPath, tempDir)).rejects.toThrow(/不是文件/);
    expect(execFileMock).not.toHaveBeenCalled();
  });

  it('rejects a non-zip file', async () => {
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const zipPath = join(tempDir, 'draft.txt');
    await writeFile(zipPath, 'not a zip');

    await expect(importDraft(zipPath, tempDir)).rejects.toThrow(/仅支持 \.zip/);
    expect(execFileMock).not.toHaveBeenCalled();
  });

  it('imports into a unique target directory when the draft name already exists', async () => {
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const draftDir = join(tempDir, 'drafts');
    const zipPath = join(tempDir, 'draft.zip');
    await writeFile(zipPath, 'zip content');
    await mkdir(join(draftDir, 'draft'), { recursive: true });

    const result = await importDraft(zipPath, draftDir);

    expect(result.draftDir).toBe(join(draftDir, 'draft_1'));
    expect(execFileMock).toHaveBeenCalledTimes(1);
  });

  it('uses an encoded PowerShell command with environment paths on Windows', async () => {
    const restorePlatform = stubProcessPlatform('win32');
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const draftDir = join(tempDir, 'drafts with space');
    const zipPath = join(tempDir, "draft with 'quote' [safe].zip");
    await writeFile(zipPath, 'zip content');

    try {
      const result = await importDraft(zipPath, draftDir);

      const [command, args, options] = execFileMock.mock.calls[0];
      expect(command).toBe('powershell.exe');
      expect(args).toEqual(expect.arrayContaining(['-EncodedCommand']));
      expect(args).not.toContain('-Command');
      expect(args).not.toContain(zipPath);
      expect(args).not.toContain(result.draftDir);
      expect(options).toMatchObject({
        env: expect.objectContaining({
          VECTCUT_IMPORT_ZIP_PATH: zipPath,
          VECTCUT_IMPORT_DESTINATION_PATH: result.draftDir,
        }),
      });

      const encodedCommand = args[args.indexOf('-EncodedCommand') + 1];
      const decodedCommand = Buffer.from(encodedCommand, 'base64').toString('utf16le');
      expect(decodedCommand).toContain('Expand-Archive');
      expect(decodedCommand).toContain("$ProgressPreference = 'SilentlyContinue'");
      expect(decodedCommand).toContain('$env:VECTCUT_IMPORT_ZIP_PATH');
      expect(decodedCommand).toContain('$env:VECTCUT_IMPORT_DESTINATION_PATH');
    } finally {
      restorePlatform();
    }
  });

  it('passes zip and target paths as direct unzip arguments on non-Windows', async () => {
    const restorePlatform = stubProcessPlatform('linux');
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const draftDir = join(tempDir, 'drafts with space');
    const zipPath = join(tempDir, "draft with 'quote' [safe].zip");
    await writeFile(zipPath, 'zip content');

    try {
      const result = await importDraft(zipPath, draftDir);

      const [command, args] = execFileMock.mock.calls[0];
      expect(command).toBe('unzip');
      expect(args).toEqual(['-o', zipPath, '-d', result.draftDir]);
    } finally {
      restorePlatform();
    }
  });
});

describe('getConfiguredOrDetectedDraftDir', () => {
  it('uses a configured Jianying draft directory before auto detection', async () => {
    const configuredDir = join(os.tmpdir(), 'configured-jianying-drafts');
    const detectDraftDir = vi.fn(() => {
      throw new Error('auto detection should not be used');
    });

    await expect(getConfiguredOrDetectedDraftDir(
      async () => ({ jianyingDraftDir: `  ${configuredDir}  ` }),
      detectDraftDir,
    )).resolves.toBe(configuredDir);

    expect(detectDraftDir).not.toHaveBeenCalled();
  });
});
