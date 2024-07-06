import * as React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css'
import { CreateYAMLView } from './create_yaml';
import { ChatView } from './ChatView';

declare global {
    interface Window {
        acquireVsCodeApi(): any;
        vscodeColorTheme: boolean;
        view:string;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('root');
    const root = createRoot(container!);
    const colorTheme = window.vscodeColorTheme;
    const vscode = window.acquireVsCodeApi();    
    const isDarkMode = colorTheme;    
    const view = window.view;

    if (view === 'chat') {
        root.render(<ChatView isDarkMode={isDarkMode} vscode={vscode} />);
    } else {
        root.render(<CreateYAMLView isDarkMode={isDarkMode} vscode={vscode} />);
    }
});