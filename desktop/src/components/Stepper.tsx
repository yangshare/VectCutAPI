interface StepperProps {
  current: number;
  steps: string[];
  onStepClick?: (idx: number) => void;
}

const listStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
  gap: 8,
  padding: 0,
  margin: 0,
  listStyle: 'none',
} satisfies React.CSSProperties;

function getStepState(idx: number, current: number): 'done' | 'active' | 'pending' {
  if (idx < current) {
    return 'done';
  }
  if (idx === current) {
    return 'active';
  }
  return 'pending';
}

export default function Stepper({ current, steps, onStepClick }: StepperProps) {
  return (
    <nav aria-label="流程步骤">
      <ol style={listStyle}>
        {steps.map((step, idx) => {
          const state = getStepState(idx, current);
          const isActive = state === 'active';
          const label = state === 'done' ? '已完成' : state === 'active' ? '当前' : '待处理';

          return (
            <li key={step}>
              <button
                type="button"
                onClick={() => onStepClick?.(idx)}
                aria-current={isActive ? 'step' : undefined}
                style={{
                  width: '100%',
                  minHeight: 52,
                  border: `1px solid ${isActive ? '#2563eb' : state === 'done' ? '#1f8a4c' : '#cbd5e1'}`,
                  borderRadius: 6,
                  background: isActive ? '#eff6ff' : state === 'done' ? '#f0fdf4' : '#f8fafc',
                  color: state === 'pending' ? '#64748b' : '#0f172a',
                  cursor: onStepClick ? 'pointer' : 'default',
                  textAlign: 'left',
                  padding: '8px 10px',
                  font: 'inherit',
                  overflow: 'hidden',
                }}
              >
                <span style={{ display: 'block', fontSize: 12, color: '#475569' }}>
                  {idx + 1}. {label}
                </span>
                <span style={{ display: 'block', fontWeight: 700, lineHeight: 1.35, wordBreak: 'break-word' }}>
                  {step}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
