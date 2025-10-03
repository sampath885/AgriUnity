import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import './ProgressTracker.css';

const ProgressTracker = forwardRef(({ data, gamificationData, isMobile = false }, ref) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [showDetails, setShowDetails] = useState(false);

  useImperativeHandle(ref, () => ({
    expand: () => setIsExpanded(true),
    collapse: () => setIsExpanded(false),
    showDetails: () => setShowDetails(true),
    hideDetails: () => setShowDetails(false)
  }));

  const calculateLevelProgress = () => {
    if (!gamificationData) return 0;
    const currentExp = gamificationData.experience;
    const currentLevel = gamificationData.level;
    const expForNextLevel = currentLevel * 1000; // Simple progression formula
    const expInCurrentLevel = currentExp % 1000;
    return (expInCurrentLevel / 1000) * 100;
  };

  const getNextLevelExp = () => {
    if (!gamificationData) return 0;
    const currentExp = gamificationData.experience;
    const currentLevel = gamificationData.level;
    const expForNextLevel = currentLevel * 1000;
    return expForNextLevel - currentExp;
  };

  const getPerformanceColor = (value, maxValue) => {
    const percentage = (value / maxValue) * 100;
    if (percentage >= 80) return '#4ecdc4';
    if (percentage >= 60) return '#f39c12';
    if (percentage >= 40) return '#e67e22';
    return '#e74c3c';
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatTime = (hours) => {
    if (hours < 1) return '< 1 hour';
    if (hours === 1) return '1 hour';
    return `${hours} hours`;
  };

  if (!isExpanded) {
    return (
      <div className="progress-tracker-collapsed">
        <button 
          className="expand-btn"
          onClick={() => setIsExpanded(true)}
        >
          📊 View Progress
        </button>
      </div>
    );
  }

  return (
    <div className={`progress-tracker ${isMobile ? 'mobile' : ''}`}>
      <div className="progress-header">
        <h3>📊 Progress Tracker</h3>
        <div className="header-actions">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button 
            className={`tab-btn ${activeTab === 'performance' ? 'active' : ''}`}
            onClick={() => setActiveTab('performance')}
          >
            Performance
          </button>
          <button 
            className={`tab-btn ${activeTab === 'achievements' ? 'active' : ''}`}
            onClick={() => setActiveTab('achievements')}
          >
            Achievements
          </button>
          <button 
            className="close-btn"
            onClick={() => setIsExpanded(false)}
          >
            ✕
          </button>
        </div>
      </div>

      <div className="progress-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            {/* Gamification Progress */}
            <div className="gamification-section">
              <div className="level-info">
                <div className="level-badge">
                  <span className="level-number">{gamificationData?.level || 1}</span>
                  <span className="level-label">Level</span>
                </div>
                <div className="exp-info">
                  <div className="exp-bar">
                    <div 
                      className="exp-fill"
                      style={{ width: `${calculateLevelProgress()}%` }}
                    />
                  </div>
                  <div className="exp-text">
                    {gamificationData?.experience || 0} / {(gamificationData?.level || 1) * 1000} XP
                  </div>
                  <div className="next-level">
                    {getNextLevelExp()} XP to next level
                  </div>
                </div>
              </div>
              
              <div className="gamification-stats">
                <div className="stat-item">
                  <span className="stat-icon">🔥</span>
                  <span className="stat-value">{gamificationData?.streak || 0}</span>
                  <span className="stat-label">Day Streak</span>
                </div>
                <div className="stat-item">
                  <span className="stat-icon">🏆</span>
                  <span className="stat-value">{gamificationData?.badges?.length || 0}</span>
                  <span className="stat-label">Badges</span>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon">📈</div>
                <div className="metric-content">
                  <div className="metric-value">{data?.dealsCompleted || 0}</div>
                  <div className="metric-label">Deals Completed</div>
                </div>
              </div>
              
              <div className="metric-card">
                <div className="metric-icon">💰</div>
                <div className="metric-content">
                  <div className="metric-value">{formatCurrency(data?.totalEarnings || 0)}</div>
                  <div className="metric-label">Total Earnings</div>
                </div>
              </div>
              
              <div className="metric-card">
                <div className="metric-icon">⚡</div>
                <div className="metric-content">
                  <div className="metric-value">{formatTime(data?.responseTime || 0)}</div>
                  <div className="metric-label">Avg Response Time</div>
                </div>
              </div>
              
              <div className="metric-card">
                <div className="metric-icon">⭐</div>
                <div className="metric-content">
                  <div className="metric-value">{data?.satisfactionRating || 0}</div>
                  <div className="metric-label">Satisfaction Rating</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="performance-tab">
            <div className="performance-charts">
              <div className="chart-container">
                <h4>Monthly Performance</h4>
                <div className="chart-placeholder">
                  <div className="chart-bar" style={{ height: '60%', backgroundColor: getPerformanceColor(60, 100) }}></div>
                  <div className="chart-bar" style={{ height: '80%', backgroundColor: getPerformanceColor(80, 100) }}></div>
                  <div className="chart-bar" style={{ height: '45%', backgroundColor: getPerformanceColor(45, 100) }}></div>
                  <div className="chart-bar" style={{ height: '90%', backgroundColor: getPerformanceColor(90, 100) }}></div>
                  <div className="chart-bar" style={{ height: '75%', backgroundColor: getPerformanceColor(75, 100) }}></div>
                  <div className="chart-bar" style={{ height: '85%', backgroundColor: getPerformanceColor(85, 100) }}></div>
                </div>
                <div className="chart-labels">
                  <span>Jan</span>
                  <span>Feb</span>
                  <span>Mar</span>
                  <span>Apr</span>
                  <span>May</span>
                  <span>Jun</span>
                </div>
              </div>
              
              <div className="performance-metrics">
                <div className="performance-item">
                  <div className="performance-label">Success Rate</div>
                  <div className="performance-value">85%</div>
                  <div className="performance-bar">
                    <div className="performance-fill" style={{ width: '85%', backgroundColor: getPerformanceColor(85, 100) }}></div>
                  </div>
                </div>
                
                <div className="performance-item">
                  <div className="performance-label">Customer Satisfaction</div>
                  <div className="performance-value">4.2/5</div>
                  <div className="performance-bar">
                    <div className="performance-fill" style={{ width: '84%', backgroundColor: getPerformanceColor(84, 100) }}></div>
                  </div>
                </div>
                
                <div className="performance-item">
                  <div className="performance-label">Response Time</div>
                  <div className="performance-value">2.3h</div>
                  <div className="performance-bar">
                    <div className="performance-fill" style={{ width: '77%', backgroundColor: getPerformanceColor(77, 100) }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'achievements' && (
          <div className="achievements-tab">
            <div className="achievements-summary">
              <div className="achievement-stats">
                <div className="achievement-stat">
                  <span className="stat-number">{gamificationData?.badges?.length || 0}</span>
                  <span className="stat-text">Unlocked</span>
                </div>
                <div className="achievement-stat">
                  <span className="stat-number">12</span>
                  <span className="stat-text">Total Available</span>
                </div>
                <div className="achievement-stat">
                  <span className="stat-number">{Math.round(((gamificationData?.badges?.length || 0) / 12) * 100)}%</span>
                  <span className="stat-text">Completion</span>
                </div>
              </div>
            </div>
            
            <div className="achievements-list">
              <div className="achievement-category">
                <h5>Recent Achievements</h5>
                <div className="recent-achievements">
                  <div className="achievement-item unlocked">
                    <span className="achievement-icon">🎯</span>
                    <span className="achievement-name">First Deal</span>
                    <span className="achievement-date">2 days ago</span>
                  </div>
                  <div className="achievement-item unlocked">
                    <span className="achievement-icon">⚡</span>
                    <span className="achievement-name">Quick Responder</span>
                    <span className="achievement-date">1 week ago</span>
                  </div>
                </div>
              </div>
              
              <div className="achievement-category">
                <h5>Next Milestones</h5>
                <div className="upcoming-achievements">
                  <div className="achievement-item locked">
                    <span className="achievement-icon">🤝</span>
                    <span className="achievement-name">Team Player</span>
                    <span className="achievement-progress">3/5 collaborations</span>
                  </div>
                  <div className="achievement-item locked">
                    <span className="achievement-icon">💰</span>
                    <span className="achievement-name">High Earner</span>
                    <span className="achievement-progress">₹45,000/₹50,000</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="progress-footer">
        <button 
          className="details-btn"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide' : 'Show'} Detailed Analytics
        </button>
      </div>
    </div>
  );
});

ProgressTracker.displayName = 'ProgressTracker';

export default ProgressTracker;
