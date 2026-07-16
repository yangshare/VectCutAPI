import { useState } from 'react';
import { importDraftContentTemplate } from '../api/client';
import { formatUserFacingError } from '../api/errorMessages';
import type { Slot } from '../types';

interface TemplateManagerProps {
  onTemplateImported: (templateId: string, slots: Slot[]) => void;
}

export default function TemplateManager({ onTemplateImported }: TemplateManagerProps) {
  const [templateId, setTemplateId] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSelectFolder() {
    setError('');
    const selected = await window.vectcut.selectTemplateFolder();
    if (selected) {
      setFolderPath(selected);
    }
  }

  async function handleImport() {
    const normalizedId = templateId.trim();
    if (!folderPath) {
      setError('请先选择剪映草稿文件夹');
      return;
    }
    if (!normalizedId) {
      setError('请输入模板 ID');
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const result = await importDraftContentTemplate(normalizedId, folderPath);
      onTemplateImported(result.template_id, result.slots);
    } catch (caught) {
      setError(formatUserFacingError(caught));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section aria-labelledby="template-manager-title" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2 id="template-manager-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
          导入母版
        </h2>
        <p style={{ margin: 0, color: '#475569' }}>
          选择一个剪映草稿文件夹并设置模板 ID，系统会读取完整轨道清单供首次配置。
        </p>
      </div>

      <div style={{ display: 'grid', gap: 12, maxWidth: 760 }}>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontWeight: 700 }}>模板 ID</span>
          <input
            value={templateId}
            onChange={(event) => setTemplateId(event.currentTarget.value)}
            placeholder="例如 product-demo-001"
            disabled={isLoading}
            style={{ height: 36, padding: '0 10px', border: '1px solid #cbd5e1', borderRadius: 6, font: 'inherit' }}
          />
        </label>

        <div style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontWeight: 700 }}>剪映草稿文件夹</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={handleSelectFolder} disabled={isLoading} style={secondaryButtonStyle}>
              选择剪映草稿文件夹
            </button>
            <span style={{ color: folderPath ? '#0f172a' : '#64748b', wordBreak: 'break-all' }}>
              {folderPath || '尚未选择'}
            </span>
          </div>
        </div>

        {error ? <p role="alert" style={errorStyle}>{error}</p> : null}

        <div>
          <button type="button" onClick={handleImport} disabled={isLoading} style={primaryButtonStyle}>
            {isLoading ? '正在导入...' : '导入并解析轨道'}
          </button>
        </div>
      </div>
    </section>
  );
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
  minHeight: 36,
  padding: '0 12px',
  border: '1px solid #94a3b8',
  borderRadius: 6,
  background: '#ffffff',
  color: '#0f172a',
  font: 'inherit',
  cursor: 'pointer',
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
