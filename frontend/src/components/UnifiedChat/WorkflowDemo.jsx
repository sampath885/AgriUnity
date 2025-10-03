import React, { useState } from 'react';
import './WorkflowDemo.css';

function WorkflowDemo() {
  const [currentStep, setCurrentStep] = useState(1);
  const [showDetails, setShowDetails] = useState(false);

  const steps = [
    {
      id: 1,
      title: 'Product Listing',
      description: 'Farmer manually enters crop details and quantity',
      icon: '🌾',
      status: 'completed'
    },
    {
      id: 2,
      title: 'Group Formation',
      description: 'System automatically groups farmers when 20 tons threshold is met',
      icon: '👥',
      status: 'completed'
    },
    {
      id: 3,
      title: 'AI Agent Activation',
      description: 'AI agent analyzes market and initiates negotiations',
      icon: '🤖',
      status: 'completed'
    },
    {
      id: 4,
      title: 'Buyer Offer',
      description: 'Buyer submits offer through the platform',
      icon: '💰',
      status: 'completed'
    },
    {
      id: 5,
      title: 'AI Analysis',
      description: 'AI agent analyzes offer using ML models and market data',
      icon: '📊',
      status: 'completed'
    },
    {
      id: 6,
      title: 'Poll Creation',
      description: 'AI agent creates poll for group voting',
      icon: '🗳️',
      status: 'completed'
    },
    {
      id: 7,
      title: 'Farmer Voting',
      description: 'Each farmer votes ACCEPT/REJECT on the offer',
      icon: '✅',
      status: 'active'
    },
    {
      id: 8,
      title: 'Deal Finalization',
      description: 'Deal created automatically when majority accepts',
      icon: '🤝',
      status: 'pending'
    }
  ];

  const getStepStatus = (step) => {
    if (step.status === 'completed') return '✅';
    if (step.status === 'active') return '🔄';
    if (step.status === 'pending') return '⏳';
    return '⭕';
  };

  const getStepClass = (step) => {
    if (step.status === 'completed') return 'step-completed';
    if (step.status === 'active') return 'step-active';
    if (step.status === 'pending') return 'step-pending';
    return 'step-default';
  };

  return (
    <div className="workflow-demo">
      <div className="demo-header">
        <h2>🔄 Complete Workflow Integration Demo</h2>
        <p>This demonstrates the end-to-end workflow from product listing to deal completion</p>
      </div>

      <div className="workflow-steps">
        {steps.map((step) => (
          <div 
            key={step.id} 
            className={`workflow-step ${getStepClass(step)}`}
            onClick={() => setCurrentStep(step.id)}
          >
            <div className="step-header">
              <div className="step-icon">{step.icon}</div>
              <div className="step-info">
                <h3 className="step-title">{step.title}</h3>
                <p className="step-description">{step.description}</p>
              </div>
              <div className="step-status">{getStepStatus(step)}</div>
            </div>
            
            {currentStep === step.id && (
              <div className="step-details">
                <div className="details-header">
                  <h4>Step {step.id} Details</h4>
                  <button 
                    className="toggle-details"
                    onClick={() => setShowDetails(!showDetails)}
                  >
                    {showDetails ? 'Hide' : 'Show'} Details
                  </button>
                </div>
                
                {showDetails && (
                  <div className="details-content">
                    {step.id === 1 && (
                      <div className="step-1-details">
                        <h5>Product Listing Process</h5>
                        <ul>
                          <li>Farmer selects crop type from dropdown</li>
                          <li>Enters quantity in kilograms</li>
                          <li>Selects quality grade (A, B, C)</li>
                          <li>System validates minimum requirements</li>
                          <li>Listing created with status 'AVAILABLE'</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 2 && (
                      <div className="step-2-details">
                        <h5>Automatic Group Formation</h5>
                        <ul>
                          <li>Django signal triggers on ProductListing save</li>
                          <li>System checks for similar crops, grades, and regions</li>
                          <li>Calculates total quantity across all matching listings</li>
                          <li>When 20 tons threshold is met, DealGroup is created</li>
                          <li>AI calculates optimal collection hub using pincode</li>
                          <li>All farmers notified about group formation</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 3 && (
                      <div className="step-3-details">
                        <h5>AI Agent Activation</h5>
                        <ul>
                          <li>AI agent becomes "Union Leader" for the group</li>
                          <li>Analyzes current market conditions</li>
                          <li>Monitors for buyer offers</li>
                          <li>Prepares market intelligence data</li>
                          <li>Ready to initiate negotiations</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 4 && (
                      <div className="step-4-details">
                        <h5>Buyer Offer Submission</h5>
                        <ul>
                          <li>Buyer discovers available deal group</li>
                          <li>Enters price per kg and desired quantity</li>
                          <li>Offer submitted through unified chat interface</li>
                          <li>System validates buyer credentials</li>
                          <li>Offer stored and queued for AI analysis</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 5 && (
                      <div className="step-5-details">
                        <h5>AI Agent Analysis</h5>
                        <ul>
                          <li>AI agent receives buyer offer</li>
                          <li>ML models analyze price against 7+ lakh historical records</li>
                          <li>Gradient Boosting model (R²: 0.7310) predicts optimal pricing</li>
                          <li>Market sentiment and seasonal patterns analyzed</li>
                          <li>"Glass Box" explanation generated with market data</li>
                          <li>Recommendation: ACCEPT, REJECT, or NEGOTIATE</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 6 && (
                      <div className="step-6-details">
                        <h5>Poll Creation by AI Agent</h5>
                        <ul>
                          <li>AI agent automatically creates Poll object</li>
                          <li>Sets 6-hour expiration time</li>
                          <li>Includes buyer offer price and AI justification</li>
                          <li>Creates GroupMessage with message_type 'POLL'</li>
                          <li>All farmers notified about new poll</li>
                          <li>Voting interface appears in unified chat</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 7 && (
                      <div className="step-7-details">
                        <h5>Farmer Voting Process</h5>
                        <ul>
                          <li>Each farmer sees poll with AI agent analysis</li>
                          <li>Voting buttons: ACCEPT or REJECT</li>
                          <li>Real-time vote counting and progress display</li>
                          <li>Individual farmer votes tracked</li>
                          <li>Majority decision required for deal acceptance</li>
                          <li>Voting status visible to all group members</li>
                        </ul>
                      </div>
                    )}
                    
                    {step.id === 8 && (
                      <div className="step-8-details">
                        <h5>Automatic Deal Finalization</h5>
                        <ul>
                          <li>System checks if all farmers have voted</li>
                          <li>If majority accepts, Deal object created automatically</li>
                          <li>DealGroup status updated to 'SOLD'</li>
                          <li>PaymentIntent created for escrow setup</li>
                          <li>Logistics coordination initiated</li>
                          <li>All parties notified of deal completion</li>
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="demo-summary">
        <h3>🎯 Key Workflow Features</h3>
        <div className="feature-grid">
          <div className="feature-item">
            <span className="feature-icon">🤖</span>
            <h4>AI Agent First Initiative</h4>
            <p>AI agent always initiates negotiations and creates polls</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🏗️</span>
            <h4>Automatic Group Formation</h4>
            <p>Groups form automatically when 20 tons threshold is met</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🗳️</span>
            <h4>Integrated Voting System</h4>
            <p>Voting happens within the unified chat interface</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <h4>Real-time Updates</h4>
            <p>Live status updates and progress tracking</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorkflowDemo;
