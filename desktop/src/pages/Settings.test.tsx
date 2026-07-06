import { describe, expect, it } from 'vitest';
import settingsSource from './Settings.tsx?raw';
import { buildHealthUrl, normalizeServerUrlForHealth } from './Settings';

describe('Settings', () => {
  it('builds health check URLs from trimmed server URLs', () => {
    expect(buildHealthUrl(' https://example.vectcut.test/// ')).toBe('https://example.vectcut.test/api/health');
    expect(buildHealthUrl('')).toBe('https://api.vectcut.com/api/health');
  });

  it('keeps settings persistence and health check contracts in the renderer', () => {
    expect(settingsSource).toContain('/api/health');
    expect(settingsSource).toContain('setUserConfig');
    expect(settingsSource).toContain('getUserConfig');
    expect(settingsSource).toContain('detectJianyingDraftDir');
    expect(settingsSource).toContain('detectJianyingVersion');
    expect(settingsSource).toContain('selectJianyingDraftDir');
    expect(settingsSource).not.toContain('selectTemplateFolder');
    expect(normalizeServerUrlForHealth(' https://api.vectcut.com/ ')).toBe('https://api.vectcut.com');
  });
});
