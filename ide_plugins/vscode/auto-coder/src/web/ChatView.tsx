import * as React from 'react';
import { useState, useEffect, useRef } from 'react';
import './dark.css';

interface ChatViewProps {
    isDarkMode: boolean;
    vscode: any;
}

interface Message {
    text: string;
    sender: 'user' | 'bot';
}

interface FilesRequest {
    files: string[];
}

interface QueryRequest {
    query: string;
}

interface ConfRequest {
    key: string;
    value: string;
}

interface ApiRequest {
    endpoint: string;
    body: FilesRequest | QueryRequest | ConfRequest;
}

export const ChatView = ({ isDarkMode, vscode }: ChatViewProps) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [autoCoderServerPort, setAutoCoderServerPort] = useState<number | null>(null);
    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const [files, setFiles] = useState<string[]>([]);
    const [selectedCommand, setSelectedCommand] = useState('/chat');

    const theme = isDarkMode ? 'dark' : 'light';

    const commands = [
        '/add_files',
        '/remove_files',
        '/list_files',
        '/conf',
        '/coding',
        '/chat',
        '/ask',
        '/revert',
        '/index/query',
        '/index/build',
        '/exclude_dirs',
        '/shell'
    ];

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            if (message.type === 'autoCoderServerPort') {
                setAutoCoderServerPort(message.port);
            }
        };
        window.addEventListener('message', handleMessage);
        vscode.postMessage({ type: 'getAutoCoderServerPort' });
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    useEffect(() => {
        if (autoCoderServerPort) {
            fetchFileList();
        }
    }, [autoCoderServerPort]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const fetchFileList = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:${autoCoderServerPort}/list_files`);
            const data = await response.json();
            setFiles(data.files);
            if (data.files.length > 0) {
                const fileListMessage = `You can ask about the following files: ${data.files.join(', ')}`;
                setMessages([{ text: fileListMessage, sender: 'bot' }]);
            } else {
                setMessages([{ text: "There are no files available to ask about at the moment.", sender: 'bot' }]);
            }
        } catch (error) {
            console.error('Error fetching file list:', error);
            setMessages([{ text: "An error occurred while fetching the file list.", sender: 'bot' }]);
        }
    };

    const sendMessage = async () => {
        if (inputMessage.trim() !== '' && !isLoading) {
            setIsLoading(true);
            setMessages(prevMessages => [...prevMessages, { text: inputMessage, sender: 'user' }]);

            try {
                const port = autoCoderServerPort;
                let request: ApiRequest;

                switch (selectedCommand) {
                    case '/add_files':
                    case '/remove_files':
                    case '/exclude_dirs':
                        request = {
                            endpoint: selectedCommand,
                            body: { files: inputMessage.split(',').map(f => f.trim()) } as FilesRequest
                        };
                        break;
                    case '/conf':
                        const [key, value] = inputMessage.split(':').map(s => s.trim());
                        request = {
                            endpoint: '/conf',
                            body: { key, value } as ConfRequest
                        };
                        break;
                    case '/list_files':
                    case '/revert':
                    case '/index/build':
                        request = {
                            endpoint: selectedCommand,
                            body: {} as QueryRequest
                        };
                        break;
                    default:
                        request = {
                            endpoint: selectedCommand === '/chat' ? '/chat' : selectedCommand,
                            body: { query: inputMessage } as QueryRequest
                        };
                        break;
                }

                const response = await fetch(`http://127.0.0.1:${port}${request.endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(request.body),
                });

                const data = await response.json();
                const endpoint = request.endpoint;

                if (endpoint === '/chat' || endpoint === '/coding') {
                    const requestId = data.request_id;
                    let result = { result: 'NO RESPONSE' };
                    let count = 90;
                    do {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        count--;
                        const resultResponse = await fetch(`http://127.0.0.1:${port}/result/${requestId}`);
                        if (resultResponse.status === 200) {
                            result = await resultResponse.json();
                            break;
                        }
                    } while (count > 0);
                    setMessages(prevMessages => [...prevMessages, { text: result.result, sender: 'bot' }]);
                } else {
                    setMessages(prevMessages => [...prevMessages, { text: JSON.stringify(data, null, 2), sender: 'bot' }]);
                }

                if (endpoint === '/list_files') {
                    setFiles(data.files);
                }
            } catch (error) {
                console.error('Error:', error);
                setMessages(prevMessages => [...prevMessages, { text: 'An error occurred while processing the command.', sender: 'bot' }]);
            } finally {
                setIsLoading(false);
                setInputMessage('');
            }
        }
    };

    const handleCommandSelect = (command: string) => {
        setSelectedCommand(command);
        setInputMessage(command + ' ');
    };

    return (
        <div className={`flex flex-col h-screen ${theme}`}>
            <div className="flex-1 overflow-y-auto p-4">
                {messages.map((message, index) => (
                    <div key={index} className={`mb-4 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}>
                        <span className={`inline-block p-2 rounded-lg ${message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'}`}>
                            {message.text}
                        </span>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <div className="p-4 border-t">
                <div className="flex">
                    <select
                        value={selectedCommand}
                        onChange={(e) => handleCommandSelect(e.target.value)}
                        className={`p-2 border-t border-b ${theme}`}
                        disabled={isLoading}
                    >
                        {commands.map((command) => (
                            <option key={command} value={command}>
                                {command}
                            </option>
                        ))}
                    </select>
                    <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        className={`flex-1 p-2 border rounded-l-lg ${theme}`}
                        placeholder="Type a message..."
                        disabled={isLoading}
                    />

                    <button
                        onClick={sendMessage}
                        className={`p-2 border rounded-r-lg bg-blue-500 text-white ${theme}`}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Sending...' : 'Send'}
                    </button>
                </div>
            </div>
        </div>
    );
};