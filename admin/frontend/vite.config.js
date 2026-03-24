import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
    plugins: [vue()],
    server: {
        host: "0.0.0.0",
        port: 5174,
        proxy: {
            "/admin-api": {
                target: "http://localhost:8100",
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/admin-api/, ""),
            },
            "/api": {
                target: "http://localhost:8080",
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ""),
            },
        },
    },
});
