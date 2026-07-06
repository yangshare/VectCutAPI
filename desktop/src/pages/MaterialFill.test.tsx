import { describe, expect, it } from 'vitest';
import { getMaterialFillStatus } from './MaterialFill';

describe('MaterialFill readiness', () => {
  it('keeps confirmation disabled until every selected slot has material', () => {
    const partial = getMaterialFillStatus(1, 2, false);

    expect(partial.canConfirm).toBe(false);
    expect(partial.buttonLabel).toBe('确认素材（已选 1 / 2）');
  });

  it('enables confirmation only when all slots are filled', () => {
    const complete = getMaterialFillStatus(2, 2, false);

    expect(complete.canConfirm).toBe(true);
    expect(complete.buttonLabel).toBe('确认素材（已选 2 / 2）');
  });

  it('keeps empty slot lists disabled', () => {
    const empty = getMaterialFillStatus(0, 0, false);

    expect(empty.canConfirm).toBe(false);
    expect(empty.buttonLabel).toBe('确认素材（已选 0 / 0）');
  });
});
