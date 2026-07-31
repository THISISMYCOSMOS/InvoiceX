import { validateDocumentFile } from "./fileValidation";

test("rejects a document larger than 20 MB", () => {
  const file = new File(
    [new Uint8Array(20 * 1024 * 1024 + 1)],
    "invoice.pdf",
    { type: "application/pdf" },
  );

  expect(validateDocumentFile(file)).toEqual({
    valid: false,
    message: "파일은 20MB 이하여야 합니다.",
  });
});

test("accepts a PDF at the 20 MB boundary", () => {
  const file = new File(
    [new Uint8Array(20 * 1024 * 1024)],
    "invoice.pdf",
    { type: "application/pdf" },
  );

  expect(validateDocumentFile(file)).toEqual({ valid: true });
});
