import React, { useState, useEffect, useRef } from 'react';
import { authFetch } from '../../api';
import useUserStore from '../../store';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import './UnifiedChat.css';

function UnifiedChat({ dealGroupId, onClose }) {
  const token = useUserStore((state) => state.token);
  const user = useUserStore((state) => state.user);
  
  const [messages, setMessages] = useState([]);
  const [dealGroup, setDealGroup] = useState(null);
  const [members, setMembers] = useState([]);
  const [activePoll, setActivePoll] = useState(null);
  const [logistics, setLogistics] = useState(null);
  const [dealStatus, setDealStatus] = useState('NEGOTIATING');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isNegotiating, setIsNegotiating] = useState(false);
  const messagesEndRef = useRef(null);

  // Safety check - don't render if no user or token
  if (!token || !user) {
    return (
      <div className="unified-chat error">
        <div className="error-message">
          <h3>❌ Authentication Error</h3>
          <p>Please log in to access this feature.</p>
          <button className="close-button" onClick={onClose}>
            ✖️ Close
          </button>
        </div>
      </div>
    );
  }

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Fetch initial data based on user role
  useEffect(() => {
    if (!token || !dealGroupId) {
      console.log('❌ Missing token or dealGroupId:', { token: !!token, dealGroupId });
      return;
    }

    console.log('🔍 UnifiedChat useEffect triggered with:', { dealGroupId, userRole: user?.role });
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // All users can fetch deal group details
        try {
          const groupResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/`, token);
          if (groupResponse) {
            setDealGroup(groupResponse);
            setDealStatus(groupResponse.status || 'NEGOTIATING');
          }
        } catch (err) {
          console.error('Failed to fetch deal group details:', err);
          setError('Failed to load deal group details. Please try again.');
          return;
        }
        
        // For buyers, try to fetch existing negotiation messages
        if (user.role === 'BUYER') {
          try {
            // Try to fetch existing messages from the group chat
            const messagesResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/chat/`, token);
            if (messagesResponse && Array.isArray(messagesResponse)) {
              // Filter and format messages for buyer view
              const buyerMessages = messagesResponse
                .filter(msg => msg.sender && (msg.sender.role === 'BUYER' || msg.is_ai_agent))
                .map(msg => ({
                  ...msg,
                  is_buyer: msg.sender && msg.sender.role === 'BUYER',
                  is_ai_agent: msg.is_ai_agent || (msg.sender && msg.sender.username === 'AI Agent')
                }));
              
              // Only set messages if we don't already have messages (to avoid overwriting new ones)
              if (messages.length === 0) {
                setMessages(buyerMessages);
                console.log('✅ Loaded existing buyer messages from database:', buyerMessages.length);
              } else {
                console.log('⚠️ Skipping database message load - local messages already exist');
              }
            }
          } catch (err) {
            console.log('Could not fetch existing messages for buyer:', err);
            // If no messages exist, start with empty array (only if we don't have local messages)
            if (messages.length === 0) {
              setMessages([]);
            }
          }
          
          // Fetch active poll for buyers (including location confirmation)
          try {
            console.log('🔄 Fetching active poll for deal group:', dealGroupId);
            const pollResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/active-poll/`, token);
            if (pollResponse) {
              console.log('✅ Active poll fetched for buyer:', pollResponse);
              console.log('🔍 Poll type:', pollResponse.poll_type);
              console.log('🔍 Poll ID:', pollResponse.id);
              setActivePoll(pollResponse);
            } else {
              console.log('⚠️ No active poll response received');
              setActivePoll(null);
            }
          } catch (err) {
            console.log('❌ Could not fetch active poll for buyer:', err);
            console.log('❌ Error details:', err.message);
            setActivePoll(null);
          }
        }
        
        // Only farmers can access chat, members, polls, and logistics
        if (user.role === 'FARMER') {
          // Fetch messages
          try {
            const messagesResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/chat/`, token);
            if (messagesResponse) {
              // Only set messages if we don't already have messages (to avoid overwriting new ones)
              if (messages.length === 0) {
                setMessages(messagesResponse);
                console.log('✅ Loaded existing farmer messages from database:', messagesResponse.length);
              } else {
                console.log('⚠️ Skipping database message load - local messages already exist');
              }
            }
          } catch (err) {
            console.log('Could not fetch messages:', err);
            if (messages.length === 0) {
              setMessages([]);
            }
          }
          
          // Fetch members
          try {
            const membersResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/members/`, token);
            if (membersResponse) {
              setMembers(membersResponse);
            }
          } catch (err) {
            console.log('Could not fetch members:', err);
            setMembers([]);
          }
          
          // Fetch active poll
          try {
            const pollResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/active-poll/`, token);
            if (pollResponse) {
              setActivePoll(pollResponse);
            }
          } catch (err) {
            console.log('Could not fetch active poll:', err);
            setActivePoll(null);
          }
          
          // Fetch logistics
          try {
            const logisticsResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/logistics/`, token);
            if (logisticsResponse) {
              setLogistics(logisticsResponse);
            }
          } catch (err) {
            console.log('Could not fetch logistics:', err);
            setLogistics(null);
          }
        }
        
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load chat data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dealGroupId, token, user?.role]);

  // Load existing negotiation data for buyers
  const loadExistingNegotiationData = async () => {
    if (!token || user?.role !== 'BUYER' || !dealGroup) return;
    
    try {
      // Try to fetch existing offers and negotiations
      const existingData = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/negotiation-history/`, token);
      
      if (existingData && existingData.timeline && Array.isArray(existingData.timeline)) {
        // Convert existing data to message format
        const existingMessages = existingData.timeline.map(item => {
          if (item.type === 'negotiation_message') {
            if (item.sender === 'buyer123' || item.sender_role === 'BUYER') {
              return {
                id: item.id,
                content: `💰 <strong>Buyer Offer</strong>: ₹${item.content}/kg`,
                sender: { username: user.name || 'You', role: 'BUYER' },
                message_type: 'OFFER',
                created_at: item.timestamp,
                is_buyer: true
              };
            } else if (item.sender === 'AI Agent' || item.sender_role === 'AI_AGENT') {
              return {
                id: item.id,
                content: item.content,
                sender: { username: 'AI Agent', role: 'AGENT' },
                message_type: 'TEXT',
                created_at: item.timestamp,
                is_ai_agent: true
              };
            }
          } else if (item.type === 'poll') {
            return {
              id: item.id,
              content: `📊 **Poll Created**: Offer ₹${item.offer_price}/kg - Status: ${item.status}`,
              sender: { username: 'System', role: 'SYSTEM' },
              message_type: 'SYSTEM',
              created_at: item.timestamp,
              is_system: true
            };
          }
          return null;
        }).filter(Boolean);
        
        if (existingMessages.length > 0) {
          setMessages(existingMessages);
        }
      }
    } catch (err) {
      console.log('Could not fetch existing negotiation data:', err);
    }
  };

  // Load existing data when component mounts
  useEffect(() => {
    if (dealGroup && user?.role === 'BUYER') {
      loadExistingNegotiationData();
    }
  }, [dealGroup, user?.role]);

  // Handle message sending (only for farmers)
  const handleSendMessage = async (content) => {
    if (!content.trim() || !token || user?.role !== 'FARMER') return;
    
    try {
      const response = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/chat/`, token, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: content.trim(),
          message_type: 'TEXT'
        }),
      });

      if (response) {
        setMessages(prev => [...prev, response]);
      }
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  // Refresh active poll data
  const refreshActivePoll = async () => {
    if (!token || !dealGroupId) return;
    
    try {
      const pollResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/active-poll/`, token);
      if (pollResponse) {
        setActivePoll(pollResponse);
      } else {
        setActivePoll(null);
      }
    } catch (err) {
      console.log('Could not refresh active poll:', err);
      setActivePoll(null);
    }
  };

  // Handle actions (voting, logistics, payments) - for both farmers and buyers
  const handleAction = async (messageId, action, data) => {
    if (!token) return;
    
    try {
      let endpoint = '';
      let method = 'POST';
      let body = {};

      switch (action) {
                 case 'vote':
           // For poll voting, use the pollId from data
           if (data.pollId) {
             // For location confirmation polls, use the location vote endpoint
             if (data.pollType === 'location_confirmation') {
               endpoint = `http://localhost:8000/api/deals/location-polls/${data.pollId}/vote/`;
             } else {
               endpoint = `http://localhost:8000/api/deals/polls/${data.pollId}/vote/`;
             }
           } else {
             endpoint = `http://localhost:8000/api/deals/groups/${dealGroupId}/vote/`;
           }
           body = { choice: data.choice };
           break;
          
        case 'confirm_collection':
          endpoint = `http://localhost:8000/api/deals/groups/${dealGroupId}/collection/confirm/`;
          break;
          
        case 'confirm_payment':
          endpoint = `http://localhost:8000/api/deals/groups/${dealGroupId}/payment/confirm/`;
          break;
          
        case 'book_shipment':
          endpoint = `http://localhost:8000/api/deals/groups/${dealGroupId}/shipment/book/`;
          break;
          
        default:
          console.log('Unknown action:', action);
          return;
      }

      const response = await authFetch(endpoint, token, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
      });

      if (response) {
        // For voting, refresh the active poll instead of reloading the page
        if (action === 'vote') {
          await refreshActivePoll();
          // Show success message
          const actionType = data.pollType === 'location_confirmation' ? 'Location' : 'Offer';
          alert(`${actionType} ${data.choice.toLowerCase()}d successfully!`);
        } else {
          // Refresh data after other actions
          window.location.reload();
        }
      }
    } catch (err) {
      console.error('Error performing action:', err);
      alert('Error performing action. Please try again.');
    }
  };

  // Handle buyer offer submission and start negotiation with AI Agent
  const handleBuyerOffer = async (offerPrice) => {
    if (!token || user?.role !== 'BUYER') return;
    
    try {
      setIsNegotiating(true);
      
      // Add the buyer's offer message immediately
      const buyerMessage = {
        id: Date.now(),
        content: `💰 <strong>Buyer Offer</strong>: ₹${offerPrice}/kg`,
        sender: user,
        message_type: 'OFFER',
        created_at: new Date().toISOString(),
        is_buyer: true
      };
      
      setMessages(prev => [...prev, buyerMessage]);
      
      // Submit the offer to backend
      console.log(`🚀 Submitting offer ₹${offerPrice}/kg to backend...`);
      const response = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/submit-offer/`, token, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          price_per_kg: offerPrice
        }),
      });

      console.log(`📡 Backend response:`, response);

      if (response) {
        console.log(`✅ Backend response received successfully`);
        console.log(`🔍 Full response structure:`, JSON.stringify(response, null, 2));
        console.log(`🔍 Available response fields:`, Object.keys(response));
        console.log(`🔍 ai_agent_message:`, response.ai_agent_message);
        console.log(`🔍 agent_recommendation:`, response.agent_recommendation);
        console.log(`🔍 Agent recommendation type:`, typeof response.agent_recommendation);
        if (response.agent_recommendation) {
          console.log(`🔍 Agent recommendation keys:`, Object.keys(response.agent_recommendation));
          console.log(`🔍 Action:`, response.agent_recommendation.action);
          console.log(`🔍 Message to buyer:`, response.agent_recommendation.message_to_buyer);
          console.log(`🔍 Justification for farmers:`, response.agent_recommendation.justification_for_farmers);
        }
        
        // Add AI Agent's comprehensive response based on backend response
        let aiResponseContent = `🤖 **AI Agent**: `;
        
        // ✅ PRIORITY 1: Use the direct ai_agent_message from API response
        if (response.ai_agent_message) {
          // Remove the "🤖 **AI Agent**: " prefix if it's already there
          aiResponseContent = response.ai_agent_message.startsWith('🤖 **AI Agent**: ') 
            ? response.ai_agent_message 
            : response.ai_agent_message;
          console.log('✅ Using ai_agent_message from API response:', aiResponseContent);
        }
        // ✅ PRIORITY 2: Use message_to_buyer from agent_recommendation
        else if (response.agent_recommendation?.message_to_buyer) {
          aiResponseContent += response.agent_recommendation.message_to_buyer;
          console.log('✅ Using message_to_buyer from agent_recommendation:', response.agent_recommendation.message_to_buyer);
        }
        // ✅ PRIORITY 3: Use justification_for_farmers as fallback
        else if (response.agent_recommendation?.justification_for_farmers) {
          aiResponseContent += response.agent_recommendation.justification_for_farmers;
          console.log('✅ Using justification_for_farmers as fallback:', response.agent_recommendation.justification_for_farmers);
        }
        // ✅ PRIORITY 4: Use action-based intelligent response
        else if (response.agent_recommendation?.action) {
          const action = response.agent_recommendation.action;
          if (action === 'ACCEPT') {
            aiResponseContent += 'Excellent offer! Your price is very competitive and above our market analysis. I recommend accepting this offer.';
          } else if (action === 'COUNTER_OFFER') {
            aiResponseContent += `Thank you for your offer. Based on our market analysis, I recommend a counter offer of ₹${response.agent_recommendation.new_price}/kg.`;
          } else if (action === 'REJECT') {
            aiResponseContent += 'Thank you for your offer. However, based on our current market analysis, this price is below our acceptable threshold.';
          } else {
            aiResponseContent += 'Thank you for your offer. Let me analyze this with our farmers and get back to you shortly.';
          }
        } else {
          // ✅ PRIORITY 5: Ultimate fallback - use the API response directly
          console.log('⚠️ No structured response found, using API response directly');
          aiResponseContent = `🤖 **AI Agent**: ${JSON.stringify(response, null, 2)}`;
        }
        
        // Add counter offer if available
        if (response.new_price) {
          aiResponseContent += `\n\n**💰 Counter Offer**: ₹${response.new_price}/kg`;
        } else if (response.agent_recommendation?.new_price) {
          aiResponseContent += `\n\n**💰 Counter Offer**: ₹${response.agent_recommendation.new_price}/kg`;
        }
        
        // Backend handles all formatting - no need for frontend market analysis
        
        // All AI analysis formatting is handled by the backend
        
        // Backend handles all confidence and risk assessment formatting
        
        // Backend handles all performance metrics formatting
        
        const aiResponse = {
          id: Date.now() + 1,
          content: aiResponseContent,
          sender: { username: 'AI Agent', role: 'AGENT' },
          message_type: 'TEXT',
          created_at: new Date().toISOString(),
          is_ai_agent: true
        };
        
        setMessages(prev => [...prev, aiResponse]);
        
        // Show success message
        console.log('Offer submitted successfully:', response);
      }
    } catch (err) {
      console.error('❌ Error submitting offer:', err);
      console.error('❌ Error details:', {
        message: err.message,
        stack: err.stack,
        dealGroupId,
        token: token ? 'Present' : 'Missing',
        user: user ? 'Present' : 'Missing'
      });
      
      // Add error message from AI Agent
      const errorMessage = {
        id: Date.now() + 1,
        content: `🤖 **AI Agent**: Sorry, I encountered an error processing your offer. Please try again or contact support. Error: ${err.message}`,
        sender: { username: 'AI Agent', role: 'AGENT' },
        message_type: 'TEXT',
        created_at: new Date().toISOString(),
        is_ai_agent: true
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsNegotiating(false);
    }
  };

  // Handle buyer response to counter offer
  const handleCounterOfferResponse = async (response, price) => {
    if (!token || user?.role !== 'BUYER') return;
    
    try {
      setIsNegotiating(true);
      
      let responseMessage;
      if (response === 'ACCEPT') {
        responseMessage = {
          id: Date.now(),
          content: `✅ <strong>Buyer Response</strong>: I accept your counter offer of ₹${price}/kg. Let's proceed with the deal.`,
          sender: user,
          message_type: 'ACCEPTANCE',
          created_at: new Date().toISOString(),
          is_buyer: true
        };
      } else if (response === 'REJECT') {
        responseMessage = {
          id: Date.now(),
          content: `❌ <strong>Buyer Response</strong>: I cannot accept ₹${price}/kg. Please provide a better offer.`,
          sender: user,
          message_type: 'REJECTION',
          created_at: new Date().toISOString(),
          is_buyer: true
        };
      } else if (response === 'COUNTER') {
        responseMessage = {
          id: Date.now(),
          content: `💰 <strong>Buyer Counter Offer</strong>: ₹${price}/kg`,
          sender: user,
          message_type: 'COUNTER_OFFER',
          created_at: new Date().toISOString(),
          is_buyer: true
        };
      }
      
      if (responseMessage) {
        setMessages(prev => [...prev, responseMessage]);
        
        // If it's a counter offer, submit it to backend
        if (response === 'COUNTER') {
          const backendResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/submit-offer/`, token, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              price_per_kg: price
            }),
          });
          
          if (backendResponse) {
            // Add AI Agent's response
            const aiResponse = {
              id: Date.now() + 1,
              content: `🤖 **AI Agent**: ${backendResponse.agent_recommendation?.message_to_buyer || 'Thank you for your counter offer. Let me analyze this.'}`,
              sender: { username: 'AI Agent', role: 'AGENT' },
              message_type: 'TEXT',
              created_at: new Date().toISOString(),
              is_ai_agent: true
            };
            
            setMessages(prev => [...prev, aiResponse]);
            
            // If there's another counter offer, show it
            if (backendResponse.agent_recommendation?.action === 'COUNTER_OFFER' && backendResponse.agent_recommendation?.new_price) {
              const counterOffer = {
                id: Date.now() + 2,
                content: `🤖 **AI Agent Counter Offer**: ₹${backendResponse.agent_recommendation.new_price}/kg\n\n**Justification**: ${backendResponse.agent_recommendation.justification || 'Based on market analysis and farmer requirements.'}`,
                sender: { username: 'AI Agent', role: 'AGENT' },
                message_type: 'COUNTER_OFFER',
                created_at: new Date().toISOString(),
                is_ai_agent: true
              };
              
              setMessages(prev => [...prev, counterOffer]);
            }
          }
        }
      }
    } catch (err) {
      console.error('Error handling counter offer response:', err);
    } finally {
      setIsNegotiating(false);
    }
  };

  // Set up polling to refresh active poll every 10 seconds for farmers
  useEffect(() => {
    if (user?.role === 'FARMER' && dealGroupId) {
      const pollInterval = setInterval(refreshActivePoll, 10000); // Refresh every 10 seconds
      
      return () => clearInterval(pollInterval);
    }
  }, [user?.role, dealGroupId, token]);

  // Refresh messages from database (for debugging and manual refresh)
  const refreshMessagesFromDatabase = async () => {
    if (!token || !dealGroupId) return;
    
    try {
      console.log('🔄 Manually refreshing messages from database...');
      const messagesResponse = await authFetch(`http://localhost:8000/api/deals/groups/${dealGroupId}/chat/`, token);
      if (messagesResponse && Array.isArray(messagesResponse)) {
        if (user.role === 'BUYER') {
          // Filter and format messages for buyer view
          const buyerMessages = messagesResponse
            .filter(msg => msg.sender && (msg.sender.role === 'BUYER' || msg.is_ai_agent))
            .map(msg => ({
              ...msg,
              is_buyer: msg.sender && msg.sender.role === 'BUYER',
              is_ai_agent: msg.is_ai_agent || (msg.sender && msg.sender.username === 'AI Agent')
            }));
          setMessages(buyerMessages);
          console.log('✅ Refreshed buyer messages from database:', buyerMessages.length);
        } else {
          setMessages(messagesResponse);
          console.log('✅ Refreshed farmer messages from database:', messagesResponse.length);
        }
      }
    } catch (err) {
      console.error('❌ Error refreshing messages from database:', err);
    }
  };

  if (loading) {
    return (
      <div className="unified-chat loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading chat...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="unified-chat error">
        <div className="error-message">
          <h3>❌ Error</h3>
          <p>{error}</p>
          <button className="retry-button" onClick={() => window.location.reload()}>
            🔄 Try Again
          </button>
          <button className="close-button" onClick={onClose}>
            ✖️ Close
          </button>
        </div>
      </div>
    );
  }

  // For buyers, show the negotiation interface
  if (user.role === 'BUYER') {
    return (
      <div className="unified-chat buyer-interface">
        {/* Header with refresh button */}
        <ChatHeader 
          dealGroup={dealGroup} 
          currentStage={dealStatus} 
          onClose={onClose}
          onRefresh={refreshMessagesFromDatabase}
        />
        
        {/* Full-screen chat interface */}
        <div className="buyer-chat-fullscreen">
          {/* Chat Messages Area */}
          <div className="chat-messages-container">
            {messages.length === 0 ? (
              <div className="welcome-message">
                <div className="ai-avatar">🤖</div>
                <div className="message-content">
                  <p><strong>AI Agent:</strong> Hello! I'm your AI negotiation agent. I represent the farmers in this deal group and will negotiate on their behalf.</p>
                  <p>Please submit your initial offer below to start the negotiation process.</p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`message ${message.is_buyer ? 'buyer-message' : 'ai-message'}`}>
                  <div className="message-avatar">
                    {message.is_buyer ? '💰' : '🤖'}
                  </div>
                  <div className="message-content">
                    <div className="message-sender">
                      {message.is_buyer ? user.name : 'AI Agent'}
                    </div>
                    <div className="message-text" dangerouslySetInnerHTML={{ __html: message.content }} />
                    <div className="message-time">
                      {new Date(message.created_at).toLocaleTimeString()}
                    </div>
                    
                    {/* Show action buttons for AI Agent counter offers */}
                    {!message.is_buyer && message.message_type === 'COUNTER_OFFER' && (
                      <div className="counter-offer-actions">
                        <p className="action-label">How would you like to respond?</p>
                        <div className="action-buttons">
                          <button 
                            className="action-btn accept-btn"
                            onClick={() => {
                              const price = message.content.match(/₹(\d+(?:\.\d+)?)/)?.[1];
                              if (price) handleCounterOfferResponse('ACCEPT', parseFloat(price));
                            }}
                          >
                            ✅ Accept
                          </button>
                          <button 
                            className="action-btn reject-btn"
                            onClick={() => {
                              const price = message.content.match(/₹(\d+(?:\.\d+)?)/)?.[1];
                              if (price) handleCounterOfferResponse('REJECT', parseFloat(price));
                            }}
                          >
                            ❌ Reject
                          </button>
                          <button 
                            className="action-btn counter-btn"
                            onClick={() => {
                              const price = message.content.match(/₹(\d+(?:\.\d+)?)/)?.[1];
                              if (price) {
                                const newPrice = prompt('Enter your counter offer price (₹):', price);
                                if (newPrice && !isNaN(newPrice)) {
                                  handleCounterOfferResponse('COUNTER', parseFloat(newPrice));
                                }
                              }
                            }}
                          >
                            💰 Counter Offer
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {/* Invisible element for scrolling */}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Chat Input Area */}
          <div className="chat-input-container">
            <div className="input-wrapper">
              <input 
                type="number" 
                id="offerPrice" 
                placeholder="Enter your price per kg (₹)" 
                min="0" 
                step="0.01"
                className="chat-input-field"
              />
              <button 
                onClick={() => {
                  const price = document.getElementById('offerPrice').value;
                  if (price && price > 0) {
                    handleBuyerOffer(parseFloat(price));
                    // Clear input after submission
                    document.getElementById('offerPrice').value = '';
                  } else {
                    alert('Please enter a valid price');
                  }
                }}
                className="send-button"
                disabled={isNegotiating}
              >
                {isNegotiating ? '🔄' : '💰 Send Offer'}
              </button>
            </div>
            <div className="input-hint">
              Type your price and click Send Offer to negotiate with the AI Agent
            </div>
          </div>
        </div>
      </div>
    );
  }

  // For farmers, show the full group chat interface with AI Agent
  return (
    <div className="unified-chat">
      {/* Simple Header */}
      <ChatHeader 
        dealGroup={dealGroup} 
        currentStage={dealStatus} 
        onClose={onClose} 
        onRefresh={refreshMessagesFromDatabase}
      />
      
      {/* Messages - Everything happens here */}
      <MessageList 
        messages={messages}
        activePoll={activePoll}
        onAction={handleAction}
        user={user}
        dealGroup={dealGroup}
        logistics={logistics}
        members={members}
      />
      
      {/* Chat Input */}
      <ChatInput 
        onSend={handleSendMessage}
        disabled={!dealGroup}
        placeholder="Type your message..."
      />
      
      {/* Invisible element for scrolling */}
      <div ref={messagesEndRef} />
    </div>
  );
}

export default UnifiedChat;
