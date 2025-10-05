// frontend/src/App.jsx
import React from 'react';
import useUserStore from './store';
import './App.css';
import Login from './Login';
import FarmerDashboard from './FarmerDashboard';
import BuyerDashboard from './BuyerDashboard';
import Logout from './Logout';
import ChatPage from './ChatPage';
import UnifiedChat from './components/UnifiedChat/UnifiedChat';
import WorkflowDemo from './components/UnifiedChat/WorkflowDemo';
import { authFetch } from './api';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';

function App() {
    const user = useUserStore((state) => state.user);
    const token = useUserStore((state) => state.token);

    const [currentPage, setCurrentPage] = React.useState('dashboard');
    const [showNotifications, setShowNotifications] = React.useState(false);
    const [notifications, setNotifications] = React.useState([]);
    const [selectedDealGroup, setSelectedDealGroup] = React.useState(null);

    const loadNotifications = async () => {
        try {
            const data = await authFetch(`${API_BASE}/api/notifications/my/`, token);
            setNotifications(data || []);
        } catch (e) {
            console.error(e);
        }
    };

    React.useEffect(() => {
        if (user && showNotifications) {
            loadNotifications();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user, showNotifications]);

    // If a deal group is selected, show the UnifiedChat
    if (selectedDealGroup) {
        return (
            <UnifiedChat 
                dealGroupId={selectedDealGroup} 
                onClose={() => setSelectedDealGroup(null)}
            />
        );
    }

    if (user) {
        return (
            <>
                <header className="app-header">
                    <div className="welcome-user">Welcome, {user.name}! ({user.role})</div>
                    <nav>
                        <button onClick={() => setCurrentPage('dashboard')}>Dashboard</button>
                        <button onClick={() => setCurrentPage('workflow-demo')}>Workflow Demo 🔄</button>
                        <button onClick={() => setCurrentPage('chatbot')}>AgriGenie Advisor</button>
                        {/* <button onClick={() => setShowNotifications((v)=>!v)} title="Notifications">🔔</button> */}
                    </nav>
                    <Logout />
                </header>
                {showNotifications && (
                    <div style={{ position: 'fixed', right: 12, top: 60, width: 360, maxHeight: 480, overflowY: 'auto', background: '#0c0c0c', border: '1px solid #222', borderRadius: 8, padding: 12, zIndex: 20 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <h4 style={{ margin: 0 }}>Notifications</h4>
                            <button onClick={()=>setShowNotifications(false)}>Close</button>
                        </div>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                            {(notifications || []).map(n => (
                                <li key={n.id} style={{ padding: '10px 6px', borderBottom: '1px solid #222' }}>
                                    <div style={{ fontSize: 12, opacity: 0.7 }}>{new Date(n.created_at).toLocaleString()}</div>
                                    <div style={{ fontWeight: 600 }}>{n.title}</div>
                                    <div style={{ fontSize: 14 }}>{n.message}</div>
                                </li>
                            ))}
                            {(!notifications || notifications.length === 0) && (
                                <li style={{ padding: 8 }}>No notifications yet</li>
                            )}
                        </ul>
                    </div>
                )}
                <main>
                    {currentPage === 'dashboard' && user.role === 'FARMER' && <FarmerDashboard />}
                    {currentPage === 'dashboard' && user.role === 'BUYER' && <BuyerDashboard />}
                    {currentPage === 'workflow-demo' && <WorkflowDemo />}
                    {currentPage === 'chatbot' && <ChatPage />}
                </main>
            </>
        );
    } else {
        // Show the new consolidated authentication system
        return <Login />;
    }
}

// New component to list deal groups and allow selection
function DealGroupsList({ onSelectDealGroup }) {
    const [dealGroups, setDealGroups] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    const token = useUserStore((state) => state.token);
    const user = useUserStore((state) => state.user);

    React.useEffect(() => {
        console.log('DealGroupsList: Component mounted, user:', user, 'token:', token ? 'exists' : 'missing');
        fetchDealGroups();
    }, []);

    const fetchDealGroups = async () => {
        try {
            setLoading(true);
            let endpoint;
            
            // Use different endpoints based on user role
            if (user.role === 'BUYER') {
                // Buyers see groups they can discover and join (FORMED, NEGOTIATING)
                endpoint = `${API_BASE}/api/deals/available-groups/`;
            } else {
                // Farmers see groups where they have listings
                endpoint = `${API_BASE}/api/deals/my-groups/`;
            }
            
            console.log('DealGroupsList: Fetching from endpoint:', endpoint, 'for role:', user.role);
            const data = await authFetch(endpoint, token);
            console.log('DealGroupsList: API response data:', data);
            setDealGroups(data || []);
        } catch (err) {
            console.error('DealGroupsList: Failed to fetch deal groups:', err);
            if (err.status === 403) {
                setError('You do not have permission to view deal groups. Please contact support.');
            } else if (err.status === 401) {
                setError('Please log in again to view your deal groups.');
            } else {
                setError(`Failed to load deal groups: ${err.message}`);
            }
        } finally {
            setLoading(false);
        }
    };

    console.log('DealGroupsList: Rendering with state:', { loading, error, dealGroups: dealGroups.length, userRole: user?.role });

    if (loading) {
        return (
            <div className="deal-groups-container">
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Loading your deal groups...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="deal-groups-container">
                <div className="error-message">
                    <h3>⚠️ Error Loading Deal Groups</h3>
                    <p>{error}</p>
                    <button onClick={fetchDealGroups} className="retry-button">
                        🔄 Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="deal-groups-container">
            <div className="deal-groups-header">
                <h1>💬 {user.role === 'BUYER' ? 'Discover Deal Groups' : 'My Deal Groups'}</h1>
                <p>{user.role === 'BUYER' ? 'Discover and join available deal groups to start trading' : 'Select a deal group to start chatting and managing your deals'}</p>
            </div>
            
            {dealGroups.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-icon">💬</div>
                    <div className="empty-state-text">No deal groups found</div>
                    <p>{user.role === 'BUYER' ? 'No deal groups are currently available for trading. Check back later for new opportunities!' : 'You\'ll see your deal groups here once you start participating in deals.'}</p>
                    <div style={{ marginTop: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                        <h4>Debug Info:</h4>
                        <p><strong>User Role:</strong> {user?.role}</p>
                        <p><strong>User ID:</strong> {user?.id}</p>
                        <p><strong>Token:</strong> {token ? 'Present' : 'Missing'}</p>
                        <p><strong>API Endpoint:</strong> {user?.role === 'BUYER' ? '/api/deals/available-groups/ (Discovery)' : '/api/deals/my-groups/ (My Groups)'}</p>
                    </div>
                </div>
            ) : (
                <div className="deal-groups-grid">
                    {dealGroups.map(group => (
                        <div key={group.id} className="deal-group-card" onClick={() => onSelectDealGroup(group.id)}>
                            <div className="group-header">
                                <h3>Group #{group.id}</h3>
                                <span className={`status-badge ${group.status?.toLowerCase()}`}>
                                    {group.status || 'ACTIVE'}
                                </span>
                            </div>
                            <div className="group-details">
                                <p><strong>Crop:</strong> {group.crop_name || 'N/A'}</p>
                                <p><strong>Total Quantity:</strong> {group.total_quantity_kg || 0} kg</p>
                                <p><strong>Members:</strong> {group.products?.count || 0}</p>
                                <p><strong>Created:</strong> {new Date(group.created_at).toLocaleDateString()}</p>
                            </div>
                            <div className="group-actions">
                                <button className="open-chat-btn">
                                    💬 Open Chat
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default App;