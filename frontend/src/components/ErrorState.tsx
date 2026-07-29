export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "요청을 처리할 수 없습니다.";
  return <p role="alert">{message}</p>;
}
