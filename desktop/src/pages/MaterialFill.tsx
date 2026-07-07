import { useState } from 'react';
import { formatUserFacingError } from '../api/errorMessages';
import type {
  CoverTitleMetadata,
  MaterialFillResult,
  MaterialMetadata,
  ProbeResult,
  Slot,
  SubtitleMetadata,
} from '../types';

interface MaterialFillProps {
  slots: Slot[];
  onMaterialsReady: (result: MaterialFillResult) => void;
}

export type SlotFillValue =
  | { kind: 'material'; value: MaterialMetadata }
  | { kind: 'subtitle'; value: SubtitleMetadata };

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

export function formatSlotFillValue(fill: SlotFillValue | undefined | null): string {
  if (!fill) {
    return '未选择';
  }

  if (fill.kind === 'subtitle') {
    return '已读取字幕内容';
  }

  const material = fill.value;
  const parts = [];
  if (typeof material.duration === 'number') {
    parts.push(`${material.duration.toFixed(2)} 秒`);
  }
  if (material.width && material.height) {
    parts.push(`${material.width} x ${material.height}`);
  }
  return parts.length > 0 ? parts.join(' / ') : '已选择';
}

export async function collectSlotFill(slot: Slot): Promise<SlotFillValue | null> {
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
  } else if (slot.type === 'cover_image') {
    selectedPath = await window.vectcut.selectImageFile();
    if (selectedPath) {
      probe = await window.vectcut.probeMedia(selectedPath);
    }
  } else if (slot.type === 'subtitle') {
    selectedPath = await window.vectcut.selectSrtFile();
    if (!selectedPath) {
      return null;
    }
    return {
      kind: 'subtitle',
      value: {
        slot_id: slot.slot_id,
        srt_content: await window.vectcut.readTextFile(selectedPath),
      },
    };
  } else {
    return null;
  }

  if (!selectedPath) {
    return null;
  }

  return {
    kind: 'material',
    value: buildMaterial(slot, selectedPath, probe),
  };
}

export function buildMaterialFillResult(
  slots: Slot[],
  fills: Record<string, SlotFillValue | undefined>,
  coverTitleTexts: Record<string, string>,
): MaterialFillResult {
  const materials: MaterialMetadata[] = [];
  const subtitles: SubtitleMetadata[] = [];
  const coverTitles: CoverTitleMetadata[] = [];

  for (const slot of slots) {
    if (slot.type === 'cover_title') {
      const text = coverTitleTexts[slot.slot_id]?.trim();
      if (text) {
        coverTitles.push({ slot_id: slot.slot_id, text });
      }
      continue;
    }

    const fill = fills[slot.slot_id];
    if (fill?.kind === 'material') {
      materials.push(fill.value);
    } else if (fill?.kind === 'subtitle') {
      subtitles.push(fill.value);
    }
  }

  return { materials, subtitles, coverTitles };
}

function formatSlotPath(fill: SlotFillValue | undefined): string {
  if (!fill) {
    return '未选择';
  }
  return fill.kind === 'material' ? fill.value.path : '已读取字幕内容';
}

export default function MaterialFill({ slots, onMaterialsReady }: MaterialFillProps) {
  const [fills, setFills] = useState<Record<string, SlotFillValue>>({});
  const [coverTitleTexts, setCoverTitleTexts] = useState<Record<string, string>>({});
  const [loadingSlotId, setLoadingSlotId] = useState('');
  const [error, setError] = useState('');

  async function handleSelect(slot: Slot) {
    if (slot.type === 'cover_title') {
      return;
    }

    setError('');
    setLoadingSlotId(slot.slot_id);
    try {
      const nextFill = await collectSlotFill(slot);
      if (!nextFill) {
        return;
      }

      setFills((current) => ({ ...current, [slot.slot_id]: nextFill }));
    } catch (caught) {
      setError(formatUserFacingError(caught));
    } finally {
      setLoadingSlotId('');
    }
  }

  function handleCoverTitleChange(slotId: string, text: string) {
    setCoverTitleTexts((current) => ({ ...current, [slotId]: text }));
  }

  function isSlotFilled(slot: Slot): boolean {
    if (slot.type === 'cover_title') {
      return Boolean(coverTitleTexts[slot.slot_id]?.trim());
    }
    return Boolean(fills[slot.slot_id]);
  }

  const selectedCount = slots.filter(isSlotFilled).length;
  const fillStatus = getMaterialFillStatus(selectedCount, slots.length, Boolean(loadingSlotId));
  const readyResult = buildMaterialFillResult(slots, fills, coverTitleTexts);

  return (
    <section aria-labelledby="material-fill-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="material-fill-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          素材填充
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          为已选槽位指定本地素材。视频、音频和图片会自动读取媒体信息，字幕会读取文本内容。
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
                const fill = fills[slot.slot_id];
                const isLoading = loadingSlotId === slot.slot_id;
                const isCoverTitle = slot.type === 'cover_title';
                const coverTitleText = coverTitleTexts[slot.slot_id] ?? '';
                return (
                  <tr key={slot.slot_id}>
                    <td style={tdStyle}>{slot.slot_id}</td>
                    <td style={tdStyle}>{slot.type}</td>
                    <td style={tdStyle}>
                      {isCoverTitle ? (
                        <input
                          aria-label={`封面标题 ${slot.slot_id}`}
                          value={coverTitleText}
                          onChange={(event) => handleCoverTitleChange(slot.slot_id, event.currentTarget.value)}
                          placeholder="请输入封面标题"
                          style={textInputStyle}
                        />
                      ) : (
                        formatSlotPath(fill)
                      )}
                    </td>
                    <td style={tdStyle}>{isLoading ? '正在读取...' : formatSlotFillValue(fill)}</td>
                    <td style={tdStyle}>
                      {isCoverTitle ? null : (
                        <button type="button" onClick={() => handleSelect(slot)} disabled={Boolean(loadingSlotId)} style={secondaryButtonStyle}>
                          {fill ? '替换素材' : '选择素材'}
                        </button>
                      )}
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
          onClick={() => onMaterialsReady(readyResult)}
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

const textInputStyle = {
  width: '100%',
  minWidth: 180,
  minHeight: 34,
  boxSizing: 'border-box',
  padding: '6px 8px',
  border: '1px solid #94a3b8',
  borderRadius: 6,
  font: 'inherit',
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
