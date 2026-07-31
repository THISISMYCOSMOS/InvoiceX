const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
const allowedMimeTypes = new Set(["application/pdf", "image/jpeg", "image/png"]);
const allowedExtensions = new Set(["pdf", "jpg", "jpeg", "png"]);

export type FileValidationResult = { valid: true } | { valid: false; message: string };

export function validateDocumentFile(file: File): FileValidationResult {
  const extension = file.name.split(".").pop()?.toLowerCase();
  const allowedType = allowedMimeTypes.has(file.type) || (extension !== undefined && allowedExtensions.has(extension));

  if (!allowedType) {
    return { valid: false, message: "PDF, JPG, JPEG, PNG 파일만 업로드할 수 있습니다." };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, message: "파일은 20MB 이하여야 합니다." };
  }

  return { valid: true };
}
