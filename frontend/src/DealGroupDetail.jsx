// frontend/src/DealGroupDetail.jsx
import React from 'react';
import './Dashboard.css'; // Reuse styles

function DealGroupDetail({ group }) {
    // This is a simplified view for the hackathon.
    // In a real app, this would fetch its own data and show a timeline of events.
    
    // Mock data for demonstration
    const agentMessage = "The AgriUnity Agent is currently negotiating with 3 verified buyers on your behalf. The initial market price is ₹35/kg. Our target is ₹42/kg. Please wait for an update.";

    const poll = {
        active: true,
        question: "A buyer has made a final offer of ₹40/kg. This is a 14% increase over the mandi price. The agent recommends ACCEPTING this offer due to high perishability. What is your vote?"
    };

    const handleVote = (vote) => {
        // In a real app, this would call a backend API endpoint to record the vote.
        alert(`You voted ${vote}! Thank you.`);
        // Here you would disable the poll buttons.
    };

    return (
        <div className="dashboard-section">
            <h4>Deal Status for Group: {group.group_id}</h4>
            <p><strong>Crop:</strong> {group.crop_name} | <strong>Grade:</strong> {group.grade} | <strong>Total Quantity:</strong> {group.total_quantity_kg} kg</p>
            
            <div className="deal-timeline">
                <div className="event">
                    <strong>Agent Update:</strong> {agentMessage}
                </div>
                
                {/* Poll Section - Conditionally rendered */}
                {poll.active && (
                    <div className="event poll-section">
                        <strong>Action Required: Please Vote</strong>
                        <p>{poll.question}</p>
                        <div className="poll-buttons">
                            <button onClick={() => handleVote('ACCEPT')} className="vote-accept">Accept Offer</button>
                            <button onClick={() => handleVote('REJECT')} className="vote-reject">Reject Offer</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default DealGroupDetail;