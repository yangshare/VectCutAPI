import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import App, { getStartupJianyingVersionWarning } from './App';
import appSource from './App.tsx?raw';
import generateImportSource from './pages/GenerateImport.tsx?raw';

describe('App', () => {
  it('renders the 4-step wizard entry screen', () => {
    const html = renderToStaticMarkup(<App />);

    expect(html).toContain('VectCut 模板套版');
    expect(html).toContain('导入母版');
    expect(html).toContain('槽位配置');
    expect(html).toContain('素材填充');
    expect(html).toContain('生成导入');
    expect(html).toContain('模板 ID');
    expect(html).toContain('选择剪映草稿文件夹');
    expect(html).toContain('导入并解析轨道');
    expect(html).toContain('设置');
    expect(html).not.toContain('脚手架就绪');
  });

  it('keeps draft download in the preload save-path flow', () => {
    const requireToken = ['requ', 'ire'].join('');
    const processToken = ['proc', 'ess'].join('');
    const osModule = ['o', 's'].join('');

    expect(generateImportSource).toContain('selectDraftSavePath');
    expect(generateImportSource).not.toContain(`${requireToken}('${osModule}')`);
    expect(generateImportSource).not.toContain(`${requireToken}("${osModule}")`);
    expect(generateImportSource).not.toContain('tmpdir');
    expect(generateImportSource).not.toContain(`node:${osModule}`);
    expect(generateImportSource).not.toContain(`import ${osModule}`);
    expect(generateImportSource).not.toContain(`${processToken}.`);
  });

  it('keeps subtitles, text slots, and cover titles in the material fill result through the wizard', () => {
    expect(appSource).toContain('MaterialFillResult');
    expect(appSource).toContain('setMaterialFillResult');
    expect(appSource).toContain('subtitles={materialFillResult.subtitles}');
    expect(appSource).toContain('textSlots={materialFillResult.textSlots}');
    expect(appSource).toContain('coverTitles={materialFillResult.coverTitles}');
  });

  it('checks Jianying version on startup without blocking the wizard', () => {
    expect(appSource).toContain("from 'react'");
    expect(appSource).toContain('detectJianyingVersion');
    expect(appSource).toContain('window.vectcut?.detectJianyingVersion');
    expect(appSource).not.toContain('window.vectcut.detectJianyingVersion()');
    expect(appSource).toContain('getStartupJianyingVersionWarning(startupJianyingVersion)');
    expect(appSource).toContain('TemplateManager onTemplateImported={handleTemplateImported}');
  });

  it('builds a startup warning for unsupported Jianying versions', () => {
    expect(getStartupJianyingVersionWarning('10.8.0')).toBeNull();
    expect(getStartupJianyingVersionWarning('10.9.beta')).toBe(
      '当前仅支持剪映专业版 10.0-10.9，检测到 10.9.beta，生成草稿可能无法打开。',
    );
    expect(getStartupJianyingVersionWarning(null)).toBeNull();
  });
});
