import React from 'react';

function PriceExplanationCard({ explanation_components = [], reference_prices = {}, bargain_script_for_farmers = '' }) {
  const hasRows = Array.isArray(explanation_components) && explanation_components.length > 0;
  const hasRefs = reference_prices && Object.keys(reference_prices).length > 0;
  const hasScript = bargain_script_for_farmers && bargain_script_for_farmers.length > 0;

  if (!hasRows && !hasRefs && !hasScript) {
    return null;
  }

  return (
    <div className="price-explanation-card">
      <h4 style={{ color: '#2c3e50', marginBottom: '16px', borderBottom: '2px solid #3498db', paddingBottom: '8px' }}>
        🤖 AI Agent's Analysis & Recommendations
      </h4>
      {hasRows && (
        <div className="explanation-components">
          {explanation_components.map((component, idx) => (
            <div key={idx} className="explanation-component" style={{
              background: 'rgba(52, 152, 219, 0.1)',
              border: '1px solid rgba(52, 152, 219, 0.2)',
              borderRadius: '8px',
              padding: '12px',
              margin: '8px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ fontSize: '20px' }}>{component.icon || '📊'}</span>
              <div>
                <div style={{ fontWeight: '600', color: '#2c3e50', marginBottom: '4px' }}>
                  {component.title || 'Analysis Component'}
                </div>
                <div style={{ color: '#34495e', marginBottom: '4px' }}>
                  {component.content || 'No content available'}
                </div>
                <div style={{ fontSize: '12px', color: '#7f8c8d' }}>
                  {component.details || 'No details available'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {hasRefs && (
        <div style={{ 
          marginTop: '16px', 
          background: 'rgba(46, 204, 113, 0.1)', 
          border: '1px solid rgba(46, 204, 113, 0.2)', 
          borderRadius: '8px', 
          padding: '12px' 
        }}>
          <h5 style={{ margin: '0 0 8px 0', color: '#27ae60' }}>💰 Reference Prices</h5>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
            {Object.entries(reference_prices).map(([k,v]) => (
              <div key={k} style={{ 
                background: 'rgba(255, 255, 255, 0.7)', 
                padding: '8px', 
                borderRadius: '4px',
                border: '1px solid rgba(46, 204, 113, 0.1)'
              }}>
                <strong style={{ color: '#27ae60' }}>{k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> 
                <span style={{ marginLeft: '4px' }}>{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasScript && (
        <div style={{ 
          marginTop: '16px', 
          background: 'rgba(155, 89, 182, 0.1)', 
          border: '1px solid rgba(155, 89, 182, 0.2)', 
          borderRadius: '8px', 
          padding: '12px' 
        }}>
          <h5 style={{ margin: '0 0 8px 0', color: '#8e44ad' }}>🤖 AI Agent's Note</h5>
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.7)', 
            padding: '12px', 
            borderRadius: '4px',
            border: '1px solid rgba(155, 89, 182, 0.1)',
            whiteSpace: 'pre-line',
            lineHeight: '1.5'
          }}>
            {bargain_script_for_farmers}
          </div>
        </div>
      )}
    </div>
  );
}

export default PriceExplanationCard;


