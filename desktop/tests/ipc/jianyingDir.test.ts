import { mkdir, mkdtemp, writeFile } from 'fs/promises';
import os from 'os';
import { join } from 'path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getConfiguredOrDetectedDraftDir, importDraft, isVersionSupported } from '../../electron/ipc/jianyingDir';

const { execFileMock } = vi.hoisted(() => ({
  execFileMock: vi.fn((_file, _args, callback) => callback(null, '', '')),
}));

vi.mock('child_process', () => ({
  execFile: execFileMock,
}));

describe('isVersionSupported', () => {
  it.each(['10.0.0', '10.5.3', '10.9.9', '10.9.10'])('supports %s', (version) => {
    expect(isVersionSupported(version)).toBe(true);
  });

  it.each(['11.0.0', '9.8.0', '10.10.0', 'abc', ''])('rejects %s', (version) => {
    expect(isVersionSupported(version)).toBe(false);
  });
});

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

  it('passes zip and target paths as execFile arguments without shell-concatenating user paths', async () => {
    const tempDir = await mkdtemp(join(os.tmpdir(), 'jianying-draft-'));
    const draftDir = join(tempDir, 'drafts with space');
    const zipPath = join(tempDir, "draft with 'quote' [safe].zip");
    await writeFile(zipPath, 'zip content');

    const result = await importDraft(zipPath, draftDir);

    const [command, args] = execFileMock.mock.calls[0];
    expect(command).toEqual(expect.any(String));
    expect(args).toEqual(expect.arrayContaining([zipPath, result.draftDir]));
    for (const arg of args) {
      if (typeof arg === 'string' && arg !== zipPath && arg !== result.draftDir) {
        expect(arg).not.toContain(zipPath);
        expect(arg).not.toContain(result.draftDir);
      }
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
