import React from 'react';
import './ChatHeader.css';

function ChatHeader({ dealGroup, currentStage, onClose, onRefresh }) {
  if (!dealGroup) {
    return (
      <div className="chat-header">
        <div className="header-content">
          <div className="deal-info">
            <div className="deal-title">
              <h3>Loading...</h3>
            </div>
          </div>
          <button className="close-button" onClick={onClose}>
            ✖️
          </button>
        </div>
      </div>
    );
  }

  // Simple group info
  const getSimpleInfo = () => {
    if (dealGroup.crop_name && dealGroup.region) {
      return `${dealGroup.crop_name} - ${dealGroup.region}`;
    }
    return `Deal Group #${dealGroup.id}`;
  };

  return (
    <div className="chat-header">
      <div className="header-content">
        <div className="deal-info">
          <div className="deal-title">
            <h3>{getSimpleInfo()}</h3>
            <span className="deal-status">{currentStage || 'Active'}</span>
          </div>
        </div>
        
        <div className="header-actions">
          {onRefresh && (
            <button className="refresh-button" onClick={onRefresh} title="Refresh messages from database">
              🔄
            </button>
          )}
          <button className="close-button" onClick={onClose}>
            ✖️
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatHeader;
