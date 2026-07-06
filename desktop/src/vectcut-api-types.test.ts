import { expectTypeOf, test } from 'vitest';

test('window.vectcut exposes controlled IPC methods to the renderer', () => {
  expectTypeOf<Window['vectcut']['selectVideoFile']>().returns.resolves.toEqualTypeOf<string | null>();
  expectTypeOf<Window['vectcut']['probeMedia']>().parameter(0).toEqualTypeOf<string>();
  expectTypeOf<Window['vectcut']['probeMedia']>().returns.resolves.toEqualTypeOf<{
    duration: number;
    width?: number;
    height?: number;
  }>();
  expectTypeOf<Window['vectcut']['setUserConfig']>().parameter(0).toEqualTypeOf<{
    serverUrl?: string;
    jianyingDraftDir?: string;
  }>();
  expectTypeOf<Window['vectcut']['readZipFile']>().returns.resolves.toEqualTypeOf<ArrayBuffer>();
});
