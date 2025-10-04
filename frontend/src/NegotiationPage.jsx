import React, { useEffect, useState } from 'react';
import useUserStore from './store';
import { authFetch } from './api';
import PriceExplanationCard from './PriceExplanationCard';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';

function NegotiationPage({ groupId, onBack }) {
  const token = useUserStore((state) => state.token);
  const [messages, setMessages] = useState([]);
  const [offerPrice, setOfferPrice] = useState('');
  const [error, setError] = useState(null);
  const [inlineExplanation, setInlineExplanation] = useState(null);

  const fetchMessages = async () => {
    try {
      const data = await authFetch(`${API_BASE}/api/deals/groups/${groupId}/messages/`, token);
      setMessages(data || []);
    } catch (err) {
      setError('Failed to load messages');
    }
  };

  useEffect(() => {
    if (token && groupId) {
      fetchMessages();
    }
  }, [token, groupId]);

  const submitOffer = async (e) => {
    e.preventDefault();
    try {
      const resp = await authFetch(`${API_BASE}/api/deals/groups/${groupId}/submit-offer/`, token, {
        method: 'POST',
        body: JSON.stringify({ price_per_kg: offerPrice })
      });
      setOfferPrice('');
      // If we got a structured explanation, show a toast/inline info
      if (resp && resp.explanation_components) {
        setInlineExplanation(resp.explanation_components);
      }
      fetchMessages();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="dashboard-container">
      <h2>Negotiation Chat - Group #{groupId}</h2>
      <button onClick={onBack} style={{ marginBottom: '10px' }}>Back</button>
      {error && <p className="error-message">{error}</p>}
      <div className="dashboard-section" style={{ maxHeight: '50vh', overflowY: 'auto' }}>
        {messages.map(m => (
          <div key={m.id} className="event">
            <strong>{m.sender_name} ({m.message_type}):</strong>
            <div>{m.content}</div>
            <div style={{ fontSize: '0.8em', color: '#666' }}>{new Date(m.created_at).toLocaleString()}</div>
          </div>
        ))}
        {messages.length === 0 && <p>No messages yet.</p>}
      </div>
      {/* Inline explanation for buyer when agent responds with structured data */}
      {inlineExplanation && inlineExplanation.length > 0 && (
        <div className="dashboard-section">
          <PriceExplanationCard explanation_components={inlineExplanation} />
        </div>
      )}
      <div className="dashboard-section">
        <form onSubmit={submitOffer} className="listing-form">
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={offerPrice}
            onChange={(e) => setOfferPrice(e.target.value)}
            placeholder="Offer price per KG"
            required
          />
          <button type="submit">Send Offer</button>
        </form>
      </div>
    </div>
  );
}

export default NegotiationPage;


