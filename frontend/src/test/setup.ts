import "@testing-library/jest-dom/vitest";

function createStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  };
}

function ensureStorage(name: "localStorage" | "sessionStorage") {
  if (window[name]) return;
  const storage = createStorage();
  Object.defineProperty(window, name, { configurable: true, value: storage });
  Object.defineProperty(globalThis, name, { configurable: true, value: storage });
}

ensureStorage("localStorage");
ensureStorage("sessionStorage");
