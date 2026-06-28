/**
 * Formats a backend timestamp (defaulting to UTC) to the user's local time.
 * Handles missing 'Z' suffix from Python datetime.utcnow().
 * 
 * @param {string} timestamp - ISO timestamp string (e.g., "2023-10-27T10:00:00")
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} - Formatted local date string
 */
export const formatToLocalTime = (timestamp, options) => {
  if (!timestamp) return '';
  
  // Ensure UTC interpretation by appending Z if not present and not already ending in Z
  const dateStr = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
  const date = new Date(dateStr);
  
  // Return original text if parsing fails
  if (isNaN(date.getTime())) return timestamp; 
  
  // Default options: "Oct 27, 2023, 10:00 PM"
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  };

  return date.toLocaleString(undefined, { ...defaultOptions, ...options });
};

/**
 * Returns just the local time (e.g., "10:00 PM")
 */
export const formatTimeOnly = (timestamp) => {
  return formatToLocalTime(timestamp, { 
    year: undefined, 
    month: undefined, 
    day: undefined 
  });
};

/**
 * Returns just the local date (e.g., "Oct 27, 2023")
 */
export const formatDateOnly = (timestamp) => {
  return formatToLocalTime(timestamp, { 
    hour: undefined, 
    minute: undefined 
  });
};
