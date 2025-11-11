import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["aws/functions/__tests__/**/*.test.mjs"],
    environment: "node",
  },
});


