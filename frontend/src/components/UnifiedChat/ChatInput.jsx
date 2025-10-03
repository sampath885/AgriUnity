import React, { useState } from 'react';
import useUserStore from '../../store';
import './ChatInput.css';

function ChatInput({ onSend, disabled = false, placeholder = "Type your message..." }) {
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  // Get user role from store
  const user = useUserStore((state) => state.user);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      setIsTyping(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setMessage(value);
    
    // Typing indicator
    if (value.trim()) {
      setIsTyping(true);
    } else {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearInput = () => {
    setMessage('');
    setIsTyping(false);
  };

  // Simple suggestions based on user role
  const getSimpleSuggestions = () => {
    if (user?.role === 'BUYER') {
      return [
        'What is the current market price?',
        'When can you deliver?',
        'What is the quality guarantee?'
      ];
    } else {
      return [
        'What is the current market price?',
        'When will the buyer arrive?',
        'Where is the collection hub?'
      ];
    }
  };

  const handleSuggestion = (suggestion) => {
    setMessage(suggestion);
  };

  return (
    <div className="chat-input">
      {/* Simple Suggestions */}
      <div className="simple-suggestions">
        {getSimpleSuggestions().map((suggestion, index) => (
          <button
            key={index}
            className="suggestion-chip"
            onClick={() => handleSuggestion(suggestion)}
            title={suggestion}
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* Simple Input Form */}
      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-container">
          {/* Message Input */}
          <div className="message-input-wrapper">
            <textarea
              value={message}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder={disabled ? 'Chat is disabled' : placeholder}
              disabled={disabled}
              className="message-input"
              rows="1"
              style={{
                minHeight: '40px',
                maxHeight: '120px',
                resize: 'none'
              }}
            />
            
            {/* Simple Typing Indicator */}
            {isTyping && (
              <div className="typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            )}
          </div>

          {/* Simple Action Buttons */}
          <div className="input-actions">
            {message.trim() && (
              <button
                type="button"
                className="clear-button"
                onClick={clearInput}
                title="Clear message"
              >
                ✕
              </button>
            )}
            
            <button
              type="submit"
              disabled={!message.trim() || disabled}
              className="send-button"
              title="Send message"
            >
              📤
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default ChatInput;
