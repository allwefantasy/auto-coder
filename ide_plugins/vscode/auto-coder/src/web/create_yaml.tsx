import * as React from 'react';
import { useState } from 'react';
import './dark.css';

interface CreateYAMLViewProps {
    isDarkMode: boolean;
    vscode: any;
}

export const CreateYAMLView = ({ isDarkMode, vscode }: CreateYAMLViewProps) => {
    const [fileName, setFileName] = useState('');
    const [prefix, setPrefix] = useState('');

    const handleSubmit = () => {
        if (!fileName.trim()) {
            alert('Please enter a file name');
            return;
        }
        const message = { fileName, prefix };
        vscode.postMessage({ type: 'submitForm', value: message }, '*');
    };

    const theme = isDarkMode ? 'dark' : 'light';

    return (
        <div className={`p-6 flex justify-center items-center min-h-screen bg-gray-100 ${theme}`}>
            <div className="max-w-md w-full bg-white shadow-md rounded-lg p-8">
                <h1 className="text-3xl font-bold mb-6 text-center text-gray-800">Create YAML File</h1>
                <div className="space-y-6">
                    <div>
                        <label htmlFor="fileName" className="block text-sm font-medium text-gray-700 mb-1">
                            File Name
                        </label>
                        <input
                            type="text"
                            name="fileName"
                            id="fileName"
                            value={fileName}
                            onChange={(e) => setFileName(e.target.value)}
                            className={`block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${isDarkMode ? 'dark' : ''}`}
                            placeholder="Enter file name"
                        />
                    </div>
                    <div>
                        <label htmlFor="prefix" className="block text-sm font-medium text-gray-700 mb-1">
                            Prefix (Optional)
                        </label>
                        <input
                            type="text"
                            name="prefix"
                            id="prefix"
                            value={prefix}
                            onChange={(e) => setPrefix(e.target.value)}
                            className={`block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${isDarkMode ? 'dark' : ''}`}
                            placeholder="Enter prefix (optional)"
                        />
                    </div>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
                    >
                        Create YAML File
                    </button>
                </div>
            </div>
        </div>
    );
};