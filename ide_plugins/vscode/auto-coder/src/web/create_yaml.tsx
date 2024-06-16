import * as React from 'react';
import { useState } from 'react';

export const CreateYAMLView: React.FC = () => {
    const [fileName, setFileName] = useState('');
    const [prefix, setPrefix] = useState('');

    const handleSubmit = () => {
        const message = { fileName, prefix };
        window.parent.postMessage({ type: 'submitForm', value: message }, '*');
    };

    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold mb-4">Create YAML File</h1>
            <div className="mb-4">
                <label htmlFor="fileName" className="block text-sm font-medium text-gray-700">
                    File Name
                </label>
                <div className="mt-1">
                    <input
                        type="text"
                        name="fileName"
                        id="fileName"
                        value={fileName}
                        onChange={(e) => setFileName(e.target.value)}
                        className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                </div>
            </div>
            <div className="mb-4">
                <label htmlFor="prefix" className="block text-sm font-medium text-gray-700">
                    Prefix
                </label>
                <div className="mt-1">
                    <input
                        type="text"
                        name="prefix"
                        id="prefix"
                        value={prefix}
                        onChange={(e) => setPrefix(e.target.value)}
                        className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
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
    );
};