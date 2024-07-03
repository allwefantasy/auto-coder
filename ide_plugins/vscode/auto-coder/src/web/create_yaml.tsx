import * as React from 'react';
import { useState } from 'react';
import './dark.css';

interface CreateYAMLViewProps {
    isDarkMode: boolean;
    vscode: any;
}

export const CreateYAMLView = ({ isDarkMode, vscode }: CreateYAMLViewProps) => {
    const [human_as_model, setHumanAsModel] = useState(false);
    const [auto_merge, setAutoMerge] = useState('editblock');
    const [skip_build_index, setSkipBuildIndex] = useState(false);
    const [skip_confirm, setSkipConfirm] = useState(true);
    const [include_file, setIncludeFile] = useState(['./base/base.yml']);
    const [query, setQuery] = useState('');
    const [urls, setUrls] = useState<string[]>([]);

    const handleSubmit = () => {
        const message = {
            human_as_model,
            auto_merge,
            skip_build_index,
            skip_confirm,
            include_file,
            query,
            urls
        };
        vscode.postMessage({ type: 'submitForm', value: message }, '*');
    };

    React.useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            switch (message.type) {
                case 'selectedPath':
                    setUrls([...urls, message.value]);
                    break;
                case 'submitFormResponse':
                    if (message.success) {
                        alert('YAML file created successfully!');
                    } else {
                        alert('Failed to create YAML file: ' + message.error);
                    }
                    break;
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, [urls]);

    const handleAddUrl = () => {
        vscode.postMessage({ type: 'selectPath' }, '*');
    };

    const handleRemoveUrl = (index: number) => {
        setUrls(urls.filter((_, i) => i !== index));
    };

    React.useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            switch (message.type) {
                case 'selectedPath':
                    setUrls([...urls, message.value]);
                    break;
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, [urls]);

    const theme = isDarkMode ? 'dark' : 'light';

    return (
        <div className={`p-6 flex justify-center items-center min-h-screen ${theme}`}>
            <div className={`max-w-2xl w-full shadow-md rounded-lg p-8 ${theme}`}>
                <h1 className={`text-3xl font-bold mb-6 text-center ${theme}`}>Create YAML File</h1>
                <div className="space-y-6">
                    <div>
                        <label htmlFor="query" className={`block text-sm font-medium mb-1 ${theme}`}>
                            Requirement Description / 需求描述
                        </label>
                        <textarea
                            name="query"
                            id="query"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                            placeholder="Enter your query"
                            rows={4}
                        />
                    </div>
                    <div>
                        <label className={`block text-sm font-medium mb-1 ${theme}`}>
                            Add Active Files / 添加活动文件
                        </label>
                        {urls.map((url, index) => (
                            <div key={index} className="flex items-center mb-2">
                                <input
                                    type="text"
                                    value={url}
                                    readOnly
                                    className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                                />
                                <button
                                    onClick={() => handleRemoveUrl(index)}
                                    className="ml-2 px-2 py-1 bg-red-500 text-white rounded"
                                >
                                    Remove
                                </button>
                            </div>
                        ))}
                        <button
                            onClick={handleAddUrl}
                            className={`mt-2 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out ${theme}`}
                        >
                            Add URL
                        </button>
                    </div>
                    <div>
                        <label htmlFor="human_as_model" className={`block text-sm font-medium mb-1 ${theme}`}>
                            whether human to answer questions / 是否人类来回答问题
                        </label>
                        <select
                            name="human_as_model"
                            id="human_as_model"
                            value={human_as_model.toString()}
                            onChange={(e) => setHumanAsModel(e.target.value === 'true')}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                        >
                            <option value="false">False</option>
                            <option value="true">True</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="auto_merge" className={`block text-sm font-medium mb-1 ${theme}`}>
                            Merge Method / 合并方法
                        </label>
                        <select
                            name="auto_merge"
                            id="auto_merge"
                            value={auto_merge}
                            onChange={(e) => setAutoMerge(e.target.value)}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                        >
                            <option value="editblock">Edit Block</option>
                            <option value="wholefile">Whole File</option>
                            <option value="diff">Diff</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="skip_build_index" className={`block text-sm font-medium mb-1 ${theme}`}>
                            Skip Build Index / 跳过构建索引
                        </label>
                        <select
                            name="skip_build_index"
                            id="skip_build_index"
                            value={skip_build_index.toString()}
                            onChange={(e) => setSkipBuildIndex(e.target.value === 'true')}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                        >
                            <option value="false">False</option>
                            <option value="true">True</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="skip_confirm" className={`block text-sm font-medium mb-1 ${theme}`}>
                            Skip File Selected Confirm / 跳过文件选择确认
                        </label>
                        <select
                            name="skip_confirm"
                            id="skip_confirm"
                            value={skip_confirm.toString()}
                            onChange={(e) => setSkipConfirm(e.target.value === 'true')}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                        >
                            <option value="true">True</option>
                            <option value="false">False</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="include_file" className={`block text-sm font-medium mb-1 ${theme}`}>
                            Base YAML / 基类YAML
                        </label>
                        <div>
                            {include_file.map((file, index) => (
                                <div key={index} className="flex items-center mb-2">
                                    <input
                                        type="text"
                                        value={file}
                                        onChange={(e) => {
                                            const newFiles = [...include_file];
                                            newFiles[index] = e.target.value;
                                            setIncludeFile(newFiles);
                                        }}
                                        className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 sm:text-sm ${theme}`}
                                        placeholder="Enter include file path"
                                    />
                                    <button
                                        onClick={() => {
                                            const newFiles = include_file.filter((_, i) => i !== index);
                                            setIncludeFile(newFiles);
                                        }}
                                        className="ml-2 px-2 py-1 bg-red-500 text-white rounded"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                            <button
                                onClick={() => setIncludeFile([...include_file, ''])}
                                className={`mt-2 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out ${theme}`}
                            >
                                Add Include File
                            </button>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out ${theme}`}
                    >
                        Create YAML File
                    </button>
                </div>
            </div>
        </div>
    );
};