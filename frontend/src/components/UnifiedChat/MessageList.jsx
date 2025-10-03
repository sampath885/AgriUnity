import React from 'react';
import './MessageList.css';
import AIMessageRenderer from './AIMessageRenderer';

console.log('📦 AIMessageRenderer imported:', AIMessageRenderer);
console.log('📦 React imported:', React);

function MessageList({ messages, activePoll, onAction, user, dealGroup, logistics, members }) {
  if (!messages || messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <div className="empty-icon">💬</div>
          <h4>No messages yet</h4>
          <p>Start the conversation by asking a question or waiting for the AI agent to provide guidance.</p>
        </div>
      </div>
    );
  }

  const renderMessage = (message) => {
    const isUser = message.sender_name === user?.username;
    const messageTime = new Date(message.created_at).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });

    // Check if this is an AI agent message
    const isAIMessage = message.is_ai_agent || 
        message.sender_name === 'Agent' || 
        message.sender_name === 'AgriGenie' ||
        message.sender_name === 'AI Agent' ||
        message.sender_name === 'Union Leader' ||
        (message.content && (
          message.content.includes('AgriGenie') ||
          message.content.includes('AI Response') ||
          message.content.includes('🤖') ||
          message.content.includes('Namaste') ||
          message.content.includes('Hello') ||
          message.content.includes('AI agricultural advisor')
        ));
    
    console.log('🔍 Message analysis:', {
      id: message.id,
      sender: message.sender_name,
      isAI: isAIMessage,
      contentPreview: message.content?.substring(0, 100)
    });
    
    if (isAIMessage) {
      console.log('✅ Using AIMessageRenderer for message:', message.id);
      return renderAIAgentMessage(message, messageTime);
    }

    // Check if this is a poll message
    if (message.message_type === 'POLL' || message.content?.toLowerCase().includes('poll')) {
      return renderPollMessage(message, isUser, messageTime);
    }

    // Check if this is a logistics message
    if (message.message_type === 'LOGISTICS' || message.content?.toLowerCase().includes('hub')) {
      return renderLogisticsMessage(message, isUser, messageTime);
    }

    // Check if this is a payment message
    if (message.message_type === 'PAYMENT' || message.content?.toLowerCase().includes('payment')) {
      return renderPaymentMessage(message, isUser, messageTime);
    }

    // Regular text message
    return (
      <div key={message.id} className={`message ${isUser ? 'user' : ''}`}>
        <div className="message-avatar">
          {isUser ? 
            (message.sender_name?.charAt(0) || 'U') : 
            '👤'
          }
        </div>
        <div className="message-content">
          {!isUser && (
            <div className="message-sender">{message.sender_name || 'System'}</div>
          )}
          <div className="message-text">{message.content}</div>
          <div className="message-time">{messageTime}</div>
        </div>
      </div>
    );
  };

  const renderAIAgentMessage = (message, messageTime) => {
    console.log('🎯 renderAIAgentMessage called for:', message.id, message.sender_name);
    try {
      // Use the new AIMessageRenderer for all AI agent messages
      return (
        <AIMessageRenderer
          key={message.id}
          message={message}
          messageTime={messageTime}
          onAction={onAction}
          activePoll={activePoll}
        />
      );
    } catch (error) {
      console.error('❌ Error rendering AI message:', error);
      // Fallback to regular message rendering
      return (
        <div key={message.id} className="message ai-agent-fallback">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="message-sender">AgriGenie AI (Fallback)</div>
            <div className="message-text">{message.content}</div>
            <div className="message-time">{messageTime}</div>
          </div>
        </div>
      );
    }
  };

  const renderPollMessage = (message, isUser, messageTime) => {
    // Use activePoll if available, otherwise parse from message content
    let pollData = activePoll;
    
    if (!pollData && message.content) {
      try {
        pollData = JSON.parse(message.content);
      } catch {
        pollData = { 
          buyer_offer_price: 'N/A', 
          agent_justification: 'AI analysis pending',
          expires_at: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString()
        };
      }
    }

    // Check if this is a location confirmation poll
    const isLocationPoll = pollData?.poll_type === 'location_confirmation' || 
                          message.content?.toLowerCase().includes('location') ||
                          message.content?.toLowerCase().includes('collection hub') ||
                          (activePoll && activePoll.poll_type === 'location_confirmation');

    return (
      <div key={message.id} className="message poll">
        <div className="message-avatar">🗳️</div>
        <div className="message-content">
          <div className="message-sender">AI Agent (Union Leader)</div>
          <div className="message-text">
            {isLocationPoll ? (
              <>
                <div className="poll-header">📍 Location Confirmation Required</div>
                <div className="poll-question">
                  <strong>Collection Hub:</strong> {typeof pollData?.agent_justification === 'object' && pollData?.agent_justification?.real_location ? 
                    `${pollData.agent_justification.real_location.city}, ${pollData.agent_justification.real_location.state}` : 
                    (pollData?.agent_justification || 'AI calculated optimal collection point')}
                </div>
                <div className="poll-description">
                  Please confirm if the proposed collection location works for you.
                </div>
              </>
            ) : (
              <>
                <div className="poll-header">🗳️ Vote Required</div>
                <div className="poll-question">
                  <strong>Buyer Offer:</strong> ₹{pollData?.buyer_offer_price || 'N/A'}/kg
                </div>
                {pollData?.agent_justification && (
                  <div className="poll-justification">
                    <strong>AI Agent Analysis:</strong> {typeof pollData.agent_justification === 'object' ? 
                      'AI analysis completed - see details below' : 
                      pollData.agent_justification}
                  </div>
                )}
              </>
            )}
            <div className="poll-expiry">
              <strong>Expires:</strong> {new Date(pollData?.expires_at || Date.now()).toLocaleString()}
            </div>
          </div>
          
          {/* Location confirmation buttons */}
          {isLocationPoll ? (
            <div className="inline-actions">
              <button 
                className="action-btn accept"
                onClick={() => onAction(message.id, 'vote', { 
                  choice: 'YES', 
                  pollId: pollData?.id,
                  pollType: 'location_confirmation'
                })}
              >
                ✅ ACCEPT LOCATION
              </button>
              <button 
                className="action-btn reject"
                onClick={() => onAction(message.id, 'vote', { 
                  choice: 'NO', 
                  pollId: pollData?.id,
                  pollType: 'location_confirmation'
                })}
              >
                ❌ REJECT LOCATION
              </button>
            </div>
          ) : (
            /* Price offer voting buttons */
            <div className="inline-actions">
              <button 
                className="action-btn accept"
                onClick={() => onAction(message.id, 'vote', { choice: 'ACCEPT' })}
              >
                👍 Accept Offer
              </button>
              <button 
                className="action-btn reject"
                onClick={() => onAction(message.id, 'vote', { choice: 'REJECT' })}
              >
                👎 Reject Offer
              </button>
            </div>
          )}
          
          <div className="message-time">{messageTime}</div>
        </div>
      </div>
    );
  };

  const renderLogisticsMessage = (message, isUser, messageTime) => {
    return (
      <div key={message.id} className="message logistics">
        <div className="message-avatar">🚚</div>
        <div className="message-content">
          <div className="message-sender">Logistics System</div>
          <div className="message-text">
            <div className="logistics-header">🚚 Logistics Update</div>
            <div className="logistics-content">{message.content}</div>
          </div>
          
          {/* Simple inline logistics actions */}
          <div className="inline-actions">
            <button 
              className="action-btn primary"
              onClick={() => onAction(message.id, 'confirm_collection')}
            >
              ✅ Confirm Collection
            </button>
            <button 
              className="action-btn secondary"
              onClick={() => onAction(message.id, 'view_hub_details')}
            >
              🏢 View Hub Details
            </button>
          </div>
          
          <div className="message-time">{messageTime}</div>
        </div>
      </div>
    );
  };

  const renderPaymentMessage = (message, isUser, messageTime) => {
    return (
      <div key={message.id} className="message payment">
        <div className="message-avatar">💰</div>
        <div className="message-content">
          <div className="message-sender">Payment System</div>
          <div className="message-text">
            <div className="payment-header">💰 Payment Information</div>
            <div className="payment-content">{message.content}</div>
          </div>
          
          {/* Simple inline payment actions */}
          <div className="inline-actions">
            <button 
              className="action-btn primary"
              onClick={() => onAction(message.id, 'confirm_payment')}
            >
              ✅ Confirm Payment
            </button>
            <button 
              className="action-btn secondary"
              onClick={() => onAction(message.id, 'view_payment_details')}
            >
              📋 View Details
            </button>
          </div>
          
          <div className="message-time">{messageTime}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="message-list">
             {/* Show active poll prominently at the top if available */}
       {activePoll && (
         <div className="active-poll-banner">
           <div className="poll-avatar">🗳️</div>
           <div className="poll-content">
             {activePoll.poll_type === 'location_confirmation' ? (
               <>
                 <div className="poll-header">📍 LOCATION CONFIRMATION REQUIRED</div>
                 <div className="poll-question">
                   <strong>Collection Hub:</strong> {typeof activePoll.agent_justification === 'object' && activePoll.agent_justification?.real_location ? 
                     `${activePoll.agent_justification.real_location.city}, ${activePoll.agent_justification.real_location.state}` : 
                     (activePoll.agent_justification || 'AI calculated optimal collection point')}
                 </div>
                 <div className="poll-description">
                   Please confirm if the proposed collection location works for you.
                 </div>
                 <div className="poll-expiry">
                   <strong>Expires:</strong> {new Date(activePoll.expires_at || Date.now()).toLocaleString()}
                 </div>
                 
                 {/* Location confirmation buttons */}
                 <div className="poll-voting-buttons">
                   <button 
                     className="vote-btn accept"
                     onClick={() => onAction('poll', 'vote', { choice: 'YES', pollId: activePoll.id, pollType: 'location_confirmation' })}
                   >
                     ✅ ACCEPT LOCATION
                   </button>
                   <button 
                     className="vote-btn reject"
                     onClick={() => onAction('poll', 'vote', { choice: 'NO', pollId: activePoll.id, pollType: 'location_confirmation' })}
                   >
                     ❌ REJECT LOCATION
                   </button>
                 </div>
               </>
             ) : (
               <>
                 <div className="poll-header">🗳️ VOTE REQUIRED - New Buyer Offer</div>
                 <div className="poll-question">
                   <strong>Buyer Offer:</strong> ₹{activePoll.buyer_offer_price}/kg
                 </div>
                 {activePoll.agent_justification && (
                   <div className="poll-justification">
                     <strong>AI Agent Analysis:</strong> {typeof activePoll.agent_justification === 'object' ? 
                       'AI analysis completed - see details below' : 
                       activePoll.agent_justification}
                   </div>
                 )}
                 <div className="poll-expiry">
                   <strong>Expires:</strong> {new Date(activePoll.expires_at || Date.now()).toLocaleString()}
                 </div>
                 
                 {/* Poll voting buttons */}
                 <div className="poll-voting-buttons">
                   <button 
                     className="vote-btn accept"
                     onClick={() => onAction('poll', 'vote', { choice: 'ACCEPT', pollId: activePoll.id })}
                   >
                     👍 Accept Offer
                     </button>
                   <button 
                     className="vote-btn reject"
                     onClick={() => onAction('poll', 'vote', { choice: 'REJECT', pollId: activePoll.id })}
                   >
                     👎 Reject Offer
                   </button>
                 </div>
               </>
             )}
           </div>
         </div>
       )}
      
      {/* Show messages below */}
      {messages.map(renderMessage)}
    </div>
  );
}

export default MessageList;
