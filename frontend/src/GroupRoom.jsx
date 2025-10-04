// frontend/src/GroupRoom.jsx
import React, { useEffect, useRef, useState } from 'react';
import useUserStore from './store';
import { authFetch } from './api';
import PriceExplanationCard from './PriceExplanationCard.jsx';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';
import './Dashboard.css';

function GroupRoom({ group, onClose }) {
  const token = useUserStore((s) => s.token);
  const [messages, setMessages] = useState([]);
  const [members, setMembers] = useState([]);
  const [poll, setPoll] = useState(null);
  const [logistics, setLogistics] = useState(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  // Debug component props
  console.log('🏗️ GroupRoom component rendered with:', { group, token, hasGroup: !!group, groupId: group?.id });

  const scrollToBottom = () => endRef.current?.scrollIntoView({ behavior: 'smooth' });

  const fetchAll = async () => {
    try {
      console.log('🔄 Starting fetchAll for group:', group.id);
      
      const [msgs, mems, polls, logisticsData, negotiationHistory] = await Promise.all([
        authFetch(`${API_BASE}/api/deals/groups/${group.id}/chat/`, token),
        authFetch(`${API_BASE}/api/deals/groups/${group.id}/members/`, token),
        authFetch(`${API_BASE}/api/deals/my-polls/`, token).catch(() => []),
        authFetch(`${API_BASE}/api/deals/groups/${group.id}/logistics/`, token).catch(() => null),
        authFetch(`${API_BASE}/api/deals/groups/${group.id}/negotiation-history/`, token).catch(() => null),
      ]);
      
      console.log('📡 Raw API responses:');
      console.log('Chat messages:', msgs);
      console.log('Members:', mems);
      console.log('Polls:', polls);
      console.log('Logistics:', logisticsData);
      console.log('Negotiation history:', negotiationHistory);
      
      // Fix: Extract messages from the response structure
      const chatMessages = msgs?.messages || msgs || [];
      console.log('💬 Extracted chat messages:', chatMessages);
      
      // Get negotiation messages from history
      const negotiationMessages = negotiationHistory?.timeline || [];
      console.log('🤝 Negotiation messages:', negotiationMessages);
      
      // Fix: Extract messages from the history structure
      let allHistoryMessages = [];
      if (negotiationHistory?.history) {
        // The backend returns history grouped by date, so we need to flatten it
        Object.values(negotiationHistory.history).forEach(dateGroup => {
          if (Array.isArray(dateGroup)) {
            allHistoryMessages = allHistoryMessages.concat(dateGroup);
          }
        });
      }
      console.log('📅 Flattened history messages:', allHistoryMessages);
      
      // Combine and format all messages
      const allMessages = [];
      
      // Add chat messages
      chatMessages.forEach(msg => {
        console.log('Processing chat message:', msg);
        allMessages.push({
          id: `chat_${msg.id}`,
          content: msg.content,
          sender_name: msg.sender_name || 'Unknown',
          is_ai_agent: msg.is_ai_agent || false,
          timestamp: msg.created_at,
          type: 'chat'
        });
      });
      
      // Add negotiation messages from history
      allHistoryMessages.forEach(msg => {
        console.log('Processing history message:', msg);
        if (msg.type === 'negotiation_message' || msg.type === 'poll') {
          allMessages.push({
            id: `history_${msg.id}`,
            content: msg.content,
            sender_name: msg.sender === 'AI Agent' ? 'AI Agent' : (msg.sender === 'buyer123' ? 'You' : msg.sender),
            is_ai_agent: msg.is_ai_agent || msg.sender === 'AI Agent',
            timestamp: msg.timestamp,
            type: 'negotiation'
          });
        }
      });
      
      // Sort by timestamp - handle both ISO strings and Date objects
      allMessages.sort((a, b) => {
        const timeA = typeof a.timestamp === 'string' ? new Date(a.timestamp) : a.timestamp;
        const timeB = typeof b.timestamp === 'string' ? new Date(b.timestamp) : b.timestamp;
        return timeA - timeB;
      });
      
      console.log('🎯 Final combined messages:', allMessages);
      console.log('📊 Messages count:', allMessages.length);
      
      setMessages(allMessages);
      setMembers(mems || []);
      setLogistics(logisticsData);
      const activePoll = (polls || []).find((p) => p.deal_group === group.id && p.is_active);
      setPoll(activePoll || null);
      scrollToBottom();
    } catch (e) {
      console.error('❌ Failed to fetch group room data:', e);
      console.error('Error details:', e.message, e.stack);
    }
  };

  useEffect(() => {
    if (token && group?.id) {
      fetchAll();
    }
    const t = setInterval(fetchAll, 10000);
    return () => clearInterval(t);
  }, [token, group?.id]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    try {
      // For buyers, create negotiation messages instead of group chat
      const user = useUserStore.getState().user;
      if (user?.role === 'BUYER') {
        // Create negotiation message for buyer
        await authFetch(`${API_BASE}/api/deals/negotiation-messages/`, token, {
          method: 'POST',
          body: JSON.stringify({ 
            deal_group: group.id,
            content: input.trim(),
            message_type: 'buyer_offer'
          }),
        });
      } else {
        // For farmers, use regular group chat
        await authFetch(`${API_BASE}/api/deals/groups/${group.id}/chat/`, token, {
          method: 'POST',
          body: JSON.stringify({ content: input.trim() }),
        });
      }
      setInput('');
      await fetchAll();
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const vote = async (choice) => {
    if (!poll) return;
    try {
      const res = await authFetch(`${API_BASE}/api/deals/polls/${poll.id}/vote/`, token, {
        method: 'POST',
        body: JSON.stringify({ choice }),
      });
      alert(res.message);
      await fetchAll();
    } catch (e) {
      alert(e.message);
    }
  };

  const bookShipment = async () => {
    try {
      setLoading(true);
      const response = await authFetch(`${API_BASE}/api/deals/deals/${group.id}/shipments/book/`, token, { 
        method: 'POST' 
      });
      alert('Shipment booked successfully! The hub will coordinate collection.');
      await fetchAll();
    } catch (e) {
      alert(`Failed to book shipment: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const confirmCollection = async () => {
    try {
      setLoading(true);
      const response = await authFetch(`${API_BASE}/api/deals/deals/${group.id}/collection/confirm/`, token, { 
        method: 'POST' 
      });
      alert('Collection confirmed! Your produce is ready for pickup.');
      await fetchAll();
    } catch (e) {
      alert(`Failed to confirm collection: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-section" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16 }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Group: {group.group_id}</h3>
          <button onClick={onClose}>Close</button>
        </div>
        <p>
          <strong>Crop:</strong> {group.crop_name || '—'} | <strong>Grade:</strong> {group.grade || '—'} |{' '}
          <strong>Total:</strong> {group.total_quantity_kg} kg
        </p>

        {/* Logistics Information */}
        {logistics && (
          <div className="logistics-section" style={{ 
            background: 'linear-gradient(135deg, #1a1a2e, #16213e)', 
            padding: '16px', 
            borderRadius: '8px', 
            marginBottom: '16px',
            border: '1px solid #0f3460'
          }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#4ecca3' }}>🚚 Collection Hub</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <strong style={{ color: '#4ecca3' }}>Hub:</strong> {logistics.hub_recommendation.name}
              </div>
              <div>
                <strong style={{ color: '#4ecca3' }}>Distance:</strong> ~{logistics.distances.median_km} km
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <strong style={{ color: '#4ecca3' }}>Address:</strong> {logistics.hub_recommendation.address}
              </div>
              <div style={{ gridColumn: '1 / -1', fontSize: '12px', opacity: 0.7 }}>
                Serving {logistics.distances.farmer_count} farmers • Last updated: {new Date(logistics.last_updated).toLocaleString()}
              </div>
            </div>
          </div>
        )}

        <div className="message-list" style={{ height: 320, overflowY: 'auto', background: '#111', padding: 12, borderRadius: 8 }}>
          {/* Debug info */}
          {console.log('Messages state:', messages)}
          {console.log('Messages length:', messages?.length)}
          
          {(!messages || messages.length === 0) ? (
            <div style={{ color: '#888', textAlign: 'center', padding: '20px' }}>
              No messages yet. Start the conversation!
            </div>
          ) : (
            messages.map((m) => {
              console.log('Processing message:', m);
              const senderName = m.sender_name || m.sender?.username || 'Unknown';
              const isAI = m.is_ai_agent || senderName === 'Agent' || senderName === 'AI Agent';
              
              return (
                <div key={m.id} className={`message ${isAI ? 'ai' : 'user'}`}>
                  <div className="message-bubble">
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
                      {senderName} {isAI ? '🤖' : '👤'}
                    </div>
                    <div>{m.content}</div>
                  </div>
                </div>
              );
            })
          )}
          <div ref={endRef} />
        </div>
        <div className="input-area" style={{ marginTop: 8 }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type a message"
            disabled={loading}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>

        {/* Quick Action Buttons */}
        <div className="quick-actions" style={{ marginTop: 16, padding: '16px', background: 'rgba(52, 152, 219, 0.1)', borderRadius: '8px', border: '1px solid rgba(52, 152, 219, 0.2)' }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#2c3e50' }}>🚀 Quick Actions</h4>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button 
              onClick={bookShipment} 
              disabled={loading}
              className="action-button"
              style={{ 
                background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
                color: 'white',
                border: 'none',
                padding: '12px 20px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.3s ease'
              }}
            >
              📦 Book Shipment
            </button>
            <button 
              onClick={confirmCollection} 
              disabled={loading}
              className="action-button"
              style={{ 
                background: 'linear-gradient(135deg, #3498db, #2980b9)',
                color: 'white',
                border: 'none',
                padding: '12px 20px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.3s ease'
              }}
            >
              ✅ Confirm Collection Ready
            </button>
          </div>
          <p style={{ margin: '12px 0 0 0', fontSize: '12px', opacity: 0.7, color: '#7f8c8d' }}>
            Use these buttons to quickly manage your logistics workflow
          </p>
        </div>

        {poll && (
          <div className="event poll-section" style={{ marginTop: 16 }}>
            <strong>Action Required: Vote on Deal</strong>
            <p>Buyer Offer: <strong>₹{poll.buyer_offer_price}/kg</strong></p>
            {typeof poll.agent_justification === 'object' && poll.agent_justification ? (
              <div>
                <p><strong>Agent's Advice:</strong></p>
                <PriceExplanationCard 
                  explanation_components={poll.agent_justification.explanation_components}
                  reference_prices={poll.agent_justification.reference_prices}
                  bargain_script_for_farmers={poll.agent_justification.bargain_script_for_farmers}
                />
              </div>
            ) : (
              <p><strong>Agent's Advice:</strong> {poll.agent_justification || 'AI analysis in progress...'}</p>
            )}
            <div className="poll-buttons">
              <button onClick={() => vote('ACCEPT')} className="vote-accept">Accept</button>
              <button onClick={() => vote('REJECT')} className="vote-reject">Reject</button>
            </div>
          </div>
        )}
      </div>

      <div>
        <h4>Members</h4>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {(members || []).map((m) => (
            <li key={m.id} style={{ padding: '8px 0', borderBottom: '1px solid #222' }}>
              <div style={{ fontWeight: 600 }}>{m.name || 'Farmer'}</div>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Region: {m.region || '—'}</div>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Primary Crops: {(m.primary_crops || []).join(', ')}</div>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Trust: {m.trust_score ?? '—'} | Deals: {m.successful_deals_count ?? 0}</div>
            </li>
          ))}
          {(!members || members.length === 0) && <li>No members found</li>}
        </ul>
      </div>
    </div>
  );
}

export default GroupRoom;
