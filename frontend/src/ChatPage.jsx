// frontend/src/ChatPage.jsx
import React, { useState, useEffect, useRef } from 'react';
import useUserStore from './store';
import './ChatPage.css';

function ChatPage() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const token = useUserStore((state) => state.token);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load last chat history on mount
    useEffect(() => {
        const loadHistory = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/chatbot/ask/', {
                    method: 'GET',
                    headers: {
                        'Authorization': `Token ${token}`
                    }
                });
                if (response.ok) {
                    const data = await response.json();
                    setMessages(
                        (data || []).map(m => ({ sender: m.sender === 'agent' ? 'ai' : 'user', text: m.content }))
                    );
                }
            } catch (e) {
                // ignore
            }
        };
        if (token) loadHistory();
    }, [token]);


    const handleSend = async () => {
        if (input.trim() === '' || isLoading) return;

        const userMessage = { sender: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        
        const currentInput = input;
        setInput('');
        setIsLoading(true);

        // --- DEBUG LOGS ---
        console.log("Preparing to send API request...");
        console.log("Auth Token being used:", token);
        // ------------------

        try {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Token ${token}`
            };
            
            console.log("Request Headers being sent:", headers); // DEBUG LOG

            const response = await fetch('http://localhost:8000/api/chatbot/ask/', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ message: currentInput })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Failed to get a response from the server.");
            }

            const data = await response.json();
            const aiMessage = { sender: 'ai', text: data.answer };
            setMessages(prev => [...prev, aiMessage]);

        } catch (error) {
            console.error("Chat error:", error);
            const errorMessage = { sender: 'ai', text: 'Sorry, I encountered an error. Please check your connection or try again.' };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <div className="message-list">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        <div className="message-bubble">{msg.text}</div>
                    </div>
                ))}
                {isLoading && (
                    <div className="message ai">
                        <div className="message-bubble loading-bubble">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Ask about crops, prices, or schemes..."
                    disabled={isLoading}
                />
                <button onClick={handleSend} disabled={isLoading}>
                    Send
                </button>
            </div>
        </div>
    );
}

export default ChatPage;