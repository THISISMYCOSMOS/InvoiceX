export function Brand({ className = "" }: { className?: string }) {
  return (
    <span className={`brand-mark ${className}`.trim()}>
      <span>Invoice</span>
      <span className="brand-mark__accent">X</span>
    </span>
  );
}
