import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/review/",
  build: {
    outDir: "../classsnap/web/dist",
    emptyOutDir: true,
  },
});
