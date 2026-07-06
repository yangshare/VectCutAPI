import type { VectCutApi } from './types';

declare global {
  interface Window {
    vectcut: VectCutApi;
  }
}
