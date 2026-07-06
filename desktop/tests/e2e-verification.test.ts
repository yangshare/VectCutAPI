import { readFile } from 'fs/promises';
import { describe, expect, it } from 'vitest';

const reportUrl = new URL('../docs/e2e-verification.md', import.meta.url);

async function readReport() {
  return readFile(reportUrl, 'utf-8');
}

describe('Task 12 e2e verification report', () => {
  it('records automated verification commands and build output checks', async () => {
    const report = await readReport();

    expect(report).toContain('# Task 12 全量测试与端到端验收报告');
    expect(report).toContain('npm test');
    expect(report).toContain('npx tsc --noEmit -p tsconfig.json');
    expect(report).toContain('npx tsc --noEmit -p tsconfig.node.json');
    expect(report).toContain('npm run build');
    expect(report).toContain('out/main');
    expect(report).toContain('out/preload');
    expect(report).toContain('out/renderer');
  });

  it('keeps the full Task 12 acceptance checklist with honest execution status', async () => {
    const report = await readReport();

    const task12Checklist = [
      '能导入母版（选剪映草稿文件夹 → 打包上传 → 返回槽位）',
      '能配置 5 类素材槽位（video/audio/bgm/subtitle/cover）',
      '能为槽位选择本地素材并自动读元数据',
      '能生成草稿并下载',
      '草稿自动解压导入剪映 draft 目录',
      '字幕样式基本保留（字体/颜色/位置）',
      '时长对齐正确（配音基准）',
      '服务器地址可在设置页配置 + 测试连接',
      '错误信息用户友好（不出现技术术语给最终用户）',
      'Windows 可打包为 .exe 安装包',
      '安装指南含 SmartScreen 绕过说明',
    ];

    for (const item of task12Checklist) {
      expect(report).toContain(item);
    }

    expect(report).toContain('未执行/需人工联调');
    expect(report).toContain('缺失条件');
  });

  it('documents backend integration steps and MVP specification coverage', async () => {
    const report = await readReport();

    expect(report).toContain('python run_http.py');
    expect(report).toContain('npm run dev');
    expect(report).toContain('真实剪映草稿');
    expect(report).toContain('draft_content.json');
    expect(report).toContain('完整 4 步向导');
    expect(report).toContain('规格 §18.4 MVP 验收清单');
    expect(report).toContain('口播/Vlog/教程');
    expect(report).toContain('Golden 测试');
    expect(report).toContain('边界情况测试');
  });
});
