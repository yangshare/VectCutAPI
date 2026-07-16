import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { Slot } from '../types';
import SlotConfig, { getInitialSelectedSlotIds, toMapping } from './SlotConfig';

function track(overrides: Partial<Slot> & Pick<Slot, 'slot_id' | 'type'>): Slot {
  return {
    name: overrides.slot_id,
    track_name: '',
    segment_index: 0,
    segment_count: 1,
    ...overrides,
  };
}

describe('SlotConfig track selection', () => {
  it('starts a newly imported template with no selected tracks', () => {
    const slots = [
      track({ slot_id: 'video_track0', type: 'video', replaceable: true, selected: false }),
      track({ slot_id: 'subtitle_track1', type: 'subtitle', replaceable: true, selected: false }),
    ];

    expect([...getInitialSelectedSlotIds(slots)]).toEqual([]);
  });

  it('restores saved replaceable tracks but never selects system tracks', () => {
    const slots = [
      track({ slot_id: 'video_track0', type: 'video', replaceable: true, selected: true }),
      track({ slot_id: 'effect_track1', type: 'effect', replaceable: false, selected: true }),
    ];

    expect([...getInitialSelectedSlotIds(slots)]).toEqual(['video_track0']);
  });

  it('renders all tracks and disables preserved system tracks', () => {
    const slots = [
      track({
        slot_id: 'video_track0',
        name: '视频轨 1',
        type: 'video',
        replaceable: true,
        selected: false,
        content_preview: '001.mp4',
      }),
      track({
        slot_id: 'effect_track1',
        name: '特效轨 1',
        type: 'effect',
        replaceable: false,
        selected: false,
      }),
    ];

    const html = renderToStaticMarkup(
      <SlotConfig templateId="tpl" slots={slots} onConfigSaved={vi.fn()} />,
    );

    expect(html).toContain('视频轨 1');
    expect(html).toContain('001.mp4');
    expect(html).toContain('特效轨 1');
    expect(html).toContain('原样保留');
    expect(html).toContain('disabled=""');
  });

  it('saves single text tracks as text mappings instead of SRT subtitle mappings', () => {
    const mapping = toMapping(track({
      slot_id: 'subtitle_track5',
      type: 'subtitle',
      track_type: 'text',
      segment_count: 1,
    }));

    expect(mapping.type).toBe('text');
  });
});
