// frontend/src/BuyerDashboard.jsx

import React, { useEffect, useState } from 'react';
import useUserStore from './store';
import { authFetch } from './api';
import './Dashboard.css';
import UnifiedChat from './components/UnifiedChat/UnifiedChat';

function BuyerDashboard() {
  const token = useUserStore((s) => s.token);
  const [groups, setGroups] = useState([]);
  const [soldDeals, setSoldDeals] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'sold', 'active'

  const loadGroups = async () => {
    try {
      setLoading(true);
      // Load different types of groups
      const [ownedGroups, availableGroups, buyerDeals] = await Promise.all([
        authFetch('http://localhost:8000/api/deals/my-groups/', token),
        authFetch('http://localhost:8000/api/deals/available-groups/', token),
        authFetch('http://localhost:8000/api/deals/buyer/deals/', token)
      ]);
      
      console.log('🔍 Frontend: Owned groups received:', ownedGroups);
      console.log('🔍 Frontend: Available groups received:', availableGroups);
      console.log('🔍 Frontend: Buyer deals received:', buyerDeals);
      
      // Combine and deduplicate groups
      const allGroups = [...(ownedGroups || []), ...(availableGroups || [])];
      const uniqueGroups = allGroups.filter((group, index, self) => 
        index === self.findIndex(g => g.id === group.id)
      );
      
      console.log('🔍 Frontend: Combined groups:', uniqueGroups);
      
      setGroups(uniqueGroups || []);
      
      // Extract sold deals from buyer deals response
      if (buyerDeals && buyerDeals.deals_by_status) {
        setSoldDeals(buyerDeals.deals_by_status.SOLD || []);
      }
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadGroups();
    }
  }, [token]);

  // If a group is selected, show the Unified Chat
  if (selectedGroupId) {
    return (
      <UnifiedChat 
        dealGroupId={selectedGroupId} 
        onClose={() => setSelectedGroupId(null)} 
      />
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h2>Buyer Dashboard - All Deal Groups</h2>
        <p>View all deal groups - your owned groups and groups available for discovery</p>
      </div>

      {/* Tab Navigation */}
      <div className="dashboard-tabs">
        <button 
          className={`tab-button ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Groups ({groups.length})
        </button>
        <button 
          className={`tab-button ${activeTab === 'sold' ? 'active' : ''}`}
          onClick={() => setActiveTab('sold')}
        >
          Sold Deals ({soldDeals.length})
        </button>
        <button 
          className={`tab-button ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          Active Deals ({groups.filter(g => g.status !== 'SOLD').length})
        </button>
      </div>

      {loading ? (
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading deal groups...</p>
        </div>
      ) : (
        <div className="dashboard-section">
          {activeTab === 'sold' ? (
            <>
              <h3>Sold Deals - Completed Transactions</h3>
              {soldDeals.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">✅</div>
                  <div className="empty-state-text">No sold deals yet</div>
                  <p>Your completed deals will appear here once location confirmation is complete.</p>
                </div>
              ) : (
                <div className="deal-groups-grid">
                  {soldDeals.map(group => (
                    <div key={group.id} className="deal-group-card sold-deal" onClick={() => setSelectedGroupId(group.id)}>
                      <div className="group-header">
                        <h3>Group #{group.group_id || group.id}</h3>
                        <span className="status-badge sold">SOLD</span>
                      </div>
                      <div className="group-details">
                        <p><strong>Crop:</strong> {group.crop_name || 'N/A'}</p>
                        <p><strong>Grade:</strong> {group.grade || 'N/A'}</p>
                        <p><strong>Total Quantity:</strong> {group.total_quantity_kg || 0} kg</p>
                        {group.buyer_info && (
                          <>
                            <p><strong>Your Offer:</strong> ₹{group.buyer_info.offer_price}/kg</p>
                            <p><strong>Total Value:</strong> ₹{group.deal_summary?.total_value || 0}</p>
                          </>
                        )}
                        {group.deal_summary && (
                          <p><strong>Location Confirmed:</strong> {group.deal_summary.location_confirmed ? '✅ Yes' : '⏳ Pending'}</p>
                        )}
                      </div>
                      <div className="group-footer">
                        <span className="deal-date">Sold on: {new Date(group.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              <h3>{activeTab === 'active' ? 'Active Deal Groups' : 'All Deal Groups'}</h3>
              {groups.filter(g => activeTab === 'active' ? g.status !== 'SOLD' : true).length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">💬</div>
                  <div className="empty-state-text">No deal groups found</div>
                  <p>No deal groups are currently available. Check back later for new opportunities!</p>
                </div>
              ) : (
                <div className="deal-groups-grid">
                  {groups.filter(g => activeTab === 'active' ? g.status !== 'SOLD' : true).map(group => {
                    console.log('🔍 Frontend: Rendering group:', group);
                    console.log('🔍 Frontend: Group fields:', Object.keys(group));
                    console.log('🔍 Frontend: Group crop_name:', group.crop_name);
                    console.log('🔍 Frontend: Group grade:', group.grade);
                    console.log('🔍 Frontend: Group region:', group.region);
                    
                    return (
                      <div key={group.id} className="deal-group-card" onClick={() => setSelectedGroupId(group.id)}>
                        <div className="group-header">
                          <h3>Group #{group.group_id || group.id}</h3>
                          <span className={`status-badge ${group.status?.toLowerCase() || 'active'}`}>
                            {group.status || 'ACTIVE'}
                          </span>
                        </div>
                        <div className="group-details">
                          <p><strong>Crop:</strong> {group.crop_name || 'N/A'}</p>
                          <p><strong>Grade:</strong> {group.grade || 'N/A'}</p>
                          <p><strong>Total Quantity:</strong> {group.total_quantity_kg || 0} kg</p>
                          <p><strong>Region:</strong> {group.region || 'N/A'}</p>
                          <p><strong>Created:</strong> {new Date(group.created_at).toLocaleDateString()}</p>
                        </div>
                        <div className="group-actions">
                          <button className="negotiate-btn">
                            💬 Start Negotiation
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default BuyerDashboard;