// frontend/src/Logout.jsx
import React from 'react';
import useUserStore from './store';

function Logout() {
    const logout = useUserStore((state) => state.logout);
    const user = useUserStore((state) => state.user);

    return (
        <div className="logout-container">
            <span>Welcome, {user?.name}!</span>
            <button onClick={logout}>Logout</button>
        </div>
    );
}
export default Logout;