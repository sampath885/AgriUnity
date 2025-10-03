import React, { useState, useEffect } from 'react';
import './QuickActions.css';

const QuickActions = ({ actions, onAction, isMobile = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hoveredAction, setHoveredAction] = useState(null);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    // Auto-collapse on mobile after action
    if (isMobile && isExpanded) {
      const timer = setTimeout(() => setIsExpanded(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isMobile, isExpanded]);

  const handleActionClick = async (action) => {
    try {
      await onAction(action.action);
      // Show success feedback
      setShowTooltip(true);
      setTimeout(() => setShowTooltip(false), 2000);
    } catch (error) {
      console.error('Error executing action:', error);
      // Show error feedback
    }
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const getActionIcon = (actionType) => {
    const iconMap = {
      'book_shipment': '🚚',
      'confirm_payment': '💰',
      'hub_details': '🏢',
      'track_delivery': '📦',
      'view_analytics': '📊',
      'contact_support': '💬',
      'share_deal': '📤',
      'download_receipt': '📄'
    };
    return iconMap[actionType] || '⚡';
  };

  const getActionColor = (actionType) => {
    const colorMap = {
      'book_shipment': '#3498db',
      'confirm_payment': '#27ae60',
      'hub_details': '#9b59b6',
      'track_delivery': '#e67e22',
      'view_analytics': '#1abc9c',
      'contact_support': '#e74c3c',
      'share_deal': '#f39c12',
      'download_receipt': '#95a5a6'
    };
    return colorMap[actionType] || '#667eea';
  };

  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className={`quick-actions ${isMobile ? 'mobile' : ''}`}>
      {/* Main Action Button */}
      <button 
        className={`main-action-btn ${isExpanded ? 'expanded' : ''}`}
        onClick={toggleExpanded}
        onMouseEnter={() => !isMobile && setHoveredAction('main')}
        onMouseLeave={() => !isMobile && setHoveredAction(null)}
      >
        <span className="main-icon">⚡</span>
        {isExpanded && <span className="main-text">Quick Actions</span>}
      </button>

      {/* Action Buttons */}
      <div className={`action-buttons ${isExpanded ? 'expanded' : ''}`}>
        {actions.map((action, index) => (
          <button
            key={action.id}
            className={`action-btn ${hoveredAction === action.id ? 'hovered' : ''}`}
            onClick={() => handleActionClick(action)}
            onMouseEnter={() => !isMobile && setHoveredAction(action.id)}
            onMouseLeave={() => !isMobile && setHoveredAction(null)}
            style={{
              '--delay': `${index * 0.1}s`,
              '--action-color': getActionColor(action.action)
            }}
          >
            <span className="action-icon">{action.icon}</span>
            {isExpanded && (
              <span className="action-name">{action.name}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="action-tooltip">
          <div className="tooltip-content">
            <span className="tooltip-icon">✅</span>
            <span className="tooltip-text">Action completed successfully!</span>
          </div>
        </div>
      )}

      {/* Mobile Instructions */}
      {isMobile && isExpanded && (
        <div className="mobile-instructions">
          <p>Tap an action to execute it</p>
        </div>
      )}
    </div>
  );
};

export default QuickActions;
