import React from 'react';
import './AIMessageRenderer.css';

const AIMessageRenderer = ({ message, messageTime, onAction, activePoll }) => {
  console.log('🤖 AIMessageRenderer component called with:', {
    id: message.id,
    sender: message.sender_name,
    contentLength: message.content?.length
  });
  
  // Function to parse and format AI response content into structured sections
  const parseAIResponse = (content) => {
    if (!content) return { sections: [] };

    // Split content into sections based on common patterns
    const sections = [];
    const lines = content.split('\n').filter(line => line.trim());
    
    let currentSection = null;
    
    lines.forEach(line => {
      const trimmedLine = line.trim();
      
      // Check for section headers (lines with emojis and bold text)
      if (trimmedLine.match(/^[🌾🤔🚜💡📊🗓️🍅💰🌱➡️👨‍🌾]/)) {
        if (currentSection) {
          sections.push(currentSection);
        }
        currentSection = {
          title: trimmedLine,
          points: []
        };
      } else if (trimmedLine.startsWith('•') || trimmedLine.startsWith('-') || trimmedLine.startsWith('*')) {
        // Bullet points
        if (currentSection) {
          currentSection.points.push(trimmedLine.substring(1).trim());
        }
      } else if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        // Bold text (section titles without emojis)
        if (currentSection) {
          sections.push(currentSection);
        }
        currentSection = {
          title: trimmedLine.replace(/\*\*/g, ''),
          points: []
        };
      } else if (trimmedLine.match(/^Remember,/) || trimmedLine.match(/^Note:/)) {
        // Special handling for remember/note statements
        if (currentSection) {
          currentSection.points.push(trimmedLine);
        }
      } else if (trimmedLine.match(/^\d+\./)) {
        // Numbered points - add to current section if it's a "Next Steps" type
        if (currentSection && currentSection.title.toLowerCase().includes('next steps')) {
          currentSection.points.push(trimmedLine);
        } else {
          // Create new section for numbered steps
          if (currentSection) {
            sections.push(currentSection);
          }
          currentSection = {
            title: `Step ${trimmedLine}`,
            points: []
          };
        }
      } else if (trimmedLine && currentSection) {
        // Regular text that might be a point
        if (trimmedLine.length > 20) { // Only add as point if it's substantial
          currentSection.points.push(trimmedLine);
        }
      }
    });
    
    // Add the last section
    if (currentSection) {
      sections.push(currentSection);
    }
    
    // If no sections were created, try to create them from the content
    if (sections.length === 0) {
      return createFallbackSections(content);
    }
    
    return { sections };
  };

  // Function to create fallback sections when parsing fails
  const createFallbackSections = (content) => {
    const sections = [];
    const lines = content.split('\n').filter(line => line.trim());
    
    let currentSection = null;
    
    lines.forEach(line => {
      const trimmedLine = line.trim();
      
      // Look for lines that might be section headers
      if (trimmedLine.includes('Understanding') || 
          trimmedLine.includes('Challenges') || 
          trimmedLine.includes('Recommendations') ||
          trimmedLine.includes('Next Steps') ||
          trimmedLine.includes('Regional') ||
          trimmedLine.includes('Market') ||
          trimmedLine.includes('Actionable') ||
          trimmedLine.includes('Remember')) {
        
        if (currentSection) {
          sections.push(currentSection);
        }
        currentSection = {
          title: trimmedLine,
          points: []
        };
      } else if (trimmedLine.startsWith('•') || trimmedLine.startsWith('-')) {
        // Bullet points
        if (currentSection) {
          currentSection.points.push(trimmedLine.substring(1).trim());
        }
      } else if (trimmedLine && currentSection && trimmedLine.length > 15) {
        // Add substantial lines as points
        currentSection.points.push(trimmedLine);
      }
    });
    
    // Add the last section
    if (currentSection) {
      sections.push(currentSection);
    }
    
    return { sections };
  };

  // Function to extract the main greeting/intro
  const extractGreeting = (content) => {
    if (!content) return '';
    
    const lines = content.split('\n');
    const firstLine = lines[0]?.trim();
    
    // Look for greeting patterns
    if (firstLine && (
      firstLine.includes('Namaste') || 
      firstLine.includes('Hello') || 
      firstLine.includes('Hi') ||
      firstLine.includes('AgriGenie') ||
      firstLine.includes('🤖') ||
      firstLine.includes('AI Response')
    )) {
      // Clean up the greeting by removing the "**AgriGenie AI Response**" prefix
      let cleanGreeting = firstLine;
      if (firstLine.includes('**AgriGenie AI Response**')) {
        cleanGreeting = firstLine.replace(/\*\*AgriGenie AI Response.*?\*\*:\s*/, '');
        // Also clean up any remaining markdown formatting
        cleanGreeting = cleanGreeting.replace(/\*\*/g, '');
      }
      return cleanGreeting;
    }
    
    // Look for the first substantial line that might be a greeting
    for (let i = 0; i < Math.min(3, lines.length); i++) {
      const line = lines[i]?.trim();
      if (line && line.length > 10 && line.length < 100) {
        if (line.includes('Namaste') || line.includes('Hello') || line.includes('Hi')) {
          return line;
        }
      }
    }
    
    return '';
  };

  const { sections } = parseAIResponse(message.content);
  const greeting = extractGreeting(message.content);
  
  console.log('📊 Parsing results:', {
    sectionsCount: sections.length,
    greeting: greeting,
    sections: sections
  });

  return (
    <div className="message ai-agent">
      <div className="message-avatar">🤖</div>
      <div className="message-content">
        <div className="message-sender">AgriGenie AI</div>
        
        {/* Greeting Section */}
        {greeting && (
          <div className="ai-greeting">
            {greeting}
          </div>
        )}
        
        {/* Structured Content Sections */}
        {sections.length > 0 ? (
          <div className="ai-structured-content">
            {sections.map((section, index) => (
              <div key={index} className="ai-section">
                <div className="section-title">
                  {section.title}
                </div>
                {section.points.length > 0 && (
                  <ul className="section-points">
                    {section.points.map((point, pointIndex) => (
                      <li key={pointIndex} className="section-point">
                        {point}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        ) : (
          // Fallback: if no structured content found, show as regular text
          <div className="message-text fallback">
            {message.content}
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="inline-actions">
          {activePoll && activePoll.poll_type === 'location_confirmation' ? (
            <>
              <button 
                className="action-btn accept"
                onClick={() => onAction(message.id, 'vote', { 
                  choice: 'YES', 
                  pollId: activePoll.id,
                  pollType: 'location_confirmation'
                })}
              >
                ✅ ACCEPT LOCATION
              </button>
              <button 
                className="action-btn reject"
                onClick={() => onAction(message.id, 'vote', { 
                  choice: 'NO', 
                  pollId: activePoll.id,
                  pollType: 'location_confirmation'
                })}
              >
                ❌ REJECT LOCATION
              </button>
            </>
          ) : (
            <>
              <button 
                className="action-btn primary"
                onClick={() => onAction(message.id, 'vote', { choice: 'ACCEPT' })}
              >
                👍 Accept Offer
              </button>
              <button 
                className="action-btn secondary"
                onClick={() => onAction(message.id, 'ai_help')}
              >
                🤖 Get Help
              </button>
            </>
          )}
        </div>
        
        <div className="message-time">{messageTime}</div>
      </div>
    </div>
  );
};

export default AIMessageRenderer;
