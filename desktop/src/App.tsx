import { useState } from 'react';
import Stepper from './components/Stepper';
import GenerateImport from './pages/GenerateImport';
import MaterialFill from './pages/MaterialFill';
import SlotConfig from './pages/SlotConfig';
import TemplateManager from './pages/TemplateManager';
import type { MaterialMetadata, Slot } from './types';

const STEPS = ['导入母版', '槽位配置', '素材填充', '生成导入'];

export default function App() {
  const [step, setStep] = useState(0);
  const [templateId, setTemplateId] = useState('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlots, setSelectedSlots] = useState<Slot[]>([]);
  const [materials, setMaterials] = useState<MaterialMetadata[]>([]);

  function handleTemplateImported(importedTemplateId: string, importedSlots: Slot[]) {
    setTemplateId(importedTemplateId);
    setSlots(importedSlots);
    setSelectedSlots([]);
    setMaterials([]);
    setStep(1);
  }

  function handleConfigSaved(selected: Slot[]) {
    setSelectedSlots(selected);
    setMaterials([]);
    setStep(2);
  }

  function handleMaterialsReady(readyMaterials: MaterialMetadata[]) {
    setMaterials(readyMaterials);
    setStep(3);
  }

  function handleRestart() {
    setStep(0);
    setTemplateId('');
    setSlots([]);
    setSelectedSlots([]);
    setMaterials([]);
  }

  function handleStepClick(idx: number) {
    if (idx <= step) {
      setStep(idx);
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', color: '#0f172a', fontFamily: 'system-ui, sans-serif' }}>
      <main style={{ maxWidth: 1080, margin: '0 auto', padding: 24, display: 'grid', gap: 18 }}>
        <header style={{ display: 'grid', gap: 8 }}>
          <h1 style={{ margin: 0, fontSize: 28 }}>VectCut 模板套版</h1>
          <p style={{ margin: 0, color: '#475569' }}>
            按步骤导入剪映母版、选择槽位、填充素材并生成可导入草稿。
          </p>
        </header>

        <Stepper current={step} steps={STEPS} onStepClick={handleStepClick} />

        <div style={{ border: '1px solid #cbd5e1', borderRadius: 8, background: '#ffffff', padding: 18 }}>
          {step === 0 ? (
            <TemplateManager onTemplateImported={handleTemplateImported} />
          ) : null}
          {step === 1 ? (
            <SlotConfig templateId={templateId} slots={slots} onConfigSaved={handleConfigSaved} />
          ) : null}
          {step === 2 ? (
            <MaterialFill slots={selectedSlots} onMaterialsReady={handleMaterialsReady} />
          ) : null}
          {step === 3 ? (
            <GenerateImport templateId={templateId} materials={materials} onRestart={handleRestart} />
          ) : null}
        </div>
      </main>
    </div>
  );
}
