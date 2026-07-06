import { useState } from 'react';
import { getUserFriendlyError, type ApiError } from '../api/errorMessages';

interface ErrorDialogProps {
  error: ApiError;
  onClose: () => void;
}

export default function ErrorDialog({ error, onClose }: ErrorDialogProps) {
  const [copyStatus, setCopyStatus] = useState('');
  const title = error.code === 'R_LOOP_TOO_MANY' ? '视频素材不足' : '操作失败';
  const friendlyMessage = getUserFriendlyError(error);
  const technicalDetails = stringifyErrorDetails(error);

  async function handleCopy() {
    try {
      if (!navigator.clipboard?.writeText) {
        setCopyStatus('复制失败');
        return;
      }
      await navigator.clipboard.writeText(`${friendlyMessage}\n\n${technicalDetails}`);
      setCopyStatus('已复制');
    } catch {
      setCopyStatus('复制失败');
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="error-dialog-title" style={backdropStyle}>
      <section style={dialogStyle}>
        <div style={{ display: 'grid', gap: 8 }}>
          <h2 id="error-dialog-title" style={{ margin: 0, fontSize: 22 }}>
            {title}
          </h2>
          <p style={messageStyle}>{friendlyMessage}</p>
        </div>

        {error.code === 'R_LOOP_TOO_MANY' ? (
          <div style={suggestionStyle}>
            <strong>建议处理方式</strong>
            <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
              <li>增加视频片段</li>
              <li>缩短配音时长</li>
              <li>使用更长素材</li>
            </ul>
          </div>
        ) : null}

        <details style={{ display: 'grid', gap: 8 }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700 }}>技术详情</summary>
          <pre style={preStyle}>{technicalDetails}</pre>
        </details>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={handleCopy} style={secondaryButtonStyle}>
              复制错误信息
            </button>
            {copyStatus ? <span role="status" style={{ color: copyStatus === '已复制' ? '#166534' : '#991b1b' }}>{copyStatus}</span> : null}
          </div>
          <button type="button" onClick={onClose} style={primaryButtonStyle}>
            关闭
          </button>
        </div>
      </section>
    </div>
  );
}

export function stringifyErrorDetails(error: ApiError): string {
  try {
    return JSON.stringify(error, null, 2);
  } catch {
    return JSON.stringify({
      code: error.code,
      message: error.message,
      details: '[unserializable error details]',
    }, null, 2);
  }
}

const backdropStyle = {
  position: 'fixed',
  inset: 0,
  zIndex: 20,
  display: 'grid',
  placeItems: 'center',
  padding: 24,
  background: 'rgba(15, 23, 42, 0.36)',
} satisfies React.CSSProperties;

const dialogStyle = {
  width: 'min(640px, 100%)',
  display: 'grid',
  gap: 16,
  padding: 18,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  boxShadow: '0 18px 45px rgba(15, 23, 42, 0.22)',
} satisfies React.CSSProperties;

const messageStyle = {
  margin: 0,
  color: '#334155',
  whiteSpace: 'pre-wrap',
} satisfies React.CSSProperties;

const suggestionStyle = {
  padding: 12,
  border: '1px solid #bfdbfe',
  borderRadius: 6,
  background: '#eff6ff',
  color: '#1e3a8a',
} satisfies React.CSSProperties;

const preStyle = {
  margin: '8px 0 0',
  padding: 12,
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  background: '#f8fafc',
  color: '#0f172a',
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
  fontSize: 12,
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
  minHeight: 36,
  padding: '0 12px',
  border: '1px solid #94a3b8',
  borderRadius: 6,
  background: '#ffffff',
  color: '#0f172a',
  font: 'inherit',
  cursor: 'pointer',
} satisfies React.CSSProperties;
