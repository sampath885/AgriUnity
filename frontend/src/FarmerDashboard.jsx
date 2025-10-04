// frontend/src/FarmerDashboard.jsx

import React, { useState, useEffect } from 'react';
import useUserStore from './store';
import { authFetch } from './api';
import './Dashboard.css';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';
import PriceExplanationCard from './PriceExplanationCard.jsx';
import FarmerProfilesModal from './components/FarmerProfilesModal.jsx';

// --- SUB-COMPONENT FOR ACTIVE POLLS ---
function ActivePolls() {
    const [polls, setPolls] = useState([]);
    const [error, setError] = useState(null);
    const token = useUserStore((state) => state.token);

    const fetchPolls = async () => {
        try {
            const data = await authFetch(`${API_BASE}/api/deals/my-polls/`, token);
            setPolls(data || []);
        } catch (err) {
            setError("Failed to fetch active polls. Please try refreshing.");
            console.error("Failed to fetch polls:", err);
        }
    };

    useEffect(() => {
        if (token) {
            fetchPolls();
        }
    }, [token]);

    const handleVote = async (pollId, choice) => {
        try {
            const result = await authFetch(`${API_BASE}/api/deals/polls/${pollId}/vote/`, token, {
                method: 'POST',
                body: JSON.stringify({ choice })
            });
            alert(result.message);
            fetchPolls();
        } catch (err) {
            alert(`Error casting vote: ${err.message}`);
        }
    };

    if (error) {
        return <p className="error-message">{error}</p>;
    }
    
    if (polls.length === 0) {
        return <p>You have no active polls requiring your vote at the moment.</p>;
    }

    return (
        <div>
            {polls.map(poll => {
                const isLocationPoll = poll.poll_type === 'location_confirmation' || poll.is_location_poll;
                
                if (isLocationPoll) {
                    const locationInfo = poll.collection_location || poll.deal_group_info?.collection_hub;
                    let locationDisplay = 'AI calculated optimal collection point';
                    let locationDetails = null;
                    
                    if (locationInfo) {
                        locationDisplay = `${locationInfo.city}, ${locationInfo.state}`;
                        locationDetails = locationInfo;
                    } else if (poll.agent_justification && typeof poll.agent_justification === 'object') {
                        const realLocation = poll.agent_justification.real_location_info;
                        const logisticsDetails = poll.agent_justification.logistics_details;
                        
                        if (realLocation) {
                            locationDisplay = `${realLocation.city_name}, ${realLocation.state_name}`;
                            locationDetails = {
                                city: realLocation.city_name,
                                state: realLocation.state_name,
                                address: logisticsDetails?.hub_address || 'Address not available',
                                coordinates: realLocation.coordinates,
                                distance: realLocation.total_distance_km,
                                travelTime: realLocation.travel_time_minutes,
                                transportCost: logisticsDetails?.transport_details?.transport_cost_per_kg || 2.50,
                                facilities: logisticsDetails?.hub_facilities || ['Cold storage', 'Weighing', 'Quality check']
                            };
                        } else if (logisticsDetails) {
                            locationDisplay = `${logisticsDetails.city_name}, ${logisticsDetails.state_name}`;
                            locationDetails = {
                                city: logisticsDetails.city_name,
                                state: logisticsDetails.state_name,
                                address: logisticsDetails.hub_address || 'Address not available',
                                coordinates: logisticsDetails.hub_coordinates,
                                distance: logisticsDetails.total_distance_km,
                                travelTime: logisticsDetails.travel_time_minutes,
                                transportCost: logisticsDetails?.transport_details?.transport_cost_per_kg || 2.50,
                                facilities: logisticsDetails?.hub_facilities || ['Cold storage', 'Weighing', 'Quality check']
                            };
                        }
                    }
                    
                    return (
                        <div key={poll.id} className="event poll-section location-poll">
                            <strong>📍 Action Required: Confirm Collection Hub Location for Group #{poll.deal_group_info?.group_id || poll.deal_group}</strong>
                            <p><strong>Poll Type:</strong> {poll.poll_type_display || 'Location Confirmation'}</p>
                            <p><strong>Description:</strong> {poll.poll_description || 'Please confirm if the proposed collection location works for you.'}</p>
                            <p><strong>Collection Hub:</strong> {locationDisplay}</p>
                            {locationDetails && (
                                <div className="location-details">
                                    <p><strong>Address:</strong> {locationDetails.address || 'Address not available'}</p>
                                    {locationDetails.coordinates && (
                                        <p><strong>Coordinates:</strong> {locationDetails.coordinates.latitude?.toFixed(4)}, {locationDetails.coordinates.longitude?.toFixed(4)}</p>
                                    )}
                                    <div className="transport-details">
                                        <p><strong>🚚 Transport Details:</strong></p>
                                        <ul>
                                            <li>Distance from your farm: {locationDetails.distance || 'N/A'} km</li>
                                            <li>Estimated travel time: {locationDetails.travelTime || 'N/A'} minutes</li>
                                            <li>Transport cost: ₹{locationDetails.transportCost || 'N/A'}/kg</li>
                                            <li>Hub facilities: {locationDetails.facilities?.join(', ') || 'Cold storage, weighing, quality check'}</li>
                                        </ul>
                                    </div>
                                </div>
                            )}
                            {!locationDetails && locationDisplay === 'AI calculated optimal collection point' && (
                                <div className="location-details" style={{borderColor: '#e74c3c', backgroundColor: 'rgba(231, 76, 60, 0.1)'}}>
                                    <p><strong>⚠️ Location Information:</strong> Collection hub location is being calculated by our AI system. This may take a few moments.</p>
                                    <p><strong>Status:</strong> AI logistics optimization in progress...</p>
                                </div>
                            )}
                            <div className="poll-buttons">
                                <button onClick={() => handleVote(poll.id, 'YES')} className="vote-accept">✅ Confirm Location</button>
                                <button onClick={() => handleVote(poll.id, 'NO')} className="vote-reject">❌ Reject Location</button>
                            </div>
                        </div>
                    );
                } else {
                    return (
                        <div key={poll.id} className="event poll-section price-poll">
                            <strong>🗳️ Action Required: Vote on Deal for Group #{poll.deal_group_info?.group_id || poll.deal_group}</strong>
                            <p>Buyer's Offer: <strong>₹{poll.buyer_offer_price}/kg</strong></p>
                            
                            {poll.agent_justification && typeof poll.agent_justification === 'object' && (
                                <div className="market-analysis">
                                    <h4>🤖 AI Agent's Analysis & Recommendations</h4>
                                    {poll.agent_justification.market_insights && (
                                        <div className="market-insights">
                                            <p><strong>💰 Market Analysis:</strong></p>
                                            <ul>
                                                <li>Current Market Rate: ₹{poll.agent_justification.market_insights.current_market_price || 'N/A'}/kg</li>
                                                <li>Quality Premium: ₹{poll.agent_justification.market_insights.quality_premium || 'N/A'}/kg</li>
                                                <li>Recommended Price: ₹{poll.agent_justification.market_insights.recommended_price || 'N/A'}/kg</li>
                                                <li>Buyer's Offer: ₹{poll.buyer_offer_price}/kg</li>
                                            </ul>
                                        </div>
                                    )}
                                    {poll.agent_justification.agent_analysis && (
                                        <div className="agent-recommendation">
                                            <p><strong>💡 AI Recommendation:</strong> {poll.agent_justification.agent_analysis.action || 'Analyzing...'}</p>
                                            {poll.agent_justification.agent_analysis.justification_for_farmers && (
                                                <p><strong>🤖 AI Agent's Note:</strong> {poll.agent_justification.agent_analysis.justification_for_farmers}</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                            
                            <div className="poll-buttons">
                                <button onClick={() => handleVote(poll.id, 'YES')} className="vote-accept">✅ Accept Offer</button>
                                <button onClick={() => handleVote(poll.id, 'NO')} className="vote-reject">❌ Reject Offer</button>
                            </div>
                        </div>
                    );
                }
            })}
        </div>
    );
}

// --- MAIN FARMER DASHBOARD COMPONENT ---
function FarmerDashboard() {
    const token = useUserStore((state) => state.token);
    const [tab, setTab] = useState('harvest');
    const [listings, setListings] = useState([]);
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(false);
    const [myListings, setMyListings] = useState([]);
    const [crops, setCrops] = useState([]);
    const [error, setError] = useState(null);
    const [formError, setFormError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    
    // --- MODAL STATE ---
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedGroup, setSelectedGroup] = useState(null);

    // --- FORM STATE ---
    const [selectedCrop, setSelectedCrop] = useState('');
    const [quantity, setQuantity] = useState('');
    const [selectedGrade, setSelectedGrade] = useState('');

    const fetchGroups = async () => {
        try {
            const data = await authFetch(`${API_BASE}/api/deals/my-groups/`, token);
            setGroups(data || []);
        } catch (e) {
            console.error(e);
        }
    };

    // --- MODAL FUNCTIONS ---
    const openFarmerProfilesModal = (group) => {
        setSelectedGroup(group);
        setIsModalOpen(true);
    };

    const closeFarmerProfilesModal = () => {
        setIsModalOpen(false);
        setSelectedGroup(null);
    };

    const fetchData = async () => {
        setError(null);
        try {
            const promises = [
                authFetch(`${API_BASE}/api/products/crops/`, token),
                authFetch(`${API_BASE}/api/products/my-listings/`, token)
            ];
            if (tab === 'groups') {
                await fetchGroups();
            }
            const [cropsData, listingsData] = await Promise.all(promises);
            setCrops(cropsData || []);
            setMyListings(listingsData || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (token) {
            fetchData();
        }
    }, [token, tab]);

    const handleSubmitListing = async (e) => {
        e.preventDefault();
        setFormError(null);
        const formData = new FormData();
        formData.append('crop_name', selectedCrop);
        formData.append('quantity_kg', parseInt(quantity, 10));
        formData.append('grade', selectedGrade);

        try {
            await authFetch(`${API_BASE}/api/products/list-product/`, token, {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Token ${token}`
                }
            });
            alert("Listing created successfully!");
            setSelectedCrop('');
            setQuantity('');
            setSelectedGrade('');
            fetchData();
        } catch (err) {
            setFormError(err.message);
        }
    };

    const canEdit = (listing) => ['AVAILABLE', 'GRADING'].includes(listing.status);

    const editListing = async (listing) => {
        const newQty = prompt('Enter new quantity (KG):', String(listing.quantity_kg));
        if (!newQty) return;
        try {
            await authFetch(`${API_BASE}/api/products/listings/${listing.id}/`, token, {
                method: 'PATCH',
                body: JSON.stringify({ quantity_kg: parseInt(newQty, 10) })
            });
            fetchData();
        } catch (e) {
            alert(e.message);
        }
    };

    if (isLoading) {
        return <div className="dashboard-container"><h2>Loading your dashboard...</h2></div>;
    }

    if (error) {
        return <div className="dashboard-container error-message"><h2>Error: {error}</h2></div>;
    }

    const user = useUserStore.getState().user;
    const logout = () => {
        useUserStore.getState().logout();
        window.location.href = '/login';
    };

    return (
        <div className="dashboard-container">
            {/* Modern Header */}
            <div className="dashboard-header">
                <div className="header-content">
                    <div className="welcome-section">
                        <div className="user-info">
                            <div className="user-name">Welcome, {user?.name || 'Farmer'}!</div>
                            <div className="user-role">{user?.role || 'FARMER'}</div>
                        </div>
                    </div>
                    <button className="logout-button" onClick={logout}>Logout</button>
                </div>
            </div>

            {/* Main Content */}
            <div className="dashboard-main">
                <h1 className="dashboard-title">My Farmer Dashboard</h1>
                
                {/* Navigation Tabs */}
                <div className="farmer-nav">
                    <button 
                        className={`nav-tab ${tab === 'harvest' ? 'active' : ''}`}
                        onClick={() => setTab('harvest')}
                    >
                        Harvest
                    </button>
                    <button 
                        className={`nav-tab ${tab === 'groups' ? 'active' : ''}`}
                        onClick={() => setTab('groups')}
                    >
                        Groups & Farmers
                    </button>
                </div>
                
                {tab === 'harvest' && (
                    <>
                        {/* Section to create a new listing */}
                        <div className="dashboard-section">
                            <h3 className="section-title">List New Harvest</h3>
                            <form onSubmit={handleSubmitListing} className="listing-form">
                                <select value={selectedCrop} onChange={e => setSelectedCrop(e.target.value)} required>
                                    <option value="">-- Select Crop --</option>
                                    {crops.map(crop => (
                                        <option key={crop.id} value={crop.name}>{crop.name}</option>
                                    ))}
                                </select>
                                <input
                                    type="number"
                                    value={quantity}
                                    onChange={e => setQuantity(e.target.value)}
                                    placeholder="Quantity in KG"
                                    required
                                    min="1"
                                />
                                <select value={selectedGrade} onChange={e => setSelectedGrade(e.target.value)} required>
                                    <option value="">-- Select Grade --</option>
                                    <option value="FAQ">FAQ</option>
                                    <option value="Medium">Medium</option>
                                    <option value="Large">Large</option>
                                    <option value="Local">Local</option>
                                    <option value="Non-FAQ">Non-FAQ</option>
                                    <option value="Ref grade-1">Ref grade-1</option>
                                    <option value="Ref grade-2">Ref grade-2</option>
                                </select>
                                <button type="submit">List My Produce</button>
                            </form>
                            {formError && <p className="error-message">{formError}</p>}
                        </div>

                        {/* Section for Active Polls */}
                        <div className="dashboard-section">
                            <h3 className="section-title">Active Polls & Deal Status</h3>
                            <ActivePolls />
                        </div>

                        {/* Section to view existing listings */}
                        <div className="dashboard-section">
                            <h3 className="section-title">My Harvest Listings</h3>
                            {myListings.length > 0 ? (
                                <table className="listings-table">
                                    <thead>
                                        <tr>
                                            <th>Crop</th>
                                            <th>Grade</th>
                                            <th>Quantity (KG)</th>
                                            <th>Status</th>
                                            <th>Date Listed</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {myListings.map(listing => (
                                            <tr key={listing.id}>
                                                <td>{crops.find(c => c.id === listing.crop)?.name || listing.crop_name || listing.crop}</td>
                                                <td>{listing.grade}</td>
                                                <td>{listing.quantity_kg}</td>
                                                <td>
                                                    <span className={`status-badge status-${listing.status.toLowerCase()}`}>
                                                        {listing.status}
                                                    </span>
                                                </td>
                                                <td>{new Date(listing.created_at).toLocaleDateString()}</td>
                                                <td>
                                                    {canEdit(listing) ? (
                                                        <button className="action-button edit" onClick={() => editListing(listing)}>Edit</button>
                                                    ) : (
                                                        <span style={{ opacity: 0.6 }}>Locked</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="empty-state">
                                    <div className="empty-state-icon">🌾</div>
                                    <div className="empty-state-text">You have no active listings.</div>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {tab === 'groups' && (
                    <div className="dashboard-section">
                        <h3 className="section-title">Groups & Other Farmers</h3>
                        {groups && groups.length > 0 ? (
                            <table className="listings-table">
                                <thead>
                                    <tr>
                                        <th>Group</th>
                                        <th>Crop</th>
                                        <th>Grade</th>
                                        <th>Total (KG)</th>
                                        <th>Status</th>
                                        <th>Farmers</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {groups.map(g => (
                                        <tr key={g.id}>
                                            <td>{g.group_id}</td>
                                            <td>{g.crop_name || '—'}</td>
                                            <td>{g.grade || '—'}</td>
                                            <td>{g.total_quantity_kg}</td>
                                            <td><span className={`status-badge status-${(g.status||'').toLowerCase()}`}>{g.status}</span></td>
                                            <td>
                                                <span 
                                                    className="farmer-count clickable" 
                                                    onClick={() => openFarmerProfilesModal(g)}
                                                    style={{ cursor: 'pointer' }}
                                                >
                                                    👥 {g.products?.length || 0} farmers
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="empty-state">
                                <div className="empty-state-icon">👥</div>
                                <div className="empty-state-text">You are not in any groups yet.</div>
                                <p>Groups will appear here once you join deal groups with other farmers.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
            
            {/* Farmer Profiles Modal */}
            <FarmerProfilesModal
                groupId={selectedGroup?.id}
                groupName={selectedGroup?.group_id}
                isOpen={isModalOpen}
                onClose={closeFarmerProfilesModal}
                token={token}
            />
        </div>
    );
}

export default FarmerDashboard;