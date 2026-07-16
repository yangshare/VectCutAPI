import { useEffect, useState } from 'react';
import { formatUserFacingError } from '../api/errorMessages';
import type {
  CoverTitleMetadata,
  MaterialFillResult,
  MaterialMetadata,
  MaterialSlotMetadata,
  VideoTrackMetadata,
  ProbeResult,
  Slot,
  SubtitleMetadata,
  TextSlotMetadata,
} from '../types';

interface MaterialFillProps {
  slots: Slot[];
  onMaterialsReady: (result: MaterialFillResult) => void;
}

export type SlotFillValue =
  | { kind: 'material'; value: MaterialMetadata }
  | { kind: 'video-track'; value: VideoTrackMetadata }
  | { kind: 'subtitle'; value: SubtitleMetadata };

export function getMaterialFillStatus(selectedCount: number, totalCount: number, isLoading: boolean) {
  return {
    canConfirm: totalCount > 0 && selectedCount === totalCount && !isLoading,
    buttonLabel: `确认素材（已选 ${selectedCount} / ${totalCount}）`,
  };
}

export interface VideoDurationFit {
  materials: VideoTrackMetadata['materials'];
  selectedSourceDuration: number;
  shortage: number;
}

export function fitVideoMaterialsToDuration(
  materials: VideoTrackMetadata['materials'],
  targetDuration?: number,
): VideoDurationFit {
  if (!targetDuration || targetDuration <= 0) {
    return {
      materials: [...materials],
      selectedSourceDuration: materials.reduce(
        (total, material) => total + Math.max(material.duration ?? 0, 0),
        0,
      ),
      shortage: 0,
    };
  }

  const selected: VideoTrackMetadata['materials'] = [];
  let selectedSourceDuration = 0;
  for (const material of materials) {
    selected.push(material);
    selectedSourceDuration += Math.max(material.duration ?? 0, 0);
    if (selectedSourceDuration >= targetDuration) {
      break;
    }
  }

  return {
    materials: selected,
    selectedSourceDuration,
    shortage: Math.max(targetDuration - selectedSourceDuration, 0),
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

export function formatSlotFillValue(
  fill: SlotFillValue | undefined | null,
  targetDuration?: number,
): string {
  if (!fill) {
    return '未选择';
  }

  if (fill.kind === 'subtitle') {
    return '已读取字幕内容';
  }

  if (fill.kind === 'video-track') {
    const fit = fitVideoMaterialsToDuration(fill.value.materials, targetDuration);
    if (targetDuration && fit.shortage > 0) {
      return `目录内 ${fill.value.materials.length} 个视频 / 还差 ${fit.shortage.toFixed(2)} 秒`;
    }
    if (targetDuration) {
      return `将使用 ${fit.materials.length} 个视频 / 对齐 ${targetDuration.toFixed(2)} 秒`;
    }
    return `目录内 ${fill.value.materials.length} 个视频 / 等待配音时长`;
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

function isManualTextSlot(slot: Slot): boolean {
  return (slot.type === 'text' || slot.type === 'subtitle')
    && slot.track_type === 'text'
    && (slot.segment_count ?? 1) <= 1;
}

export async function collectSlotFill(slot: Slot): Promise<SlotFillValue | null> {
  let selectedPath: string | null = null;
  let probe: ProbeResult | undefined;

  if (slot.type === 'video') {
    const selection = await window.vectcut.selectVideoDirectory();
    if (!selection) {
      return null;
    }
    const selectedPaths = sortVideoPaths(selection.files);
    if (selectedPaths.length === 0) {
      throw new Error('所选目录中没有支持的视频文件');
    }
    return {
      kind: 'video-track',
      value: {
        slot_id: slot.slot_id,
        directory: selection.directory,
        materials: await probeVideoFiles(selectedPaths),
      },
    };
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

async function probeVideoFiles(paths: string[], concurrency = 4): Promise<VideoTrackMetadata['materials']> {
  const materials: VideoTrackMetadata['materials'] = new Array(paths.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < paths.length) {
      const index = nextIndex;
      nextIndex += 1;
      const path = paths[index];
      const metadata = await window.vectcut.probeMedia(path);
      materials[index] = { path, ...metadata };
    }
  }

  const workerCount = Math.min(concurrency, paths.length);
  await Promise.all(Array.from({ length: workerCount }, () => worker()));
  return materials;
}

export function sortVideoPaths(paths: string[]): string[] {
  const collator = new Intl.Collator('zh-CN', { numeric: true, sensitivity: 'base' });
  return [...paths].sort((left, right) => collator.compare(fileName(left), fileName(right)));
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function buildMaterialFillResult(
  slots: Slot[],
  fills: Record<string, SlotFillValue | undefined>,
  coverTitleTexts: Record<string, string>,
  textSlotTexts: Record<string, string> = {},
): MaterialFillResult {
  const materials: MaterialSlotMetadata[] = [];
  const subtitles: SubtitleMetadata[] = [];
  const textSlots: TextSlotMetadata[] = [];
  const coverTitles: CoverTitleMetadata[] = [];
  const targetDuration = getAudioTargetDuration(slots, fills);

  for (const slot of slots) {
    if (slot.type === 'cover_title') {
      const text = coverTitleTexts[slot.slot_id]?.trim();
      if (text) {
        coverTitles.push({ slot_id: slot.slot_id, text });
      }
      continue;
    }

    if (isManualTextSlot(slot)) {
      const text = textSlotTexts[slot.slot_id]?.trim();
      if (text) {
        textSlots.push({ slot_id: slot.slot_id, text });
      }
      continue;
    }

    const fill = fills[slot.slot_id];
    if (fill?.kind === 'material') {
      materials.push(fill.value);
    } else if (fill?.kind === 'video-track') {
      materials.push({
        ...fill.value,
        materials: fitVideoMaterialsToDuration(
          fill.value.materials,
          targetDuration,
        ).materials,
      });
    } else if (fill?.kind === 'subtitle') {
      subtitles.push(fill.value);
    }
  }

  return { materials, subtitles, textSlots, coverTitles };
}

export function getAudioTargetDuration(
  slots: Slot[],
  fills: Record<string, SlotFillValue | undefined>,
): number | undefined {
  const durations = slots
    .filter((slot) => slot.type === 'audio')
    .map((slot) => fills[slot.slot_id])
    .filter((fill): fill is Extract<SlotFillValue, { kind: 'material' }> => fill?.kind === 'material')
    .map((fill) => fill.value.duration)
    .filter((duration): duration is number => typeof duration === 'number' && duration > 0);
  return durations.length > 0 ? Math.max(...durations) : undefined;
}

export function getVideoCoverageError(
  slots: Slot[],
  fills: Record<string, SlotFillValue | undefined>,
  targetDuration?: number,
): string {
  if (!targetDuration) {
    return '';
  }
  for (const slot of slots) {
    const fill = fills[slot.slot_id];
    if (slot.type !== 'video' || fill?.kind !== 'video-track') {
      continue;
    }
    const fit = fitVideoMaterialsToDuration(fill.value.materials, targetDuration);
    if (fit.shortage > 0) {
      return `视频目录总时长不足，还差 ${fit.shortage.toFixed(2)} 秒`;
    }
  }
  return '';
}

function formatSlotPath(fill: SlotFillValue | undefined): string {
  if (!fill) {
    return '未选择';
  }
  if (fill.kind === 'material') {
    return fill.value.path;
  }
  if (fill.kind === 'video-track') {
    if (fill.value.directory) {
      return fill.value.directory;
    }
    const first = fill.value.materials[0];
    const last = fill.value.materials[fill.value.materials.length - 1];
    if (!first || !last) {
      return '未选择';
    }
    return first.path === last.path
      ? first.path
      : `${fileName(first.path)} ... ${fileName(last.path)}`;
  }
  return '已读取字幕内容';
}

export default function MaterialFill({ slots, onMaterialsReady }: MaterialFillProps) {
  const [fills, setFills] = useState<Record<string, SlotFillValue>>({});
  const [coverTitleTexts, setCoverTitleTexts] = useState<Record<string, string>>({});
  const [textSlotTexts, setTextSlotTexts] = useState<Record<string, string>>({});
  const [loadingSlotId, setLoadingSlotId] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setTextSlotTexts((current) => {
      const next = { ...current };
      for (const slot of slots) {
        if (
          isManualTextSlot(slot)
          && next[slot.slot_id] === undefined
          && slot.content_preview
        ) {
          next[slot.slot_id] = slot.content_preview;
        }
      }
      return next;
    });
  }, [slots]);

  async function handleSelect(slot: Slot) {
    if (slot.type === 'cover_title' || isManualTextSlot(slot)) {
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

  function handleTextSlotChange(slotId: string, text: string) {
    setTextSlotTexts((current) => ({ ...current, [slotId]: text }));
  }

  function isSlotFilled(slot: Slot): boolean {
    if (slot.type === 'cover_title') {
      return Boolean(coverTitleTexts[slot.slot_id]?.trim());
    }
    if (isManualTextSlot(slot)) {
      return Boolean(textSlotTexts[slot.slot_id]?.trim());
    }
    return Boolean(fills[slot.slot_id]);
  }

  const selectedCount = slots.filter(isSlotFilled).length;
  const targetDuration = getAudioTargetDuration(slots, fills);
  const coverageError = getVideoCoverageError(slots, fills, targetDuration);
  const fillStatus = getMaterialFillStatus(
    selectedCount,
    slots.length,
    Boolean(loadingSlotId) || Boolean(coverageError),
  );
  const readyResult = buildMaterialFillResult(slots, fills, coverTitleTexts, textSlotTexts);

  return (
    <section aria-labelledby="material-fill-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="material-fill-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          素材填充
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          按轨道指定素材。主视频从目录中按文件名顺序匹配配音时长。
        </p>
      </div>

      {slots.length === 0 ? (
        <p style={emptyStyle}>当前没有已选槽位，请返回槽位配置步骤重新选择。</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                {['槽位', '类型', '素材/文字', '元数据', '操作'].map((heading) => (
                  <th key={heading} style={thStyle}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => {
                const fill = fills[slot.slot_id];
                const isLoading = loadingSlotId === slot.slot_id;
                const isCoverTitle = slot.type === 'cover_title';
                const isTextSlot = isManualTextSlot(slot);
                const coverTitleText = coverTitleTexts[slot.slot_id] ?? '';
                const textSlotText = textSlotTexts[slot.slot_id] ?? '';
                return (
                  <tr key={slot.slot_id}>
                    <td style={tdStyle}>
                      <strong>{slot.name ?? slot.slot_id}</strong>
                    </td>
                    <td style={tdStyle}>{formatSlotType(slot)}</td>
                    <td style={tdStyle}>
                      {isCoverTitle ? (
                        <input
                          aria-label={`封面标题 ${slot.slot_id}`}
                          value={coverTitleText}
                          onChange={(event) => handleCoverTitleChange(slot.slot_id, event.currentTarget.value)}
                          placeholder="请输入封面标题"
                          style={textInputStyle}
                        />
                      ) : isTextSlot ? (
                        <input
                          aria-label={`文字轨 ${slot.slot_id}`}
                          value={textSlotText}
                          onChange={(event) => handleTextSlotChange(slot.slot_id, event.currentTarget.value)}
                          placeholder={slot.content_preview || '请输入文字'}
                          style={textInputStyle}
                        />
                      ) : (
                        formatSlotPath(fill)
                      )}
                    </td>
                    <td style={tdStyle}>
                      {isTextSlot
                        ? (textSlotText.trim() ? '手动输入文字' : '未输入')
                        : isLoading ? '正在读取...' : formatSlotFillValue(fill, targetDuration)}
                    </td>
                    <td style={tdStyle}>
                      {isCoverTitle || isTextSlot ? null : (
                        <button type="button" onClick={() => handleSelect(slot)} disabled={Boolean(loadingSlotId)} style={secondaryButtonStyle}>
                          {fill ? '重新选择' : slot.type === 'video' ? '选择目录' : '选择素材'}
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

      {error || coverageError ? (
        <p role="alert" style={errorStyle}>{error || coverageError}</p>
      ) : null}

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

function formatSlotType(slot: Slot): string {
  if (isManualTextSlot(slot)) {
    return '文字';
  }

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
  }[slot.type];
}

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
