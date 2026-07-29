import type { ExtractedField } from "../types/documents";

export function ExtractedFieldRow({ label, field }: { label: string; field: ExtractedField<string | number | boolean> }) {
  return <tr><th scope="row">{label}</th><td>{field.value === null ? "없음" : String(field.value)}</td><td>{field.status}</td></tr>;
}
