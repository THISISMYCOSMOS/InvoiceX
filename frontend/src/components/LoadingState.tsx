export function LoadingState({ label = "불러오는 중" }: { label?: string }) {
  return <p role="status">{label}</p>;
}
