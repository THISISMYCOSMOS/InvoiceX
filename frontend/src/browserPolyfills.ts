import { Buffer } from "buffer";

const browserGlobals = globalThis as typeof globalThis & {
  Buffer?: typeof Buffer;
};

browserGlobals.Buffer ??= Buffer;
