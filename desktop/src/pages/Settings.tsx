import { useEffect, useState } from 'react';
import { formatUserFacingError } from '../api/errorMessages';
import { getUnsupportedJianyingVersionMessage } from '../utils/jianyingVersion';

export {
  getUnsupportedJianyingVersionMessage,
  isJianyingVersionSupported,
} from '../utils/jianyingVersion';

const DEFAULT_SERVER_URL = 'https://api.vectcut.com';

interface SettingsProps {
  onClose: () => void;
}

export function normalizeServerUrlForHealth(serverUrl: string): string {
  const trimmed = serverUrl.trim();
  const withoutTrailingSlash = trimmed.replace(/\/+$/, '');
  return withoutTrailingSlash || DEFAULT_SERVER_URL;
}

export function buildHealthUrl(serverUrl: string): string {
  return `${normalizeServerUrlForHealth(serverUrl)}/api/health`;
}

export default function Settings({ onClose }: SettingsProps) {
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER_URL);
  const [jianyingDir, setJianyingDir] = useState('');
  const [jianyingVersion, setJianyingVersion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [saveStatus, setSaveStatus] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('');
  const [connectionState, setConnectionState] = useState<'idle' | 'success' | 'failure'>('idle');

  useEffect(() => {
    let isMounted = true;

    async function loadSettings() {
      setIsLoading(true);
      setLoadError('');
      try {
        const config = await window.vectcut.getUserConfig();
        const configuredServerUrl = config.serverUrl?.trim() ? config.serverUrl : DEFAULT_SERVER_URL;
        const detectedDir = config.jianyingDraftDir
          ? config.jianyingDraftDir
          : await window.vectcut.detectJianyingDraftDir();
        const detectedVersion = await window.vectcut.detectJianyingVersion();

        if (!isMounted) {
          return;
        }
        setServerUrl(configuredServerUrl);
        setJianyingDir(detectedDir ?? '');
        setJianyingVersion(detectedVersion ?? '');
      } catch (error) {
        if (isMounted) {
          setLoadError(formatUserFacingError(error));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleTestConnection() {
    setConnectionState('idle');
    setConnectionStatus('正在测试连接...');
    try {
      const response = await fetch(buildHealthUrl(serverUrl));
      if (response.ok) {
        setConnectionState('success');
        setConnectionStatus('连接成功');
        return;
      }

      setConnectionState('failure');
      setConnectionStatus(`连接失败：HTTP ${response.status}`);
    } catch (error) {
      setConnectionState('failure');
      setConnectionStatus(`连接失败：${formatUserFacingError(error)}`);
    }
  }

  async function handleSelectDir() {
    setSaveStatus('');
    setLoadError('');
    try {
      const selected = await window.vectcut.selectJianyingDraftDir();
      if (selected) {
        setJianyingDir(selected);
      }
    } catch (error) {
      setLoadError(formatUserFacingError(error));
    }
  }

  async function handleSave() {
    setIsSaving(true);
    setSaveStatus('');
    setLoadError('');
    try {
      await window.vectcut.setUserConfig({
        serverUrl: normalizeServerUrlForHealth(serverUrl),
        jianyingDraftDir: jianyingDir || undefined,
      });
      setSaveStatus('已保存');
    } catch (error) {
      setLoadError(formatUserFacingError(error));
    } finally {
      setIsSaving(false);
    }
  }

  const connectionStyle = connectionState === 'success'
    ? successStyle
    : connectionState === 'failure'
      ? errorStyle
      : noteStyle;
  const unsupportedJianyingVersionMessage = getUnsupportedJianyingVersionMessage(jianyingVersion);

  return (
    <section aria-labelledby="settings-title" style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'start', flexWrap: 'wrap' }}>
        <div>
          <h2 id="settings-title" style={{ margin: '0 0 6px', fontSize: 22 }}>
            设置
          </h2>
          <p style={{ margin: 0, color: '#475569' }}>
            配置服务端地址和剪映草稿目录。
          </p>
        </div>
        <button type="button" onClick={onClose} style={secondaryButtonStyle}>
          关闭
        </button>
      </div>

      {isLoading ? <p style={noteStyle}>正在加载设置...</p> : null}
      {loadError ? <p role="alert" style={errorStyle}>{loadError}</p> : null}

      <div style={{ display: 'grid', gap: 18, maxWidth: 760 }}>
        <div style={{ display: 'grid', gap: 10 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontWeight: 700 }}>服务器地址</span>
            <input
              value={serverUrl}
              onChange={(event) => {
                setServerUrl(event.currentTarget.value);
                setConnectionStatus('');
                setConnectionState('idle');
              }}
              placeholder={DEFAULT_SERVER_URL}
              style={inputStyle}
            />
          </label>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={handleTestConnection} style={secondaryButtonStyle}>
              测试连接
            </button>
            {connectionStatus ? <span role="status" style={connectionStyle}>{connectionStatus}</span> : null}
          </div>
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          <span style={{ fontWeight: 700 }}>剪映草稿目录</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={handleSelectDir} style={secondaryButtonStyle}>
              手动选择目录
            </button>
            <span style={{ color: jianyingDir ? '#0f172a' : '#64748b', wordBreak: 'break-all' }}>
              {jianyingDir || '未检测到草稿目录'}
            </span>
          </div>
          <span style={{ color: '#475569' }}>
            剪映版本：{jianyingVersion || '未检测到'}
          </span>
          {unsupportedJianyingVersionMessage ? (
            <p role="alert" style={errorStyle}>
              {unsupportedJianyingVersionMessage}
            </p>
          ) : null}
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button type="button" onClick={handleSave} disabled={isSaving} style={primaryButtonStyle}>
            {isSaving ? '正在保存...' : '保存设置'}
          </button>
          {saveStatus ? <span role="status" style={successStyle}>{saveStatus}</span> : null}
        </div>
      </div>
    </section>
  );
}

const inputStyle = {
  height: 36,
  padding: '0 10px',
  border: '1px solid #cbd5e1',
  borderRadius: 6,
  font: 'inherit',
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

const noteStyle = {
  margin: 0,
  color: '#475569',
} satisfies React.CSSProperties;

const successStyle = {
  margin: 0,
  color: '#166534',
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
