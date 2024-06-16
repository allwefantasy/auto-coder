import * as React from 'react';
import { useState } from 'react';
import './dark.css';

interface CreateYAMLViewProps {
    isDarkMode: boolean;
    vscode: any;
}

export const CreateYAMLView = ({ isDarkMode,vscode }: CreateYAMLViewProps) => {
    const [fileName, setFileName] = useState('');
    const [prefix, setPrefix] = useState('');

    const handleSubmit = () => {        
        const message = { fileName, prefix };
        vscode.postMessage({ type: 'submitForm', value: message }, '*');
    };

    const theme = isDarkMode ? 'dark' : 'light';

    return (
        <div className={`p-4 flex justify-center ${theme}`}>
            <div className="max-w-md w-full">
                <h1 className="text-2xl font-bold mb-4">Create YAML File</h1>
                <div className="mb-4">
                    <label htmlFor="fileName" className="block text-sm font-medium">
                        File Name
                    </label>
                    <div className="mt-1">
                        <input
                            type="text"
                            name="fileName"
                            id="fileName"
                            value={fileName}
                            onChange={(e) => setFileName(e.target.value)}
                            className={`block w-full sm:text-sm rounded-md ${isDarkMode ? 'dark' : ''}`}
                        />
                    </div>
                </div>
                <div className="mb-4">
                    <label htmlFor="prefix" className="block text-sm font-medium">
                        Prefix
                    </label>
                    <div className="mt-1">
                        <input
                            type="text"
                            name="prefix"
                            id="prefix"
                            value={prefix}
                            onChange={(e) => setPrefix(e.target.value)}
                            className={`block w-full sm:text-sm rounded-md ${isDarkMode ? 'dark' : ''}`}
                        />
                    </div>
                </div>
                <button
                    type="button"
                    onClick={handleSubmit}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    Create
                </button>
            </div>
        </div>
    );
};