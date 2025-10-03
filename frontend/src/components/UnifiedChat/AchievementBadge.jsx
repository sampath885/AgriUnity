import React, { useState, useEffect } from 'react';
import './AchievementBadge.css';

const AchievementBadge = ({ achievement, onClick, isMobile = false }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    if (achievement.unlocked && !isAnimating) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [achievement.unlocked, isAnimating]);

  const handleClick = () => {
    if (onClick) {
      onClick(achievement);
    }
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setShowTooltip(false);
  };

  const getBadgeClass = () => {
    let className = 'achievement-badge';
    
    if (achievement.unlocked) {
      className += ' unlocked';
      if (isAnimating) className += ' animating';
    } else {
      className += ' locked';
    }
    
    if (isHovered) className += ' hovered';
    if (isMobile) className += ' mobile';
    
    return className;
  };

  const getRarityClass = () => {
    // Determine rarity based on achievement properties
    if (achievement.rarity === 'legendary') return 'legendary';
    if (achievement.rarity === 'epic') return 'epic';
    if (achievement.rarity === 'rare') return 'rare';
    return 'common';
  };

  const getProgressPercentage = () => {
    if (achievement.progress && achievement.target) {
      return Math.min((achievement.progress / achievement.target) * 100, 100);
    }
    return achievement.unlocked ? 100 : 0;
  };

  return (
    <div className="achievement-badge-container">
      <div
        className={getBadgeClass()}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        data-achievement-id={achievement.id}
      >
        <div className="badge-icon">
          <span className="icon">{achievement.icon}</span>
          {achievement.unlocked && (
            <div className="unlock-effect">
              <div className="sparkle sparkle-1">✨</div>
              <div className="sparkle sparkle-2">✨</div>
              <div className="sparkle sparkle-3">✨</div>
            </div>
          )}
        </div>
        
        <div className="badge-content">
          <div className="badge-name">{achievement.name}</div>
          {achievement.unlocked && (
            <div className="badge-description">{achievement.description}</div>
          )}
          
          {/* Progress bar for locked achievements */}
          {!achievement.unlocked && achievement.progress !== undefined && (
            <div className="progress-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${getProgressPercentage()}%` }}
                />
              </div>
              <div className="progress-text">
                {achievement.progress || 0}/{achievement.target || 1}
              </div>
            </div>
          )}
        </div>

        {/* Rarity indicator */}
        {achievement.rarity && (
          <div className={`rarity-indicator ${getRarityClass()}`}>
            {achievement.rarity.charAt(0).toUpperCase()}
          </div>
        )}

        {/* Unlock date */}
        {achievement.unlocked && achievement.unlockedAt && (
          <div className="unlock-date">
            {new Date(achievement.unlockedAt).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="achievement-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-icon">{achievement.icon}</span>
            <span className="tooltip-name">{achievement.name}</span>
          </div>
          <div className="tooltip-description">{achievement.description}</div>
          
          {achievement.rarity && (
            <div className="tooltip-rarity">
              <span className={`rarity-badge ${getRarityClass()}`}>
                {achievement.rarity}
              </span>
            </div>
          )}
          
          {achievement.rewards && (
            <div className="tooltip-rewards">
              <div className="rewards-title">Rewards:</div>
              <div className="rewards-list">
                {achievement.rewards.map((reward, index) => (
                  <div key={index} className="reward-item">
                    <span className="reward-icon">{reward.icon}</span>
                    <span className="reward-text">{reward.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {achievement.unlocked && achievement.unlockedAt && (
            <div className="tooltip-date">
              Unlocked: {new Date(achievement.unlockedAt).toLocaleDateString()}
            </div>
          )}
        </div>
      )}

      {/* Achievement notification */}
      {isAnimating && (
        <div className="achievement-notification">
          <div className="notification-content">
            <div className="notification-icon">🏆</div>
            <div className="notification-text">
              <div className="notification-title">Achievement Unlocked!</div>
              <div className="notification-name">{achievement.name}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AchievementBadge;
