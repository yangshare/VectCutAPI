import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import App from './App';
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
    expect(html).toContain('导入并解析槽位');
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
});
