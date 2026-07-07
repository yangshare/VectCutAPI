import { mkdir, mkdtemp, rm, stat, writeFile } from 'fs/promises';
import os from 'os';
import { basename, join } from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildPackCommand,
  packTemplateFolder,
  readDraftContentFile,
  validateTemplateFolder,
} from '../../electron/ipc/packer';

const { execFileMock } = vi.hoisted(() => ({
  execFileMock: vi.fn((_file, args, optionsOrCallback, maybeCallback) => {
    const callback = typeof optionsOrCallback === 'function' ? optionsOrCallback : maybeCallback;
    const options = typeof optionsOrCallback === 'function' ? {} : optionsOrCallback;
    const zipPath =
      args.find((arg: string) => arg.endsWith('.zip')) ?? options.env?.VECTCUT_PACK_DEST;
    return writeFile(zipPath, 'mock zip content').then(() => callback(null, '', ''));
  }),
}));

vi.mock('child_process', () => ({
  execFile: execFileMock,
}));

describe('packer', () => {
  let tempDir: string;

  beforeEach(async () => {
    execFileMock.mockClear();
    tempDir = await mkdtemp(join(os.tmpdir(), 'packer-test-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it('throws when draft_content.json is missing', async () => {
    const folderPath = join(tempDir, 'template');
    await mkdir(folderPath);

    expect(() => validateTemplateFolder(folderPath)).toThrow(
      '母版文件夹缺少 draft_content.json，请确认是剪映草稿目录',
    );
  });

  it('throws when folder path does not exist', () => {
    const folderPath = join(tempDir, 'missing');

    expect(() => validateTemplateFolder(folderPath)).toThrow(`母版文件夹不存在：${folderPath}`);
  });

  it('accepts a valid template folder', async () => {
    const folderPath = join(tempDir, 'template');
    await mkdir(folderPath);
    await writeFile(join(folderPath, 'draft_content.json'), '{}');

    expect(() => validateTemplateFolder(folderPath)).not.toThrow();
  });

  it('reads only root draft_content.json without invoking the zip packer', async () => {
    const folderPath = join(tempDir, 'template');
    await mkdir(folderPath);
    await writeFile(join(folderPath, 'draft_content.json'), '{"tracks":[]}');

    const result = await readDraftContentFile(folderPath);

    expect(result.filePath).toBe(join(folderPath, 'draft_content.json'));
    expect(result.sizeMB).toBeGreaterThan(0);
    expect(Buffer.from(result.bytes).toString('utf8')).toBe('{"tracks":[]}');
    expect(execFileMock).not.toHaveBeenCalled();
  });

  it('packs a valid template folder to a non-empty zip file', async () => {
    const folderPath = join(tempDir, 'template with space');
    const outputDir = join(tempDir, 'output');
    await mkdir(folderPath);
    await mkdir(outputDir);
    await writeFile(join(folderPath, 'draft_content.json'), '{}');
    const previousEnv = process.env.VECTCUT_EXISTING_ENV_FOR_TEST;
    process.env.VECTCUT_EXISTING_ENV_FOR_TEST = 'keep';

    let result;
    try {
      result = await packTemplateFolder(folderPath, outputDir);
    } finally {
      if (previousEnv === undefined) {
        delete process.env.VECTCUT_EXISTING_ENV_FOR_TEST;
      } else {
        process.env.VECTCUT_EXISTING_ENV_FOR_TEST = previousEnv;
      }
    }
    const zipStats = await stat(result.zipPath);

    expect(result.zipPath).toMatch(/\.zip$/);
    expect(basename(result.zipPath)).toContain('template with space-');
    expect(result.sizeMB).toBeGreaterThan(0);
    expect(zipStats.size).toBeGreaterThan(0);

    if (process.platform === 'win32') {
      const [, , options] = execFileMock.mock.calls[0];
      expect(options.env).toMatchObject({
        VECTCUT_EXISTING_ENV_FOR_TEST: 'keep',
        VECTCUT_PACK_SOURCE: folderPath,
        VECTCUT_PACK_DEST: result.zipPath,
      });
    }
  });

  it('uses unique zip paths when packing the same folder in the same millisecond', async () => {
    const folderPath = join(tempDir, 'template');
    const outputDir = join(tempDir, 'output');
    await mkdir(folderPath);
    await mkdir(outputDir);
    await writeFile(join(folderPath, 'draft_content.json'), '{}');

    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-06T00:00:00.000Z'));
    try {
      const first = await packTemplateFolder(folderPath, outputDir);
      const second = await packTemplateFolder(folderPath, outputDir);

      expect(first.zipPath).not.toBe(second.zipPath);
      expect(first.zipPath).toMatch(/\.zip$/);
      expect(second.zipPath).toMatch(/\.zip$/);
    } finally {
      vi.useRealTimers();
    }
  });

  it('builds non-Windows zip command with the folder path only in cwd', () => {
    const folderPath = join(tempDir, `template with 'single' "double" (round) [square]`);
    const zipPath = join(tempDir, 'output.zip');

    const command = buildPackCommand('linux', folderPath, zipPath);

    expect(command).toEqual({
      command: 'zip',
      args: ['-r', zipPath, '.'],
      options: { cwd: folderPath },
    });
    expect(command?.command).not.toContain(folderPath);
    expect(command?.args).not.toContain(folderPath);
  });

  it('builds Windows zip command with user paths passed through env only', () => {
    const folderPath = join(tempDir, `template with 'single' "double" (round) [square]`);
    const zipPath = join(tempDir, 'output.zip');

    const command = buildPackCommand('win32', folderPath, zipPath);

    const commandScriptIndex = command.args.indexOf('-Command');
    const commandScript = commandScriptIndex >= 0 ? command.args[commandScriptIndex + 1] : '';

    expect(command.command).toBe('powershell.exe');
    expect(command.args).toEqual(
      expect.arrayContaining([
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
      ]),
    );
    expect(command.args).not.toContain(folderPath);
    expect(command.args).not.toContain(join(folderPath, '*'));
    expect(command.args).not.toContain(zipPath);
    expect(command.options?.env).toMatchObject({
      VECTCUT_PACK_SOURCE: folderPath,
      VECTCUT_PACK_DEST: zipPath,
    });
    expect(commandScript).toContain('$env:VECTCUT_PACK_SOURCE');
    expect(commandScript).toContain('$env:VECTCUT_PACK_DEST');
    expect(commandScript).not.toContain('$args');
    expect(commandScript).not.toContain(folderPath);
    expect(commandScript).not.toContain(zipPath);
  });
});
