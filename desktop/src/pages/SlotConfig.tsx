import { useState } from 'react';
import { saveSlotConfig } from '../api/client';
import { formatUserFacingError } from '../api/errorMessages';
import type { Slot, SlotMapping } from '../types';

interface SlotConfigProps {
  templateId: string;
  slots: Slot[];
  onConfigSaved: (selected: Slot[]) => void;
}

function toMapping(slot: Slot): SlotMapping {
  return {
    slot_id: slot.slot_id,
    type: slot.type,
    track_name: slot.track_name,
    segment_index: slot.segment_index,
    ...(slot.locator ? { locator: slot.locator } : {}),
  };
}

export default function SlotConfig({ templateId, slots, onConfigSaved }: SlotConfigProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set(slots.map((slot) => slot.slot_id)));
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
    const picked = slots.filter((slot) => selectedIds.has(slot.slot_id));
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
          模板 {templateId} 已解析出 {slots.length} 个槽位，勾选本次需要替换的内容。
        </p>
      </div>

      {slots.length === 0 ? (
        <p style={emptyStyle}>没有解析到可替换槽位，请返回导入步骤检查母版内容。</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
            <thead>
              <tr>
                {['选择', 'slot_id', 'type', 'track_name', 'segment_index', 'locator'].map((heading) => (
                  <th key={heading} style={thStyle}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={slot.slot_id}>
                  <td style={tdStyle}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(slot.slot_id)}
                      onChange={() => toggleSlot(slot.slot_id)}
                      disabled={isLoading}
                      aria-label={`选择 ${slot.slot_id}`}
                    />
                  </td>
                  <td style={tdStyle}>{slot.slot_id}</td>
                  <td style={tdStyle}>{slot.type}</td>
                  <td style={tdStyle}>{slot.track_name}</td>
                  <td style={tdStyle}>{slot.segment_index}</td>
                  <td style={tdStyle}>
                    {slot.locator ? `track ${slot.locator.track_index}, seg ${slot.locator.segment_index}` : '-'}
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
