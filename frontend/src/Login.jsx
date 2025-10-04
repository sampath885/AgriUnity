// frontend/src/Login.jsx
import React, { useState } from 'react';
import useUserStore from './store';
import { authFetch } from './api';
import './Login.css';

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || '';

function Login() {
  const [step, setStep] = useState('role-select'); // role-select, farmer-auth, buyer-auth, login
  const [userRole, setUserRole] = useState('');
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    fullName: '',
    phoneNumber: '',
    pincode: '',
    businessType: '',
    gstNumber: ''
  });
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [locationData, setLocationData] = useState({
    state: '',
    district: '',
    isDetecting: false
  });

  const { setUser } = useUserStore();

  const handleRoleSelect = (role) => {
    setUserRole(role);
    setStep(role === 'FARMER' ? 'farmer-auth' : 'buyer-auth');
    setError('');
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleLoginChange = (e) => {
    const { name, value } = e.target;
    setLoginData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePincodeChange = async (e) => {
    const pincode = e.target.value;
    setFormData(prev => ({ ...prev, pincode }));
    
    // Clear previous location data when pincode changes
    if (pincode.length < 6) {
      setLocationData({ state: '', district: '', isDetecting: false });
      return;
    }
    
    // Auto-detect location when pincode is 6 digits
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      console.log(`🔍 Detecting location for pincode: ${pincode}`);
      setLocationData(prev => ({ ...prev, isDetecting: true }));
      
      try {
        const url = `${API_BASE}/api/locations/pincode/${pincode}/`;
        console.log(`🌐 Fetching from: ${url}`);
        
        const response = await fetch(url);
        console.log(`📡 Response status: ${response.status}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log(`✅ Pincode data received:`, data);
          
          setLocationData({
            state: data.state || '',
            district: data.district || '',
            isDetecting: false
          });
          setError(''); // Clear any previous errors
          
          console.log(`📍 Location set to: ${data.district}, ${data.state}`);
        } else {
          const errorData = await response.json();
          console.log(`❌ Pincode error:`, errorData);
          
          setLocationData({ state: '', district: '', isDetecting: false });
          setError(`Pincode not found: ${errorData.error || 'Please check your pincode'}`);
        }
      } catch (error) {
        console.error('🚨 Network error:', error);
        setLocationData({ state: '', district: '', isDetecting: false });
        setError('Network error: Unable to verify pincode. Please try again.');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate that we have location data
    if (!locationData.state || !locationData.district) {
      setError('Please enter a valid 6-digit pincode to auto-detect your location');
      setLoading(false);
      return;
    }

    try {
      // Prepare the data according to backend expectations
      const registrationData = {
        username: formData.username,
        password: formData.password,
        name: formData.fullName,
        role: userRole,
        phone_number: formData.phoneNumber,
        pincode: formData.pincode,
        region: `${locationData.district}, ${locationData.state}`
      };

      if (userRole === 'FARMER') {
        // Simple farmer registration - no crops needed
        registrationData.primary_crops = [];
      } else if (userRole === 'BUYER' && formData.businessType) {
        registrationData.buyer_profile = {
          business_name: formData.fullName,
          gst_number: formData.gstNumber
        };
      }

      const response = await fetch('http://localhost:8000/api/auth/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(registrationData)
      });

      if (response.ok) {
        const data = await response.json();
        if (data.token) {
          setUser(data.user, data.token);
        } else {
          setError('Registration successful! Please login.');
          setStep('login');
        }
      } else {
        const errorData = await response.json();
        console.log('🚨 Registration error details:', errorData);
        console.log('📤 Data sent:', registrationData);
        throw new Error(errorData.detail || JSON.stringify(errorData) || 'Registration failed');
      }
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/auth/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(loginData)
      });

      if (response.ok) {
        const data = await response.json();
        if (data.token) {
          setUser(data.user, data.token);
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const goBack = () => {
    if (step === 'farmer-auth' || step === 'buyer-auth') {
      setStep('role-select');
    } else if (step === 'login') {
      setStep('role-select');
    }
    setError('');
  };

  const renderRoleSelection = () => (
    <div className="role-selection">
      <div className="hero-section">
        <h1 className="main-title">Welcome to AgriUnity</h1>
        <p className="subtitle">Your AI-powered agricultural platform</p>
        <div className="platform-highlights">
          <div className="highlight-item">
            <span className="highlight-icon">🚚</span>
            <span>Smart Logistics</span>
          </div>
          <div className="highlight-item">
            <span className="highlight-icon">🤖</span>
            <span>AI-Powered</span>
          </div>
          <div className="highlight-item">
            <span className="highlight-icon">📊</span>
            <span>Market Access</span>
          </div>
        </div>
      </div>

      <div className="role-cards">
        <div className="role-card farmer-card" onClick={() => handleRoleSelect('FARMER')}>
          <div className="role-icon">👨‍🌾</div>
          <h2>I am a Farmer</h2>
          <p>Get better prices, logistics support, and market access</p>
          <div className="role-benefits">
            <span>✓ Smart Grouping</span>
            <span>✓ Hub Collection</span>
            <span>✓ Price Optimization</span>
          </div>
        </div>

        <div className="role-card buyer-card" onClick={() => handleRoleSelect('BUYER')}>
          <div className="role-icon">🏢</div>
          <h2>I am a Buyer</h2>
          <p>Access quality produce, bulk quantities, and transparent pricing</p>
          <div className="role-benefits">
            <span>✓ Quality Assurance</span>
            <span>✓ Bulk Purchasing</span>
            <span>✓ Direct Sourcing</span>
          </div>
        </div>
      </div>

      <div className="existing-user">
        <p>Already have an account? <button onClick={() => setStep('login')} className="link-button">Login here</button></p>
      </div>
    </div>
  );

  const renderFarmerAuth = () => (
    <div className="auth-form">
      <div className="auth-header">
        <button onClick={goBack} className="back-button">← Back</button>
        <h2>Farmer Registration</h2>
        <p>Join thousands of farmers getting better prices</p>
      </div>

      <form onSubmit={handleSubmit} className="registration-form">
        <div className="form-row">
          <div className="form-group">
            <label>Full Name *</label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleInputChange}
              required
              placeholder="Enter your full name"
            />
          </div>
          <div className="form-group">
            <label>Username *</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              required
              placeholder="Choose a username"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Password *</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              placeholder="Create a strong password"
            />
          </div>
          <div className="form-group">
            <label>Phone Number *</label>
            <input
              type="tel"
              name="phoneNumber"
              value={formData.phoneNumber}
              onChange={handleInputChange}
              required
              placeholder="10-digit phone number"
              pattern="[0-9]{10}"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Pincode *</label>
            <div className="pincode-input-group">
              <input
                type="text"
                name="pincode"
                value={formData.pincode}
                onChange={handlePincodeChange}
                required
                placeholder="6-digit pincode"
                pattern="[0-9]{6}"
                maxLength="6"
              />
              {locationData.isDetecting && (
                <div className="detecting-indicator">
                  <span className="spinner"></span>
                  Detecting location...
                </div>
              )}
            </div>
            <small className="help-text">Enter your 6-digit pincode to auto-detect location</small>
            {formData.pincode.length === 6 && !locationData.state && !locationData.isDetecting && (
              <small className="pincode-help">
                💡 If your pincode is not found, please contact support or use a nearby major city pincode
              </small>
            )}
          </div>
          <div className="form-group">
            {/* Empty div for grid alignment */}
          </div>
        </div>

        {/* Auto-detected location display */}
        {(locationData.state || locationData.district) && (
          <div className="location-info">
            <div className="location-badge">
              <span className="location-icon">📍</span>
              <span className="location-text">
                {locationData.district}, {locationData.state}
              </span>
              <span className="location-source">Auto-detected from pincode</span>
            </div>
          </div>
        )}

        <button type="submit" className="submit-button" disabled={loading}>
          {loading ? 'Creating Account...' : 'Create Farmer Account'}
        </button>
      </form>
    </div>
  );

  const renderBuyerAuth = () => (
    <div className="auth-form">
      <div className="auth-header">
        <button onClick={goBack} className="back-button">← Back</button>
        <h2>Buyer Registration</h2>
        <p>Access quality produce from verified farmers</p>
      </div>

      <form onSubmit={handleSubmit} className="registration-form">
        <div className="form-row">
          <div className="form-group">
            <label>Business Name *</label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleInputChange}
              required
              placeholder="Enter your business name"
            />
          </div>
          <div className="form-group">
            <label>Username *</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              required
              placeholder="Choose a username"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Password *</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              placeholder="Create a strong password"
            />
          </div>
          <div className="form-group">
            <label>Phone Number *</label>
            <input
              type="tel"
              name="phoneNumber"
              value={formData.phoneNumber}
              onChange={handleInputChange}
              required
              placeholder="10-digit phone number"
              pattern="[0-9]{10}"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Pincode *</label>
            <div className="pincode-input-group">
              <input
                type="text"
                name="pincode"
                value={formData.pincode}
                onChange={handlePincodeChange}
                required
                placeholder="6-digit pincode"
                pattern="[0-9]{6}"
                maxLength="6"
              />
              {locationData.isDetecting && (
                <div className="detecting-indicator">
                  <span className="spinner"></span>
                  Detecting location...
                </div>
              )}
            </div>
            <small className="help-text">Enter your 6-digit pincode to auto-detect location</small>
            {formData.pincode.length === 6 && !locationData.state && !locationData.isDetecting && (
              <small className="pincode-help">
                💡 If your pincode is not found, please contact support or use a nearby major city pincode
              </small>
            )}
          </div>
          <div className="form-group">
            <label>Business Type</label>
            <select 
              name="businessType" 
              value={formData.businessType} 
              onChange={handleInputChange}
              className="business-select"
            >
              <option value="">-- Select Business Type --</option>
              <option value="Wholesaler">Wholesaler</option>
              <option value="Retailer">Retailer</option>
              <option value="Processor">Processor</option>
              <option value="Exporter">Exporter</option>
              <option value="Restaurant">Restaurant</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>GST Number *</label>
            <input
              type="text"
              name="gstNumber"
              value={formData.gstNumber}
              onChange={handleInputChange}
              required
              placeholder="15-character GSTIN (e.g., 22AAAAA0000A1Z5)"
              pattern="[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}"
              maxLength="15"
            />
            <small className="help-text">Enter your 15-character GSTIN number</small>
          </div>
          <div className="form-group">
            {/* Empty div for grid alignment */}
          </div>
        </div>

        {/* Auto-detected location display */}
        {(locationData.state || locationData.district) && (
          <div className="location-info">
            <div className="location-badge">
              <span className="location-icon">📍</span>
              <span className="location-text">
                {locationData.district}, {locationData.state}
              </span>
              <span className="location-source">Auto-detected from pincode</span>
            </div>
          </div>
        )}

        <button type="submit" className="submit-button" disabled={loading}>
          {loading ? 'Creating Account...' : 'Create Buyer Account'}
        </button>
      </form>
    </div>
  );

  const renderLogin = () => (
    <div className="auth-form">
      <div className="auth-header">
        <button onClick={goBack} className="back-button">← Back</button>
        <h2>Welcome Back</h2>
        <p>Login to your AgriUnity account</p>
      </div>

      <form onSubmit={handleLogin} className="login-form">
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            name="username"
            value={loginData.username}
            onChange={handleLoginChange}
            required
            placeholder="Enter your username"
          />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            name="password"
            value={loginData.password}
            onChange={handleLoginChange}
            required
            placeholder="Enter your password"
          />
        </div>

        <button type="submit" className="submit-button" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );

  return (
    <div className="login-container">
      <div className="login-content">
        {error && <div className="error-message">{error}</div>}
        
        {step === 'role-select' && renderRoleSelection()}
        {step === 'farmer-auth' && renderFarmerAuth()}
        {step === 'buyer-auth' && renderBuyerAuth()}
        {step === 'login' && renderLogin()}
      </div>
    </div>
  );
}

export default Login;