import { describe, expect, it } from 'vitest';
import generateImportSource from './GenerateImport.tsx?raw';
import { toApiError } from './GenerateImport';

describe('GenerateImport error dialog integration', () => {
  it('recognizes structured API errors for dialog rendering', () => {
    expect(toApiError({ code: 'R_LOOP_TOO_MANY', message: 'too many loops' })).toEqual({
      code: 'R_LOOP_TOO_MANY',
      message: 'too many loops',
    });
    expect(toApiError(new Error('plain failure'))).toBeNull();
  });

  it('renders ErrorDialog for structured API errors', () => {
    expect(generateImportSource).toContain("import ErrorDialog from '../components/ErrorDialog'");
    expect(generateImportSource).toContain('dialogError');
    expect(generateImportSource).toContain('<ErrorDialog');
    expect(generateImportSource).toContain('toApiError(caught)');
  });

  it('passes media, subtitles, and cover titles to renderDraft', () => {
    expect(generateImportSource).toContain('subtitles');
    expect(generateImportSource).toContain('coverTitles');
    expect(generateImportSource).toContain('renderDraft(templateId, materials, subtitles, coverTitles)');
  });
});
