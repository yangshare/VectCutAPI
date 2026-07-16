import { useState } from 'react';
import { saveSlotConfig } from '../api/client';
import { formatUserFacingError } from '../api/errorMessages';
import type { Slot, SlotMapping } from '../types';

interface SlotConfigProps {
  templateId: string;
  slots: Slot[];
  onConfigSaved: (selected: Slot[]) => void;
}

export function toMapping(slot: Slot): SlotMapping {
  return {
    slot_id: slot.slot_id,
    name: slot.name,
    type: isSingleTextSlot(slot) ? 'text' : slot.type,
    track_name: slot.track_name,
    segment_index: slot.segment_index,
    ...(slot.segment_indices ? { segment_indices: slot.segment_indices } : {}),
    ...(slot.segment_count ? { segment_count: slot.segment_count } : {}),
    ...(slot.locator ? { locator: slot.locator } : {}),
  };
}

function isSingleTextSlot(slot: Slot): boolean {
  return (slot.track_type === 'text' || slot.type === 'text' || slot.type === 'subtitle')
    && (slot.segment_count ?? 1) <= 1;
}

export function getInitialSelectedSlotIds(slots: Slot[]): Set<string> {
  return new Set(
    slots.filter((slot) => slot.replaceable && slot.selected).map((slot) => slot.slot_id),
  );
}

export default function SlotConfig({ templateId, slots, onConfigSaved }: SlotConfigProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => getInitialSelectedSlotIds(slots));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  function toggleSlot(slotId: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(slotId)) {
        next.delete(slotId);
      } else {
        next.add(slotId);
      }
      return next;
    });
  }

  async function handleSave() {
    const picked = slots.filter((slot) => slot.replaceable && selectedIds.has(slot.slot_id));
    const mappings = picked.map(toMapping);

    setIsLoading(true);
    setError('');
    try {
      await saveSlotConfig(templateId, mappings);
      onConfigSaved(picked);
    } catch (caught) {
      setError(formatUserFacingError(caught));
    } finally {
      setIsLoading(false);
    }
  }

  const selectedCount = selectedIds.size;

  return (
    <section aria-labelledby="slot-config-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="slot-config-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          槽位配置
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          模板 {templateId} 共 {slots.length} 条轨道，请勾选以后每期需要替换的轨道。
        </p>
      </div>

      {slots.length === 0 ? (
        <p style={emptyStyle}>没有解析到轨道，请返回导入步骤检查母版内容。</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
            <thead>
              <tr>
                {['选择', '轨道', '类型', '轨道内容', '状态', '稳定定位'].map((heading) => (
                  <th key={heading} style={thStyle}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={slot.slot_id} style={slot.replaceable ? undefined : preservedRowStyle}>
                  <td style={tdStyle}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(slot.slot_id)}
                      onChange={() => toggleSlot(slot.slot_id)}
                      disabled={isLoading || !slot.replaceable}
                      aria-label={`选择 ${slot.slot_id}`}
                    />
                  </td>
                  <td style={tdStyle}>
                    <strong>{slot.name ?? slot.slot_id}</strong>
                    <div style={secondaryTextStyle}>{slot.slot_id}</div>
                  </td>
                  <td style={tdStyle}>{formatSlotType(slot.type)}</td>
                  <td style={tdStyle}>
                    <div>{formatTrackContent(slot)}</div>
                    {slot.content_preview ? (
                      <div style={previewTextStyle}>{slot.content_preview}</div>
                    ) : null}
                  </td>
                  <td style={tdStyle}>
                    {slot.replaceable ? '可配置' : '原样保留'}
                  </td>
                  <td style={tdStyle}>
                    {slot.locator?.track_id
                      ? `ID ${shortId(slot.locator.track_id)}`
                      : slot.locator
                        ? `轨道 ${slot.locator.track_index}`
                        : slot.track_name || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {error ? <p role="alert" style={errorStyle}>{error}</p> : null}

      <div>
        <button
          type="button"
          onClick={handleSave}
          disabled={isLoading || selectedCount === 0}
          style={primaryButtonStyle}
        >
          {isLoading ? '正在保存...' : `保存槽位配置（${selectedCount}）`}
        </button>
      </div>
    </section>
  );
}

function formatSlotType(type: Slot['type']): string {
  return {
    video: '视频',
    audio: '配音',
    bgm: '背景音乐',
    text: '文字',
    subtitle: '字幕',
    cover_image: '封面图片',
    cover_title: '封面标题',
    effect: '特效',
    adjust: '调节',
    filter: '滤镜',
    sticker: '贴纸',
    unknown: '其他',
  }[type];
}

function formatTrackContent(slot: Slot): string {
  const count = slot.segment_count ?? 1;
  if (slot.track_type === 'text' || slot.type === 'subtitle') {
    return `${count} 条文字片段`;
  }
  if (slot.track_type === 'video' || slot.type === 'video') {
    return `${count} 个视频片段`;
  }
  if (slot.track_type === 'audio' || slot.type === 'audio' || slot.type === 'bgm') {
    return `${count} 个音频片段`;
  }
  return `${count} 个片段`;
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

const thStyle = {
  borderBottom: '1px solid #cbd5e1',
  padding: '10px 8px',
  textAlign: 'left',
  background: '#f8fafc',
  color: '#334155',
  fontSize: 13,
} satisfies React.CSSProperties;

const tdStyle = {
  borderBottom: '1px solid #e2e8f0',
  padding: '10px 8px',
  verticalAlign: 'middle',
  wordBreak: 'break-word',
} satisfies React.CSSProperties;

const secondaryTextStyle = {
  marginTop: 3,
  color: '#64748b',
  fontSize: 12,
} satisfies React.CSSProperties;

const previewTextStyle = {
  marginTop: 3,
  maxWidth: 360,
  color: '#475569',
  fontSize: 12,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
} satisfies React.CSSProperties;

const preservedRowStyle = {
  color: '#64748b',
  background: '#f8fafc',
} satisfies React.CSSProperties;

const primaryButtonStyle = {
  minHeight: 38,
  padding: '0 14px',
  border: '1px solid #1d4ed8',
  borderRadius: 6,
  background: '#2563eb',
  color: '#ffffff',
  font: 'inherit',
  fontWeight: 700,
  cursor: 'pointer',
} satisfies React.CSSProperties;

const emptyStyle = {
  margin: 0,
  padding: 12,
  border: '1px solid #cbd5e1',
  borderRadius: 6,
  background: '#f8fafc',
  color: '#475569',
} satisfies React.CSSProperties;

const errorStyle = {
  margin: 0,
  padding: 10,
  border: '1px solid #fecaca',
  borderRadius: 6,
  background: '#fef2f2',
  color: '#991b1b',
  whiteSpace: 'pre-wrap',
} satisfies React.CSSProperties;
