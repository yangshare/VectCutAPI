import { useState } from 'react';
import { formatUserFacingError } from '../api/errorMessages';
import type { MaterialMetadata, ProbeResult, Slot } from '../types';

interface MaterialFillProps {
  slots: Slot[];
  onMaterialsReady: (materials: MaterialMetadata[]) => void;
}

export function getMaterialFillStatus(selectedCount: number, totalCount: number, isLoading: boolean) {
  return {
    canConfirm: totalCount > 0 && selectedCount === totalCount && !isLoading,
    buttonLabel: `确认素材（已选 ${selectedCount} / ${totalCount}）`,
  };
}

function buildMaterial(slot: Slot, path: string, probe?: ProbeResult): MaterialMetadata {
  return {
    slot_id: slot.slot_id,
    path,
    duration: probe?.duration,
    width: probe?.width,
    height: probe?.height,
  };
}

function formatMetadata(material: MaterialMetadata | undefined): string {
  if (!material) {
    return '未选择';
  }

  const parts = [];
  if (typeof material.duration === 'number') {
    parts.push(`${material.duration.toFixed(2)} 秒`);
  }
  if (material.width && material.height) {
    parts.push(`${material.width} x ${material.height}`);
  }
  return parts.length > 0 ? parts.join(' / ') : '已选择';
}

export default function MaterialFill({ slots, onMaterialsReady }: MaterialFillProps) {
  const [materials, setMaterials] = useState<Record<string, MaterialMetadata>>({});
  const [loadingSlotId, setLoadingSlotId] = useState('');
  const [error, setError] = useState('');

  async function handleSelect(slot: Slot) {
    setError('');
    setLoadingSlotId(slot.slot_id);
    try {
      let selectedPath: string | null = null;
      let probe: ProbeResult | undefined;

      if (slot.type === 'video') {
        selectedPath = await window.vectcut.selectVideoFile();
        if (selectedPath) {
          probe = await window.vectcut.probeMedia(selectedPath);
        }
      } else if (slot.type === 'audio' || slot.type === 'bgm') {
        selectedPath = await window.vectcut.selectAudioFile();
        if (selectedPath) {
          probe = await window.vectcut.probeMedia(selectedPath);
        }
      } else {
        selectedPath = await window.vectcut.selectSrtFile();
      }

      if (!selectedPath) {
        return;
      }

      const nextMaterial = buildMaterial(slot, selectedPath, probe);
      setMaterials((current) => ({ ...current, [slot.slot_id]: nextMaterial }));
    } catch (caught) {
      setError(formatUserFacingError(caught));
    } finally {
      setLoadingSlotId('');
    }
  }

  const selectedMaterials = slots
    .map((slot) => materials[slot.slot_id])
    .filter((material): material is MaterialMetadata => Boolean(material));
  const fillStatus = getMaterialFillStatus(selectedMaterials.length, slots.length, Boolean(loadingSlotId));

  return (
    <section aria-labelledby="material-fill-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="material-fill-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          素材填充
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          为已选槽位指定本地素材。视频和音频会自动读取时长，字幕仅记录 SRT 路径。
        </p>
      </div>

      {slots.length === 0 ? (
        <p style={emptyStyle}>当前没有已选槽位，请返回槽位配置步骤重新选择。</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                {['槽位', '类型', '素材路径', '元数据', '操作'].map((heading) => (
                  <th key={heading} style={thStyle}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => {
                const material = materials[slot.slot_id];
                const isLoading = loadingSlotId === slot.slot_id;
                return (
                  <tr key={slot.slot_id}>
                    <td style={tdStyle}>{slot.slot_id}</td>
                    <td style={tdStyle}>{slot.type}</td>
                    <td style={tdStyle}>{material?.path || '未选择'}</td>
                    <td style={tdStyle}>{isLoading ? '正在读取...' : formatMetadata(material)}</td>
                    <td style={tdStyle}>
                      <button type="button" onClick={() => handleSelect(slot)} disabled={Boolean(loadingSlotId)} style={secondaryButtonStyle}>
                        {material ? '替换素材' : '选择素材'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {error ? <p role="alert" style={errorStyle}>{error}</p> : null}

      <div>
        <button
          type="button"
          onClick={() => onMaterialsReady(selectedMaterials)}
          disabled={!fillStatus.canConfirm}
          style={primaryButtonStyle}
        >
          {fillStatus.buttonLabel}
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

const secondaryButtonStyle = {
  minHeight: 34,
  padding: '0 10px',
  border: '1px solid #94a3b8',
  borderRadius: 6,
  background: '#ffffff',
  color: '#0f172a',
  font: 'inherit',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
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
