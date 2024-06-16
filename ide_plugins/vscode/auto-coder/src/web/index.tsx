import * as React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css'
import { CreateYAMLView } from './create_yaml';

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('root');
    const root = createRoot(container!);
    const colorTheme = (window as any).vscodeColorTheme;
    const isDarkMode = colorTheme === 1; 
    root.render(<CreateYAMLView isDarkMode={isDarkMode}/>);
});