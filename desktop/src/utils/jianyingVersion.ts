export function isJianyingVersionSupported(version: string): boolean {
  const match = /^(\d+)\.(\d+)\.\d+(?:\.\d+)*$/.exec(version.trim());
  if (!match) {
    return false;
  }

  const major = Number.parseInt(match[1], 10);
  const minor = Number.parseInt(match[2], 10);
  return major === 10 && minor >= 0 && minor <= 9;
}

export function getUnsupportedJianyingVersionMessage(version: string): string | null {
  const detectedVersion = version.trim();
  if (!detectedVersion || isJianyingVersionSupported(detectedVersion)) {
    return null;
  }

  return `当前仅支持剪映专业版 10.0-10.9，检测到 ${detectedVersion}，生成草稿可能无法打开。`;
}
