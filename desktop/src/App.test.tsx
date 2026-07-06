import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('App', () => {
  it('renders the scaffold status', () => {
    const html = renderToStaticMarkup(<App />);

    expect(html).toContain('VectCut 模板套版');
    expect(html).toContain('脚手架就绪。任务 2 起逐步填充功能。');
  });
});
