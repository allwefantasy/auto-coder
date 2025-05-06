import { defineConfig } from '@vscode/test-cli';

export default defineConfig({
	files: '${workspaceFolder}/out/test/**/*.test.js',
});
