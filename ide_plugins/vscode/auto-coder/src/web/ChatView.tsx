import * as React from 'react';
import { useState, useEffect, useRef, useCallback } from 'react';
import { pollResult, checkBackendReady, fetchConfigOptions, fetchFileList } from './utils';
import { handleCoding } from './coding';
import './dark.css';
import './chatAnimation.css';
import { handleIndexBuild } from './index_query';
interface ChatViewProps {
    isDarkMode: boolean;
    vscode: any;
}

interface Message {
    text: string;
    sender: 'user' | 'bot';
    animationKey?: string;
}

interface LogMessage {
    text: string;
    timestamp: string;
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
    const [autoCoderServerPort, setAutoCoderServerPort] = useState<number | null>(null);
    const [isBackendReady, setIsBackendReady] = useState(false);

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const [files, setFiles] = useState<string[]>([]);
    const [selectedCommand, setSelectedCommand] = useState('/chat');
    const [confSubCommand, setConfSubCommand] = useState('/set');
    const [configOptions, setConfigOptions] = useState<string[]>([]);

    const [awaitingUserResponse, setAwaitingUserResponse] = useState(false);

    const messagesRef = useRef(messages);

    //输入框添加自动补全功能的状态存储
    const [showAutoComplete, setShowAutoComplete] = useState(false);
    const [filteredOptions, setFilteredOptions] = useState<string[]>([]);
    const [cursorPosition, setCursorPosition] = useState({ top: 0, left: 0 });
    const inputRef = useRef<HTMLInputElement>(null);

    const theme = isDarkMode ? 'dark' : 'light';

    // 新增日志状态
    const [logMessages, setLogMessages] = useState<LogMessage[]>([]);
    const logMessagesEndRef = useRef<null | HTMLDivElement>(null);

    // 新增日志面板最小化状态
    const [isLogPaneMinimized, setIsLogPaneMinimized] = useState(false);


    const updateCursorPosition = useCallback(() => {
        if (inputRef.current) {
            const inputElement = inputRef.current;
            const cursorPosition = inputElement.selectionStart;
            if (cursorPosition === null) {
                return;
            }
            const textBeforeCursor = inputElement.value.substring(0, cursorPosition);
            const dummyElement = document.createElement('span');
            dummyElement.style.font = window.getComputedStyle(inputElement).font;
            dummyElement.style.visibility = 'hidden';
            dummyElement.style.position = 'absolute';
            dummyElement.textContent = textBeforeCursor;
            document.body.appendChild(dummyElement);

            const inputRect = inputElement.getBoundingClientRect();
            const dummyRect = dummyElement.getBoundingClientRect();

            document.body.removeChild(dummyElement);

            setCursorPosition({
                top: inputRect.top + inputRect.height,
                left: inputRect.left + dummyRect.width
            });
        }
    }, []);

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

    const confSubCommands = ['/set', '/drop', '/list'];

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
            checkBackendReady(autoCoderServerPort, setIsBackendReady);
        }
    }, [autoCoderServerPort]);


    useEffect(() => {
        if (isBackendReady) {
            updateFileList();
            updateConfigOptions();
        }
    }, [isBackendReady]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        messagesRef.current = messages;
    }, [messages]);

    useEffect(() => {
        logMessagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logMessages]);

    const updateFileList = async () => {
        const fileList = await fetchFileList(autoCoderServerPort);
        setFiles(fileList);
        if (fileList.length > 0) {
            const fileListMessage = `You can ask about the following files: ${fileList.join(', ')}`;
            setMessages([{ text: fileListMessage, sender: 'bot' }]);
        } else {
            setMessages([{ text: "There are no files available to ask about at the moment.", sender: 'bot' }]);
        }
    };

    const updateConfigOptions = async () => {
        const options = await fetchConfigOptions(autoCoderServerPort);
        setConfigOptions(options);
    };

    const sendMessage = async () => {
        if (!isLoading) {
            setIsLoading(true);
            const newUserMessage: Message = {
                text: inputMessage,
                sender: 'user',
                animationKey: `msg-${Date.now()}`
            };
            setMessages(prevMessages => [...prevMessages, newUserMessage]);
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
                        if (confSubCommand === '/set') {
                            const [key, value] = inputMessage.split(':').map(s => s.trim());
                            request = {
                                endpoint: '/conf',
                                body: { key, value } as ConfRequest
                            };
                        } else if (confSubCommand === '/drop') {
                            request = {
                                endpoint: `/conf/${inputMessage.trim()}`,
                                body: {} as QueryRequest
                            };
                        } else {
                            request = {
                                endpoint: '/conf/list',
                                body: {} as QueryRequest
                            };
                        }
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

                const endpoint = request.endpoint;

                if (endpoint === '/coding') {
                    if (!awaitingUserResponse) {
                        handleCoding(
                            inputMessage,
                            autoCoderServerPort,
                            (text, sender) => {
                                setMessages(prevMessages => {
                                    const newMessages = [...prevMessages, { text, sender }];
                                    return newMessages;
                                });
                            },
                            setAwaitingUserResponse,
                            () => messagesRef.current
                        );

                    }
                    return;
                }

                const response = await fetch(`http://127.0.0.1:${port}${request.endpoint}`, {
                    method: confSubCommand === '/drop' ? 'DELETE' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(request.body),
                });

                const data = await response.json();

                if (endpoint === '/index/build') {
                    const requestId = data.request_id;
                    setMessages(prevMessages => [...prevMessages, 
                        { text: `Indexing request is submit. Check the log pane`, sender: 'bot' }]);
                    handleIndexBuild(autoCoderServerPort, requestId,addLogMessage);
                    return    
                }

                if (endpoint === '/chat' || endpoint == "/ask") {
                    const requestId = data.request_id;

                    const _pollResult = await pollResult(autoCoderServerPort || 8081, requestId, (text) => {
                        setMessages(prevMessages => {
                            const newMessages = [...prevMessages];
                            const lastMessage = newMessages[newMessages.length - 1];
                            if (lastMessage.sender === 'bot') {
                                lastMessage.text = text;
                            } else {
                                newMessages.push({
                                    text,
                                    sender: 'bot',
                                    animationKey: `msg-${Date.now()}`
                                });
                            }
                            return newMessages;
                        });
                    });
                    if (_pollResult.status === 'failed') {
                        setMessages(prevMessages => [...prevMessages, { text: 'Failed to get response', sender: 'bot' }]);
                    }
                } else {
                    if ("message" in data) {
                        setMessages(prevMessages => [...prevMessages, { text: data.message, sender: 'bot' }]);
                    }
                    else {
                        setMessages(prevMessages => [...prevMessages, { text: JSON.stringify(data, null, 2), sender: 'bot' }]);
                    }

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

    const addLogMessage = (text: string) => {
        const timestamp = new Date().toLocaleTimeString();
        setLogMessages(prevLogs => [...prevLogs, { text, timestamp }]);
    };

    const handleCommandSelect = (command: string) => {
        setSelectedCommand(command);
        if (command === '/conf') {
            setConfSubCommand('/set');
        }
        setShowAutoComplete(false);
    };

    const handleConfSubCommandSelect = (subCommand: string) => {
        setConfSubCommand(subCommand);
        setShowAutoComplete(false);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setInputMessage(value);

        if (selectedCommand === '/conf' && confSubCommand === '/set') {
            const filteredOptions = configOptions.filter(option =>
                option.toLowerCase().startsWith(value.toLowerCase())
            );
            setFilteredOptions(filteredOptions);
            setShowAutoComplete(filteredOptions.length > 0);
        } else {
            setShowAutoComplete(false);
        }
        updateCursorPosition();
    };

    const handleAutoCompleteSelect = (option: string) => {
        setInputMessage(`${option}:`);
        setShowAutoComplete(false);
    };

    const handleInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    if (!isBackendReady)
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-lg font-semibold">Waiting Auto-Coder.Chat Ready...</p>
                </div>
            </div>
        );
    return (
        <div className={`flex flex-col h-screen ${theme}`}>
            <div className="flex flex-1 overflow-hidden">
                <div className="flex-1 overflow-y-auto p-4">
                    {messages.map((message) => (
                        <div
                            key={message.animationKey}
                            className={`mb-4 ${message.sender === 'user' ? 'text-right' : 'text-left'} message-animation`}
                        >
                            <div
                                className={`inline-block p-2 rounded-lg ${message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'
                                    }`}
                            >
                                {message.text.split('\n').map((line, i) => (
                                    <React.Fragment key={i}>
                                        {line}
                                        {i !== message.text.split('\n').length - 1 && <br />}
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
                <div id="log_pane" className={`${isLogPaneMinimized ? 'w-10' : 'w-1/3'} overflow-y-auto p-4 border-l relative transition-all duration-300`}>
                    <button
                        onClick={() => setIsLogPaneMinimized(!isLogPaneMinimized)}
                        className="absolute top-2 right-2 text-xl cursor-pointer transition-transform duration-300 hover:scale-110"
                        title={isLogPaneMinimized ? "Maximize" : "Minimize"}
                    >
                        {isLogPaneMinimized ? '⤢' : '⤡'}
                    </button>
                    {!isLogPaneMinimized && (
                        <>
                            <h3 className="text-lg font-semibold mb-2">Log Messages</h3>
                            {logMessages.map((log, index) => (
                                <div key={index} className="mb-2">
                                    <span className="text-sm text-gray-500">[{log.timestamp}] </span>
                                    <span>{log.text}</span>
                                </div>
                            ))}
                            <div ref={logMessagesEndRef} />
                        </>
                    )}
                </div>
            </div>
            <div className="p-4 border-t">
                <div className="flex flex-col space-y-4 mb-4">
                    <div className="flex space-x-2">
                        <select
                            value={selectedCommand}
                            onChange={(e) => handleCommandSelect(e.target.value)}
                            className={`p-2 border rounded-lg ${theme}`}
                            disabled={isLoading}
                        >
                            {commands.map((command) => (
                                <option key={command} value={command}>
                                    {command}
                                </option>
                            ))}
                        </select>
                        {selectedCommand === '/conf' && (
                            <select
                                value={confSubCommand}
                                onChange={(e) => handleConfSubCommandSelect(e.target.value)}
                                className={`p-2 border rounded-lg ${theme}`}
                                disabled={isLoading}
                            >
                                {confSubCommands.map((subCommand) => (
                                    <option key={subCommand} value={subCommand}>
                                        {subCommand}
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>
                    <div className="flex space-x-2">
                        <input
                            ref={inputRef}
                            type="text"
                            value={inputMessage}
                            onChange={handleInputChange}
                            onKeyPress={handleInputKeyPress}
                            className={`flex-1 p-2 border rounded-lg ${theme}`}
                            placeholder="Type a message..."
                            disabled={isLoading}
                            list="config-options"
                            onSelect={updateCursorPosition}
                            onKeyUp={updateCursorPosition}
                            onClick={updateCursorPosition}
                        />
                        <button
                            onClick={sendMessage}
                            className={`p-2 border rounded-lg bg-blue-500 text-white ${theme}`}
                            disabled={isLoading}
                        >
                            {isLoading ? 'Sending...' : 'Send'}
                        </button>
                    </div>
                    <div className="h-16"> {/* Added a fixed height div for autocomplete spacing */}
                        {showAutoComplete && (
                            <div
                                className={`absolute z-10 bg-white border border-gray-300 rounded-md shadow-lg ${theme}`}
                                style={{
                                    top: `${cursorPosition.top}px`,
                                    left: `${cursorPosition.left}px`,
                                    maxHeight: '200px',
                                    overflowY: 'auto'
                                }}
                            >
                                {filteredOptions.map((option, index) => (
                                    <div
                                        key={index}
                                        className={`p-2 cursor-pointer hover:bg-gray-100 ${theme}`}
                                        onClick={() => handleAutoCompleteSelect(option)}
                                    >
                                        {option}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};