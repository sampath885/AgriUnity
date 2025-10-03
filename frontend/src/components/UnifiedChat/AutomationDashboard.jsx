import React, { useState, useEffect } from 'react';
import './AutomationDashboard.css';

function AutomationDashboard({ workflowEngine, aiAgent, dealGroup, onActionTaken }) {
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [aiStatus, setAiStatus] = useState(null);
  const [automationLogs, setAutomationLogs] = useState([]);
  const [showDetails, setShowDetails] = useState(false);
  const [autoProgressEnabled, setAutoProgressEnabled] = useState(true);
  const [selectedStage, setSelectedStage] = useState('all');

  useEffect(() => {
    if (workflowEngine) {
      updateWorkflowStatus();
      const interval = setInterval(updateWorkflowStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [workflowEngine]);

  useEffect(() => {
    if (aiAgent) {
      updateAIStatus();
      const interval = setInterval(updateAIStatus, 10000);
      return () => clearInterval(interval);
    }
  }, [aiAgent]);

  const updateWorkflowStatus = () => {
    if (workflowEngine) {
      const status = workflowEngine.getWorkflowStatus();
      setWorkflowStatus(status);
      setAutoProgressEnabled(status.automationEnabled);
    }
  };

  const updateAIStatus = () => {
    if (aiAgent) {
      const status = aiAgent.getAIStatus();
      setAiStatus(status);
    }
  };

  const toggleAutoProgress = () => {
    if (workflowEngine) {
      const newState = !autoProgressEnabled;
      workflowEngine.setAutoProgress(newState);
      setAutoProgressEnabled(newState);
    }
  };

  const getStageInfo = (stage) => {
    const stages = {
      'NEGOTIATING': { icon: '🤝', color: '#ff6b35', name: 'Negotiating' },
      'ACCEPTED': { icon: '✅', color: '#4caf50', name: 'Accepted' },
      'IN_TRANSIT': { icon: '🚚', color: '#2196f3', name: 'In Transit' },
      'DELIVERED': { icon: '📦', color: '#9c27b0', name: 'Delivered' },
      'COMPLETED': { icon: '🎉', color: '#4caf50', name: 'Completed' }
    };
    return stages[stage] || { icon: '❓', color: '#666', name: stage };
  };

  const getStageProgress = (stage) => {
    const stageOrder = ['NEGOTIATING', 'ACCEPTED', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED'];
    const currentIndex = stageOrder.indexOf(stage);
    return currentIndex >= 0 ? ((currentIndex + 1) / stageOrder.length * 100).toFixed(0) : 0;
  };

  const handleActionTaken = (actionId) => {
    if (onActionTaken) {
      onActionTaken(actionId);
    }
  };

  const getAutomationLogs = () => {
    // This would typically come from the workflow engine
    // For now, we'll simulate some logs
    return [
      {
        id: 1,
        timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
        type: 'STAGE_PROGRESSION',
        message: 'Automatically progressed from NEGOTIATING to ACCEPTED',
        level: 'info'
      },
      {
        id: 2,
        timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        type: 'AUTO_ACTION',
        message: 'Executed auto-action: assign_logistics_hub',
        level: 'info'
      },
      {
        id: 3,
        timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        message: 'Market analysis completed - prices stable',
        level: 'info'
      }
    ];
  };

  const filteredLogs = selectedStage === 'all' 
    ? getAutomationLogs() 
    : getAutomationLogs().filter(log => log.type.includes(selectedStage));

  return (
    <div className="automation-dashboard">
      <div className="dashboard-header">
        <h3>🤖 Automation Dashboard</h3>
        <button 
          className="toggle-details"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      {/* Workflow Status Overview */}
      <div className="workflow-overview">
        <div className="overview-header">
          <h4>📋 Workflow Status</h4>
          <div className="auto-progress-toggle">
            <label>
              <input
                type="checkbox"
                checked={autoProgressEnabled}
                onChange={toggleAutoProgress}
              />
              Auto-Progress
            </label>
          </div>
        </div>

        {workflowStatus && (
          <div className="workflow-status-grid">
            <div className="status-card current-stage">
              <div className="status-icon" style={{ backgroundColor: getStageInfo(workflowStatus.currentStage).color }}>
                {getStageInfo(workflowStatus.currentStage).icon}
              </div>
              <div className="status-details">
                <span className="status-label">Current Stage</span>
                <span className="status-value">{getStageInfo(workflowStatus.currentStage).name}</span>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${getStageProgress(workflowStatus.currentStage)}%`,
                      backgroundColor: getStageInfo(workflowStatus.currentStage).color
                    }}
                  ></div>
                </div>
              </div>
            </div>

            <div className="status-card pending-actions">
              <div className="status-icon pending">
                ⏳
              </div>
              <div className="status-details">
                <span className="status-label">Pending Actions</span>
                <span className="status-value">{workflowStatus.pendingActions.length}</span>
                <span className="status-subtitle">Require attention</span>
              </div>
            </div>

            <div className="status-card automation-status">
              <div className="status-icon automation">
                {autoProgressEnabled ? '🟢' : '🔴'}
              </div>
              <div className="status-details">
                <span className="status-label">Automation</span>
                <span className="status-value">{autoProgressEnabled ? 'Active' : 'Paused'}</span>
                <span className="status-subtitle">{autoProgressEnabled ? 'Running smoothly' : 'Manual control'}</span>
              </div>
            </div>

            <div className="status-card last-update">
              <div className="status-icon update">
                ⏰
              </div>
              <div className="status-details">
                <span className="status-label">Last Update</span>
                <span className="status-value">
                  {new Date(workflowStatus.lastUpdate).toLocaleTimeString()}
                </span>
                <span className="status-subtitle">Real-time monitoring</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AI Agent Status */}
      {aiStatus && (
        <div className="ai-status-section">
          <div className="section-header">
            <h4>🤖 AI Agent Status</h4>
            <span className="status-indicator active">Active</span>
          </div>
          
          <div className="ai-status-grid">
            <div className="ai-status-item">
              <span className="label">Personality:</span>
              <span className="value">{aiStatus.personality.role || 'General Advisor'}</span>
            </div>
            
            <div className="ai-status-item">
              <span className="label">Focus:</span>
              <span className="value">{aiStatus.personality.focus || 'General guidance'}</span>
            </div>
            
            <div className="ai-status-item">
              <span className="label">Context Items:</span>
              <span className="value">{aiStatus.conversationContext}</span>
            </div>
            
            <div className="ai-status-item">
              <span className="label">Last Activity:</span>
              <span className="value">
                {aiStatus.lastActivity ? 
                  new Date(aiStatus.lastActivity).toLocaleTimeString() : 
                  'N/A'
                }
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Pending Actions */}
      {workflowStatus && workflowStatus.pendingActions.length > 0 && (
        <div className="pending-actions-section">
          <div className="section-header">
            <h4>⏳ Pending Actions</h4>
            <span className="action-count">{workflowStatus.pendingActions.length} actions</span>
          </div>
          
          <div className="actions-list">
            {workflowStatus.pendingActions.map(action => (
              <div key={action.id} className="action-item">
                <div className="action-header">
                  <span className={`action-priority priority-${action.priority}`}>
                    {action.priority === 'high' ? '🔥' : 
                     action.priority === 'medium' ? '⚡' : '💡'}
                  </span>
                  <span className="action-type">{action.type}</span>
                  <span className="action-time">
                    {new Date(action.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                
                <div className="action-content">
                  <p>{action.message}</p>
                </div>
                
                <div className="action-actions">
                  <button 
                    className="action-btn primary"
                    onClick={() => handleActionTaken(action.id)}
                  >
                    Take Action
                  </button>
                  <button className="action-btn secondary">
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stage History */}
      {workflowStatus && workflowStatus.stageHistory.length > 0 && (
        <div className="stage-history-section">
          <div className="section-header">
            <h4>📈 Stage History</h4>
            <span className="history-count">{workflowStatus.stageHistory.length} transitions</span>
          </div>
          
          <div className="stage-timeline">
            {workflowStatus.stageHistory.map((stage, index) => (
              <div key={index} className="timeline-item">
                <div className="timeline-marker">
                  <div className="marker-icon">
                    {getStageInfo(stage.stage).icon}
                  </div>
                  <div className="timeline-line"></div>
                </div>
                
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="stage-name">{getStageInfo(stage.stage).name}</span>
                    <span className="stage-time">
                      {new Date(stage.timestamp).toLocaleString()}
                    </span>
                  </div>
                  
                  <div className="stage-reason">
                    {stage.reason}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Automation Logs */}
      {showDetails && (
        <div className="automation-logs-section">
          <div className="section-header">
            <h4>📝 Automation Logs</h4>
            <div className="log-filters">
              <select 
                value={selectedStage} 
                onChange={(e) => setSelectedStage(e.target.value)}
                className="stage-filter"
              >
                <option value="all">All Stages</option>
                <option value="NEGOTIATING">Negotiating</option>
                <option value="ACCEPTED">Accepted</option>
                <option value="IN_TRANSIT">In Transit</option>
                <option value="DELIVERED">Delivered</option>
                <option value="COMPLETED">Completed</option>
              </select>
            </div>
          </div>
          
          <div className="logs-container">
            {filteredLogs.map(log => (
              <div key={log.id} className={`log-entry log-${log.level}`}>
                <div className="log-timestamp">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </div>
                <div className="log-type">
                  {log.type}
                </div>
                <div className="log-message">
                  {log.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <div className="section-header">
          <h4>⚡ Quick Actions</h4>
        </div>
        
        <div className="quick-actions-grid">
          <button className="quick-action-btn">
            🔄 Refresh Status
          </button>
          
          <button className="quick-action-btn">
            📊 Generate Report
          </button>
          
          <button className="quick-action-btn">
            🚨 Emergency Stop
          </button>
          
          <button className="quick-action-btn">
            ⚙️ Settings
          </button>
        </div>
      </div>
    </div>
  );
}

export default AutomationDashboard;
