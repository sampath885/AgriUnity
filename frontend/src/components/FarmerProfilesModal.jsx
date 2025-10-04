import React, { useState, useEffect } from 'react';
import { authFetch } from '../api';
import './FarmerProfilesModal.css';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';

const FarmerProfilesModal = ({ groupId, groupName, isOpen, onClose, token }) => {
    const [farmers, setFarmers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && groupId && token) {
            fetchFarmers();
        }
    }, [isOpen, groupId, token]);

    const fetchFarmers = async () => {
        if (!token) {
            setError('Authentication token not available');
            return;
        }
        
        setLoading(true);
        setError(null);
        try {
            const data = await authFetch(`${API_BASE}/api/deals/groups/${groupId}/members/`, token);
            setFarmers(data || []);
        } catch (err) {
            setError('Failed to fetch farmer profiles. Please try again.');
            console.error('Failed to fetch farmers:', err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const getTrustScoreColor = (score) => {
        if (score >= 8) return '#28a745'; // Green for high trust
        if (score >= 6) return '#ffc107'; // Yellow for medium trust
        return '#dc3545'; // Red for low trust
    };

    const getTrustScoreLabel = (score) => {
        if (score >= 8) return 'High Trust';
        if (score >= 6) return 'Medium Trust';
        return 'Low Trust';
    };

    return (
        <div className="farmer-profiles-modal-overlay" onClick={onClose}>
            <div className="farmer-profiles-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>👥 Farmers in {groupName}</h2>
                    <button className="close-button" onClick={onClose}>✖️</button>
                </div>
                
                <div className="modal-content">
                    {loading && (
                        <div className="loading-state">
                            <div className="loading-spinner"></div>
                            <p>Loading farmer profiles...</p>
                        </div>
                    )}
                    
                    {error && (
                        <div className="error-state">
                            <p className="error-message">{error}</p>
                            <button onClick={fetchFarmers} className="retry-button">Retry</button>
                        </div>
                    )}
                    
                    {!loading && !error && farmers.length === 0 && (
                        <div className="empty-state">
                            <p>No farmers found in this group.</p>
                        </div>
                    )}
                    
                    {!loading && !error && farmers.length > 0 && (
                        <div className="farmers-grid">
                            {farmers.map((farmer) => (
                                <div key={farmer.id} className="farmer-card">
                                    <div className="farmer-avatar">
                                        {farmer.name ? farmer.name.charAt(0).toUpperCase() : farmer.username.charAt(0).toUpperCase()}
                                    </div>
                                    
                                    <div className="farmer-info">
                                        <h3 className="farmer-name">
                                            {farmer.name || `${farmer.first_name} ${farmer.last_name}`.trim() || farmer.username}
                                        </h3>
                                        
                                        <div className="farmer-details">
                                            <div className="detail-item">
                                                <span className="label">Username:</span>
                                                <span className="value">@{farmer.username}</span>
                                            </div>
                                            
                                            {farmer.phone_number && (
                                                <div className="detail-item">
                                                    <span className="label">📱 Phone:</span>
                                                    <span className="value">{farmer.phone_number}</span>
                                                </div>
                                            )}
                                            
                                            <div className="detail-item">
                                                <span className="label">🏆 Trust Score:</span>
                                                <span 
                                                    className="trust-score"
                                                    style={{ color: getTrustScoreColor(farmer.trust_score) }}
                                                >
                                                    {farmer.trust_score}/10 - {getTrustScoreLabel(farmer.trust_score)}
                                                </span>
                                            </div>
                                            
                                            {farmer.region && (
                                                <div className="detail-item">
                                                    <span className="label">📍 Region:</span>
                                                    <span className="value">{farmer.region}</span>
                                                </div>
                                            )}
                                            
                                            {farmer.pincode && (
                                                <div className="detail-item">
                                                    <span className="label">📮 Pincode:</span>
                                                    <span className="value">{farmer.pincode}</span>
                                                </div>
                                            )}
                                            
                                            <div className="detail-item">
                                                <span className="label">✅ Verified:</span>
                                                <span className="value">
                                                    {farmer.is_verified ? 'Yes' : 'No'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                
                <div className="modal-footer">
                    <button onClick={onClose} className="close-modal-button">
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FarmerProfilesModal;
