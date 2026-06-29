export const formatApiError = (data, fallback = 'Request failed. Please try again.') => {
  const detail = data?.detail ?? data?.message ?? data?.error;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : item?.field;
        const message = item?.msg || item?.message || JSON.stringify(item);
        return field ? `${field}: ${message}` : message;
      })
      .join(' ');
  }

  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }

  return detail || fallback;
};

export const parseApiResponse = async (response) => {
  const responseText = await response.text();
  if (!responseText) return {};

  try {
    return JSON.parse(responseText);
  } catch {
    if (response.ok) {
      throw new Error('Server returned an unexpected response.');
    }
    throw new Error(`Server returned ${response.status}: ${responseText.slice(0, 160)}`);
  }
};
