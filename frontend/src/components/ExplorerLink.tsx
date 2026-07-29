export function ExplorerLink({ signature }: { signature: string }) {
  return <a href={`https://explorer.solana.com/tx/${encodeURIComponent(signature)}?cluster=devnet`} target="_blank" rel="noreferrer">Solana Explorer에서 보기</a>;
}
