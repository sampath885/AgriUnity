import React, { useState, useEffect, useRef } from 'react';
import './AIBargainingInterface.css';

const AIBargainingInterface = ({ dealGroup, buyer, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionData, setSessionData] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [logisticsData, setLogisticsData] = useState(null);
  const [bargainingStatus, setBargainingStatus] = useState('initializing');
  const [currentOffer, setCurrentOffer] = useState(null);
  const [pollStatus, setPollStatus] = useState(null);
  
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize bargaining session
  useEffect(() => {
    if (dealGroup && buyer) {
      initializeBargainingSession();
    }
  }, [dealGroup, buyer]);

  const initializeBargainingSession = async () => {
    try {
      setBargainingStatus('initializing');
      
      const response = await fetch(`/api/deals/advanced-bargaining/start-session/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          deal_group_id: dealGroup.id,
          buyer_id: buyer.id
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSessionData(data);
        setBargainingStatus('active');
        
        // Add welcome message
        addMessage('agent', data.agent_message || 'Welcome to advanced bargaining! How can I help you today?');
        
        // Load market and logistics data
        loadMarketData();
        loadLogisticsData();
      } else {
        throw new Error('Failed to start bargaining session');
      }
    } catch (error) {
      console.error('Error starting bargaining session:', error);
      setBargainingStatus('error');
      addMessage('system', '❌ Failed to start bargaining session. Please try again.');
    }
  };

  const loadMarketData = async () => {
    try {
      const response = await fetch(`/api/deals/advanced-bargaining/market-insights/${dealGroup.id}/`);
      if (response.ok) {
        const data = await response.json();
        setMarketData(data);
      }
    } catch (error) {
      console.error('Error loading market data:', error);
    }
  };

  const loadLogisticsData = async () => {
    try {
      const response = await fetch(`/api/deals/advanced-bargaining/logistics-optimization/${dealGroup.id}/`);
      if (response.ok) {
        const data = await response.json();
        setLogisticsData(data);
      }
    } catch (error) {
      console.error('Error loading logistics data:', error);
    }
  };

  const addMessage = (sender, content, data = null) => {
    const newMessage = {
      id: Date.now(),
      sender,
      content,
      timestamp: new Date(),
      data
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || bargainingStatus !== 'active') return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Add user message to chat
    addMessage('buyer', userMessage);
    setIsTyping(true);

    try {
      const response = await fetch(`/api/deals/advanced-bargaining/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          deal_group_id: dealGroup.id,
          buyer_id: buyer.id,
          message: userMessage,
          message_type: 'text'
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        // Add agent response
        addMessage('agent', data.message, data);
        
        // Handle different actions
        handleAgentAction(data);
        
      } else {
        throw new Error('Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addMessage('system', '❌ Failed to send message. Please try again.');
    } finally {
      setIsTyping(false);
    }
  };

  const handleAgentAction = (response) => {
    const action = response.action;
    
    switch (action) {
      case 'accept_and_poll':
        setPollStatus({
          status: 'created',
          poll_id: response.data?.poll_id,
          price: response.data?.accepted_price
        });
        break;
        
      case 'counter_offer':
        setCurrentOffer({
          type: 'counter',
          price: response.data?.counter_price,
          message: response.message
        });
        break;
        
      case 'reject_with_counter':
        setCurrentOffer({
          type: 'rejection',
          price: response.data?.counter_price,
          message: response.message
        });
        break;
        
      case 'provide_market_data':
        // Update market data display
        if (response.data) {
          setMarketData(prev => ({ ...prev, ...response.data }));
        }
        break;
        
      default:
        break;
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const acceptOffer = async (price) => {
    try {
      addMessage('buyer', `I accept the offer of ₹${price}/kg`);
      
      const response = await fetch(`/api/deals/advanced-bargaining/accept-offer/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          deal_group_id: dealGroup.id,
          buyer_id: buyer.id,
          accepted_price: price
        })
      });

      if (response.ok) {
        const data = await response.json();
        addMessage('agent', data.message, data);
        setCurrentOffer(null);
        
        if (data.action === 'accept_and_poll') {
          setPollStatus({
            status: 'created',
            poll_id: data.data?.poll_id,
            price: data.data?.accepted_price
          });
        }
      }
    } catch (error) {
      console.error('Error accepting offer:', error);
      addMessage('system', '❌ Failed to accept offer. Please try again.');
    }
  };

  const rejectOffer = () => {
    addMessage('buyer', 'I reject this offer. Let me make a new proposal.');
    setCurrentOffer(null);
  };

  const makeNewOffer = () => {
    setCurrentOffer({
      type: 'new',
      price: null,
      message: 'Please enter your new offer price:'
    });
  };

  return (
    <div className="advanced-bargaining-interface">
      {/* Header */}
      <div className="bargaining-header">
        <div className="header-info">
          <h2>🤖 Advanced AI Bargaining</h2>
          <div className="deal-info">
            <span className="crop-name">{dealGroup?.group_id}</span>
            <span className="buyer-name">Buyer: {buyer?.username}</span>
          </div>
        </div>
        
        <div className="status-indicator">
          <div className={`status-dot ${bargainingStatus}`}></div>
          <span className="status-text">
            {bargainingStatus === 'initializing' && 'Initializing...'}
            {bargainingStatus === 'active' && 'Active'}
            {bargainingStatus === 'error' && 'Error'}
          </span>
          <button className="close-bargaining-btn" onClick={onClose}>
            ✖️ Close
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="bargaining-content">
        {/* Left Panel - Chat Interface */}
        <div className="chat-panel">
          <div className="chat-header">
            <h3>💬 Bargaining Chat</h3>
            <div className="chat-actions">
              <button 
                className="action-btn market-btn"
                onClick={loadMarketData}
                title="Refresh Market Data"
              >
                📊 Market
              </button>
              <button 
                className="action-btn logistics-btn"
                onClick={loadLogisticsData}
                title="View Logistics"
              >
                🚚 Logistics
              </button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="chat-messages" ref={chatContainerRef}>
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.sender}`}>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-timestamp">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
                
                {/* Message Data Display */}
                {message.data && (
                  <div className="message-data">
                    {message.data.predicted_price && (
                      <div className="price-info">
                        <span className="label">ML Predicted:</span>
                        <span className="price">₹{message.data.predicted_price}/kg</span>
                      </div>
                    )}
                    {message.data.confidence_level && (
                      <div className="confidence-info">
                        <span className="label">Confidence:</span>
                        <span className="confidence">{message.data.confidence_level}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            
            {isTyping && (
              <div className="message agent typing">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="chat-input">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message or offer..."
              disabled={bargainingStatus !== 'active'}
            />
            <button 
              onClick={sendMessage}
              disabled={!inputMessage.trim() || bargainingStatus !== 'active'}
              className="send-btn"
            >
              📤 Send
            </button>
          </div>
        </div>

        {/* Right Panel - Market & Logistics */}
        <div className="info-panel">
          {/* Market Data */}
          <div className="info-section market-section">
            <h3>📊 Market Overview</h3>
            {marketData ? (
              <div className="market-data">
                <div className="data-row">
                  <span className="label">Current Price:</span>
                  <span className="value">₹{marketData.current_price_per_kg}/kg</span>
                </div>
                <div className="data-row">
                  <span className="label">ML Prediction:</span>
                  <span className="value">₹{marketData.predicted_price}/kg</span>
                </div>
                <div className="data-row">
                  <span className="label">Trend:</span>
                  <span className="value">{marketData.price_trend}</span>
                </div>
                <div className="data-row">
                  <span className="label">Data Points:</span>
                  <span className="value">{marketData.data_points}</span>
                </div>
              </div>
            ) : (
              <div className="loading">Loading market data...</div>
            )}
          </div>

          {/* Logistics Data */}
          <div className="info-section logistics-section">
            <h3>🚚 Logistics</h3>
            {logisticsData ? (
              <div className="logistics-data">
                <div className="data-row">
                  <span className="label">Hub Location:</span>
                  <span className="value">{logisticsData.hub_location}</span>
                </div>
                <div className="data-row">
                  <span className="label">Distance:</span>
                  <span className="value">{logisticsData.total_distance_km} km</span>
                </div>
                <div className="data-row">
                  <span className="label">Transport Cost:</span>
                  <span className="value">₹{logisticsData.transport_cost_per_kg}/kg</span>
                </div>
              </div>
            ) : (
              <div className="loading">Loading logistics...</div>
            )}
          </div>

          {/* Current Offer */}
          {currentOffer && (
            <div className="info-section offer-section">
              <h3>💰 Current Offer</h3>
              <div className="offer-content">
                <div className="offer-message">{currentOffer.message}</div>
                {currentOffer.price && (
                  <div className="offer-price">₹{currentOffer.price}/kg</div>
                )}
                <div className="offer-actions">
                  <button 
                    onClick={() => acceptOffer(currentOffer.price)}
                    className="accept-btn"
                  >
                    ✅ Accept
                  </button>
                  <button 
                    onClick={rejectOffer}
                    className="reject-btn"
                  >
                    ❌ Reject
                  </button>
                  <button 
                    onClick={makeNewOffer}
                    className="new-offer-btn"
                  >
                    💡 New Offer
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Poll Status */}
          {pollStatus && (
            <div className="info-section poll-section">
              <h3>🗳️ Poll Status</h3>
              <div className="poll-content">
                <div className="poll-status">
                  Status: <span className="status-badge">{pollStatus.status}</span>
                </div>
                {pollStatus.price && (
                  <div className="poll-price">Price: ₹{pollStatus.price}/kg</div>
                )}
                <div className="poll-message">
                  Farmers are voting on your offer. You'll be notified of the results.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button 
          className="quick-btn market-inquiry"
          onClick={() => setInputMessage('What is the current market price?')}
        >
          📊 Market Price
        </button>
        <button 
          className="quick-btn logistics-inquiry"
          onClick={() => setInputMessage('Tell me about the collection hub')}
        >
          🚚 Logistics
        </button>
        <button 
          className="quick-btn quality-inquiry"
          onClick={() => setInputMessage('What makes this crop special?')}
        >
          🌾 Quality Info
        </button>
        <button 
          className="quick-btn make-offer"
          onClick={() => setInputMessage('I would like to make an offer')}
        >
          💰 Make Offer
        </button>
      </div>
    </div>
  );
};

export default AIBargainingInterface;
