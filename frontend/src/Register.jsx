// frontend/src/Register.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Register() {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to the new Login component which handles both login and registration
    navigate('/login');
  }, [navigate]);

  return null;
}

export default Register;