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

export const ChatView = ({ isDarkMode, vscode }: ChatViewProps) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const messagesEndRef = useRef<null | HTMLDivElement>(null);

    const theme = isDarkMode ? 'dark' : 'light';

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            if (message.type === 'receiveMessage') {
                setMessages(prevMessages => [...prevMessages, { text: message.message, sender: 'bot' }]);
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = () => {
        if (inputMessage.trim() !== '') {
            setMessages(prevMessages => [...prevMessages, { text: inputMessage, sender: 'user' }]);
            vscode.postMessage({ type: 'sendMessage', text: inputMessage });
            setInputMessage('');
        }
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
                    <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        className={`flex-1 p-2 border rounded-l-lg ${theme}`}
                        placeholder="Type a message..."
                    />
                    <button
                        onClick={sendMessage}
                        className={`p-2 border rounded-r-lg bg-blue-500 text-white ${theme}`}
                    >
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};