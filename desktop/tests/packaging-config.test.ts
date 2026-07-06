import { readFile } from 'fs/promises';
import { describe, expect, it } from 'vitest';

const builderConfigUrl = new URL('../electron-builder.yml', import.meta.url);
const installGuideUrl = new URL('../docs/install-guide.md', import.meta.url);

async function readBuilderConfig() {
  return readFile(builderConfigUrl, 'utf-8');
}

async function readInstallGuide() {
  return readFile(installGuideUrl, 'utf-8');
}

describe('desktop packaging config', () => {
  it('defines electron-builder metadata, outputs, targets, and ffprobe resources', async () => {
    const config = await readBuilderConfig();

    expect(config).toContain('appId: com.vectcut.desktop');
    expect(config).toContain('productName: VectCut 模板套版');
    expect(config).toContain('output: dist');
    expect(config).toContain('buildResources: build');
    expect(config).toContain('out/**/*');
    expect(config).toContain('package.json');
    expect(config).toContain("'!**/*.{ts,tsx,map}'");
    expect(config).toContain("'!tests/**'");
    expect(config).toContain("'!docs/**'");
    expect(config).toContain('oneClick: false');
    expect(config).toContain('allowToChangeInstallationDirectory: true');
    expect(config).toContain('createDesktopShortcut: true');
    expect(config).toContain('shortcutName: VectCut 模板套版');
    expect(config).toContain('category: public.app-category.video');
    expect(config).toContain('artifactName: ${productName}-${version}.${ext}');
    expect(config).not.toContain('{bin,bin/**}');
    expect(config).toContain('from: node_modules/ffprobe-static/bin/win32/${arch}/ffprobe.exe');
    expect(config).toContain('to: ffprobe/bin/ffprobe.exe');
    expect(config).toContain('from: node_modules/ffprobe-static/bin/darwin/${arch}/ffprobe');
    expect(config).toContain('to: ffprobe/bin/ffprobe');
    expect(config).toContain('artifactName: ${productName}-Setup-${version}-${arch}.${ext}');
    expect(config).toContain('artifactName: ${productName}-Portable-${version}-${arch}.${ext}');
  });

  it('documents Windows, macOS, server setup, and common install issues', async () => {
    const guide = await readInstallGuide();

    expect(guide).toContain('# VectCut 模板套版 安装指南');
    expect(guide).toContain('## Windows 安装');
    expect(guide).toContain('Windows 10 64 位及以上');
    expect(guide).toContain('剪映专业版 10.0-10.9');
    expect(guide).toContain('ffprobe 已内置');
    expect(guide).toContain('MVP 内测阶段未购买代码签名证书');
    expect(guide).toContain('更多信息');
    expect(guide).toContain('仍要运行');
    expect(guide).toContain('开源');
    expect(guide).toContain('## macOS 安装');
    expect(guide).toContain('dmg');
    expect(guide).toContain('Applications');
    expect(guide).toContain('macOS 11 及以上');
    expect(guide).toContain('剪映专业版 10.0-10.9（Mac 版）');
    expect(guide).toContain('Gatekeeper');
    expect(guide).toContain("xattr -cr '/Applications/VectCut 模板套版.app'");
    expect(guide).toContain('未签名');
    expect(guide).toContain('未公证');
    expect(guide).toContain('## 首次使用');
    expect(guide).toContain('https://api.vectcut.com');
    expect(guide).toContain('http://127.0.0.1:9001');
    expect(guide).not.toContain('http://127.0.0.1:8000');
    expect(guide).toContain('确认草稿目录自动检测结果');
    expect(guide).toContain('保存设置');
    expect(guide).toContain('开始使用');
    expect(guide).toContain('## 服务端配置');
    expect(guide).toContain('服务器地址');
    expect(guide).toContain('剪映草稿目录');
    expect(guide).toContain('测试连接');
    expect(guide).toContain('## 常见问题');
    expect(guide).toContain('SmartScreen');
    expect(guide).toContain('找不到剪映草稿目录');
    expect(guide).toContain('连接失败');
    expect(guide).toContain('生成后看不到草稿');
  });
});
