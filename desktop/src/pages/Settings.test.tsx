import { describe, expect, it } from 'vitest';
import settingsSource from './Settings.tsx?raw';
import {
  buildHealthUrl,
  getUnsupportedJianyingVersionMessage,
  isJianyingVersionSupported,
  normalizeServerUrlForHealth,
} from './Settings';

describe('Settings', () => {
  it('builds health check URLs from trimmed server URLs', () => {
    expect(buildHealthUrl(' https://example.vectcut.test/// ')).toBe('https://example.vectcut.test/health');
    expect(buildHealthUrl('')).toBe('https://api.vectcut.com/health');
  });

  it('keeps settings persistence and health check contracts in the renderer', () => {
    expect(settingsSource).toContain('/health');
    expect(settingsSource).not.toContain('/api/health');
    expect(settingsSource).toContain('setUserConfig');
    expect(settingsSource).toContain('getUserConfig');
    expect(settingsSource).toContain('detectJianyingDraftDir');
    expect(settingsSource).toContain('detectJianyingVersion');
    expect(settingsSource).toContain('selectJianyingDraftDir');
    expect(settingsSource).not.toContain('selectTemplateFolder');
    expect(normalizeServerUrlForHealth(' https://api.vectcut.com/ ')).toBe('https://api.vectcut.com');
  });

  it('builds an unsupported Jianying version warning for detected versions outside 10.0-10.9', () => {
    expect(isJianyingVersionSupported('10.0.0')).toBe(true);
    expect(isJianyingVersionSupported('10.9.0.12345')).toBe(true);
    expect(isJianyingVersionSupported('10.10.0')).toBe(false);
    expect(isJianyingVersionSupported('11.0.0')).toBe(false);
    expect(isJianyingVersionSupported('10.9.beta')).toBe(false);
    expect(isJianyingVersionSupported('10.9.')).toBe(false);
    expect(isJianyingVersionSupported('10.9')).toBe(false);
    expect(getUnsupportedJianyingVersionMessage('10.10.0')).toBe(
      '当前仅支持剪映专业版 10.0-10.9，检测到 10.10.0，生成草稿可能无法打开。',
    );
    expect(getUnsupportedJianyingVersionMessage('')).toBeNull();
    expect(getUnsupportedJianyingVersionMessage('10.8.0')).toBeNull();
  });
});
