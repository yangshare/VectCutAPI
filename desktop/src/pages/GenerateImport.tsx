import { useState } from 'react';
import { downloadDraft, renderDraft } from '../api/client';
import { formatUserFacingError, type ApiError } from '../api/errorMessages';
import ErrorDialog from '../components/ErrorDialog';
import type { CoverTitleMetadata, MaterialMetadata, SubtitleMetadata } from '../types';

interface GenerateImportProps {
  templateId: string;
  materials: MaterialMetadata[];
  subtitles: SubtitleMetadata[];
  coverTitles: CoverTitleMetadata[];
  onRestart: () => void;
}

type FlowState = 'idle' | 'rendering' | 'downloading' | 'importing' | 'done' | 'error';

function stateText(state: FlowState): string {
  switch (state) {
    case 'rendering':
      return '正在生成草稿';
    case 'downloading':
      return '正在保存 ZIP';
    case 'importing':
      return '正在导入剪映';
    case 'done':
      return '导入完成';
    case 'error':
      return '处理失败';
    default:
      return '准备生成';
  }
}

export function toApiError(error: unknown): ApiError | null {
  if (
    error
    && typeof error === 'object'
    && 'code' in error
    && typeof (error as { code: unknown }).code === 'string'
    && 'message' in error
    && typeof (error as { message: unknown }).message === 'string'
  ) {
    const candidate = error as { code: string; message: string; details?: unknown };
    return {
      code: candidate.code,
      message: candidate.message,
      ...(isRecord(candidate.details) ? { details: candidate.details } : {}),
    };
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

export default function GenerateImport({
  templateId,
  materials,
  subtitles,
  coverTitles,
  onRestart,
}: GenerateImportProps) {
  const [flowState, setFlowState] = useState<FlowState>('idle');
  const [taskId, setTaskId] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [draftDir, setDraftDir] = useState('');
  const [message, setMessage] = useState('');
  const [dialogError, setDialogError] = useState<ApiError | null>(null);

  async function handleStart() {
    setFlowState('rendering');
    setMessage('');
    setDialogError(null);
    setDraftDir('');
    setWarnings([]);

    try {
      const rendered = await renderDraft(templateId, materials, subtitles, coverTitles);
      setTaskId(rendered.task_id);
      setWarnings(rendered.warnings);

      const savePath = await window.vectcut.selectDraftSavePath(`${rendered.task_id}.zip`);
      if (!savePath) {
        setFlowState('idle');
        setMessage('已取消保存位置选择，可以重新开始生成。');
        return;
      }

      setFlowState('downloading');
      await downloadDraft(rendered.task_id, savePath);

      setFlowState('importing');
      const imported = await window.vectcut.importDraftToJianying(savePath);
      setDraftDir(imported.draftDir);
      setFlowState('done');
    } catch (caught) {
      const apiError = toApiError(caught);
      if (apiError) {
        setDialogError(apiError);
      }
      setMessage(formatUserFacingError(caught));
      setFlowState('error');
    }
  }

  const isBusy = flowState === 'rendering' || flowState === 'downloading' || flowState === 'importing';
  const slotValueCount = materials.length + subtitles.length + coverTitles.length;

  return (
    <section aria-labelledby="generate-import-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="generate-import-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          生成导入
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          使用模板 {templateId} 和 {slotValueCount} 个槽位值生成草稿 ZIP，保存后导入剪映草稿目录。
        </p>
      </div>

      <dl style={statusGridStyle}>
        <div>
          <dt style={dtStyle}>状态</dt>
          <dd style={ddStyle}>{stateText(flowState)}</dd>
        </div>
        <div>
          <dt style={dtStyle}>任务 ID</dt>
          <dd style={ddStyle}>{taskId || '尚未生成'}</dd>
        </div>
        <div>
          <dt style={dtStyle}>素材数量</dt>
          <dd style={ddStyle}>{slotValueCount}</dd>
        </div>
      </dl>

      {warnings.length > 0 ? (
        <div style={warningStyle}>
          <strong>生成警告</strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>
            {warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      {message ? (
        <p role={flowState === 'error' ? 'alert' : 'status'} style={flowState === 'error' ? errorStyle : noteStyle}>
          {message}
        </p>
      ) : null}

      {draftDir ? (
        <p style={successStyle}>
          已导入剪映草稿目录：<span style={{ wordBreak: 'break-all' }}>{draftDir}</span>
        </p>
      ) : null}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {flowState === 'done' ? (
          <button type="button" onClick={onRestart} style={primaryButtonStyle}>
            开始下一个模板
          </button>
        ) : (
          <button type="button" onClick={handleStart} disabled={isBusy || slotValueCount === 0} style={primaryButtonStyle}>
            {isBusy ? stateText(flowState) : '开始生成并导入'}
          </button>
        )}
        {flowState === 'error' ? (
          <button type="button" onClick={handleStart} style={secondaryButtonStyle}>
            重新开始
          </button>
        ) : null}
      </div>

      {dialogError ? (
        <ErrorDialog error={dialogError} onClose={() => setDialogError(null)} />
      ) : null}
    </section>
  );
}

const statusGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: 8,
  margin: 0,
} satisfies React.CSSProperties;

const dtStyle = {
  margin: 0,
  color: '#64748b',
  fontSize: 12,
  fontWeight: 700,
} satisfies React.CSSProperties;

const ddStyle = {
  margin: '4px 0 0',
  color: '#0f172a',
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
  minHeight: 38,
  padding: '0 14px',
  border: '1px solid #94a3b8',
  borderRadius: 6,
  background: '#ffffff',
  color: '#0f172a',
  font: 'inherit',
  cursor: 'pointer',
} satisfies React.CSSProperties;

const warningStyle = {
  margin: 0,
  padding: 10,
  border: '1px solid #fde68a',
  borderRadius: 6,
  background: '#fffbeb',
  color: '#92400e',
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

const noteStyle = {
  margin: 0,
  padding: 10,
  border: '1px solid #bfdbfe',
  borderRadius: 6,
  background: '#eff6ff',
  color: '#1e40af',
} satisfies React.CSSProperties;

const successStyle = {
  margin: 0,
  padding: 10,
  border: '1px solid #bbf7d0',
  borderRadius: 6,
  background: '#f0fdf4',
  color: '#166534',
} satisfies React.CSSProperties;
