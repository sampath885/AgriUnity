// frontend/src/api.js

/**
 * A helper function to make authenticated API calls.
 * It automatically includes the Authorization header.
 * @param {string} url - The API endpoint to call.
 * @param {string} token - The user's authentication token.
 * @param {object} options - Optional fetch options (method, body, etc.).
 * @returns {Promise<any>} - The JSON response from the server.
 */
export const authFetch = async (url, token, options = {}) => {
    const isFormData = options && options.body instanceof FormData;
    const defaultHeaders = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        'Authorization': `Token ${token}`
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
        // Try to parse error JSON, but handle cases where it might not be JSON
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        throw new Error(Object.values(errorData).flat().join(' ') || 'An API error occurred.');
    }
    
    // Handle cases with no content in the response body
    if (response.status === 204) {
        return null;
    }

    return response.json();
};