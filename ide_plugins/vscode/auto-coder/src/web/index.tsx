import * as React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css'
import { CreateYAMLView } from './create_yaml';

declare global {
    interface Window {
        acquireVsCodeApi(): any;
        vscodeColorTheme: number;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('root');
    const root = createRoot(container!);
    const colorTheme = window.vscodeColorTheme;
    const vscode = window.acquireVsCodeApi();
    const isDarkMode = colorTheme === 1;
    root.render(<CreateYAMLView isDarkMode={isDarkMode} vscode={vscode} />);
});