import React, { useState, useEffect, useRef } from 'react';
import './SearchAndFilter.css';

const SearchAndFilter = ({ searchQuery, onSearch, filterOptions, onFilterChange, isMobile = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery);
  const [localFilterOptions, setLocalFilterOptions] = useState(filterOptions);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [recentSearches, setRecentSearches] = useState([]);
  
  const searchInputRef = useRef(null);
  const filterPanelRef = useRef(null);

  useEffect(() => {
    setLocalSearchQuery(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    setLocalFilterOptions(filterOptions);
  }, [filterOptions]);

  useEffect(() => {
    // Load search history from localStorage
    const savedHistory = localStorage.getItem('agriunity_search_history');
    if (savedHistory) {
      try {
        const history = JSON.parse(savedHistory);
        setSearchHistory(history);
        setRecentSearches(history.slice(0, 5));
      } catch (error) {
        console.error('Error loading search history:', error);
      }
    }
  }, []);

  const saveSearchHistory = (query) => {
    if (!query.trim()) return;
    
    const newHistory = [query, ...searchHistory.filter(item => item !== query)].slice(0, 10);
    setSearchHistory(newHistory);
    setRecentSearches(newHistory.slice(0, 5));
    
    try {
      localStorage.setItem('agriunity_search_history', JSON.stringify(newHistory));
    } catch (error) {
      console.error('Error saving search history:', error);
    }
  };

  const handleSearch = (query) => {
    const trimmedQuery = query.trim();
    if (trimmedQuery) {
      saveSearchHistory(trimmedQuery);
      onSearch(trimmedQuery);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    handleSearch(localSearchQuery);
  };

  const handleFilterChange = (filterType, value) => {
    const newFilters = { ...localFilterOptions, [filterType]: value };
    setLocalFilterOptions(newFilters);
    onFilterChange(filterType, value);
  };

  const handleClearSearch = () => {
    setLocalSearchQuery('');
    onSearch('');
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      messageType: 'all',
      dateRange: 'all',
      sender: 'all'
    };
    setLocalFilterOptions(clearedFilters);
    Object.entries(clearedFilters).forEach(([key, value]) => {
      onFilterChange(key, value);
    });
  };

  const handleRecentSearchClick = (query) => {
    setLocalSearchQuery(query);
    handleSearch(query);
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  };

  const toggleAdvancedFilters = () => {
    setShowAdvancedFilters(!showAdvancedFilters);
  };

  const getFilterIcon = (filterType) => {
    const iconMap = {
      messageType: '💬',
      dateRange: '📅',
      sender: '👤'
    };
    return iconMap[filterType] || '🔍';
  };

  const getDateRangeLabel = (range) => {
    const rangeMap = {
      'all': 'All Time',
      'today': 'Today',
      'week': 'This Week',
      'month': 'This Month',
      'quarter': 'This Quarter',
      'year': 'This Year'
    };
    return rangeMap[range] || range;
  };

  const getMessageTypeLabel = (type) => {
    const typeMap = {
      'all': 'All Messages',
      'text': 'Text Messages',
      'poll': 'Poll Messages',
      'logistics': 'Logistics Messages',
      'payment': 'Payment Messages',
      'ai_agent': 'AI Agent Messages',
      'voice': 'Voice Messages',
      'photo': 'Photo Messages'
    };
    return typeMap[type] || type;
  };

  const getSenderLabel = (sender) => {
    const senderMap = {
      'all': 'All Senders',
      'me': 'My Messages',
      'others': 'Others\' Messages',
      'ai': 'AI Agent Messages'
    };
    return senderMap[sender] || sender;
  };

  return (
    <div className={`search-and-filter ${isMobile ? 'mobile' : ''}`}>
      {/* Search Bar */}
      <div className={`search-bar ${isExpanded ? 'expanded' : ''}`}>
        <form onSubmit={handleSearchSubmit} className="search-form">
          <div className="search-input-container">
            <span className="search-icon">🔍</span>
            <input
              ref={searchInputRef}
              type="text"
              className="search-input"
              placeholder="Search messages..."
              value={localSearchQuery}
              onChange={(e) => setLocalSearchQuery(e.target.value)}
              onFocus={() => setIsExpanded(true)}
            />
            {localSearchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={handleClearSearch}
              >
                ✕
              </button>
            )}
          </div>
          
          {isExpanded && (
            <button type="submit" className="search-submit-btn">
              Search
            </button>
          )}
        </form>

        {/* Expand/Collapse Button */}
        <button
          className={`expand-btn ${isExpanded ? 'expanded' : ''}`}
          onClick={toggleExpanded}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Expanded Search Panel */}
      {isExpanded && (
        <div className="search-panel">
          {/* Recent Searches */}
          {recentSearches.length > 0 && (
            <div className="recent-searches">
              <h4>Recent Searches</h4>
              <div className="search-tags">
                {recentSearches.map((query, index) => (
                  <button
                    key={index}
                    className="search-tag"
                    onClick={() => handleRecentSearchClick(query)}
                  >
                    {query}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Quick Filters */}
          <div className="quick-filters">
            <h4>Quick Filters</h4>
            <div className="filter-chips">
              <button
                className={`filter-chip ${localFilterOptions.messageType === 'poll' ? 'active' : ''}`}
                onClick={() => handleFilterChange('messageType', 'poll')}
              >
                📊 Polls
              </button>
              <button
                className={`filter-chip ${localFilterOptions.messageType === 'logistics' ? 'active' : ''}`}
                onClick={() => handleFilterChange('messageType', 'logistics')}
              >
                🚚 Logistics
              </button>
              <button
                className={`filter-chip ${localFilterOptions.messageType === 'payment' ? 'active' : ''}`}
                onClick={() => handleFilterChange('messageType', 'payment')}
              >
                💰 Payments
              </button>
              <button
                className={`filter-chip ${localFilterOptions.messageType === 'ai_agent' ? 'active' : ''}`}
                onClick={() => handleFilterChange('messageType', 'ai_agent')}
              >
                🤖 AI Agent
              </button>
            </div>
          </div>

          {/* Advanced Filters Toggle */}
          <div className="advanced-filters-toggle">
            <button
              className={`toggle-btn ${showAdvancedFilters ? 'active' : ''}`}
              onClick={toggleAdvancedFilters}
            >
              {showAdvancedFilters ? 'Hide' : 'Show'} Advanced Filters
            </button>
          </div>

          {/* Advanced Filters */}
          {showAdvancedFilters && (
            <div className="advanced-filters" ref={filterPanelRef}>
              <div className="filter-group">
                <label className="filter-label">
                  <span className="filter-icon">{getFilterIcon('messageType')}</span>
                  Message Type
                </label>
                <select
                  className="filter-select"
                  value={localFilterOptions.messageType}
                  onChange={(e) => handleFilterChange('messageType', e.target.value)}
                >
                  <option value="all">All Messages</option>
                  <option value="text">Text Messages</option>
                  <option value="poll">Poll Messages</option>
                  <option value="logistics">Logistics Messages</option>
                  <option value="payment">Payment Messages</option>
                  <option value="ai_agent">AI Agent Messages</option>
                  <option value="voice">Voice Messages</option>
                  <option value="photo">Photo Messages</option>
                </select>
              </div>

              <div className="filter-group">
                <label className="filter-label">
                  <span className="filter-icon">{getFilterIcon('dateRange')}</span>
                  Date Range
                </label>
                <select
                  className="filter-select"
                  value={localFilterOptions.dateRange}
                  onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                  <option value="year">This Year</option>
                </select>
              </div>

              <div className="filter-group">
                <label className="filter-label">
                  <span className="filter-icon">{getFilterIcon('sender')}</span>
                  Sender
                </label>
                <select
                  className="filter-select"
                  value={localFilterOptions.sender}
                  onChange={(e) => handleFilterChange('sender', e.target.value)}
                >
                  <option value="all">All Senders</option>
                  <option value="me">My Messages</option>
                  <option value="others">Others' Messages</option>
                  <option value="ai">AI Agent Messages</option>
                </select>
              </div>

              {/* Clear Filters Button */}
              <div className="filter-actions">
                <button
                  className="clear-filters-btn"
                  onClick={handleClearFilters}
                >
                  🗑️ Clear All Filters
                </button>
              </div>
            </div>
          )}

          {/* Active Filters Summary */}
          <div className="active-filters">
            <h4>Active Filters</h4>
            <div className="active-filter-tags">
              {Object.entries(localFilterOptions).map(([key, value]) => {
                if (value === 'all') return null;
                
                let label = '';
                switch (key) {
                  case 'messageType':
                    label = getMessageTypeLabel(value);
                    break;
                  case 'dateRange':
                    label = getDateRangeLabel(value);
                    break;
                  case 'sender':
                    label = getSenderLabel(value);
                    break;
                  default:
                    label = `${key}: ${value}`;
                }

                return (
                  <span key={key} className="active-filter-tag">
                    {label}
                    <button
                      className="remove-filter-btn"
                      onClick={() => handleFilterChange(key, 'all')}
                    >
                      ✕
                    </button>
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchAndFilter;
