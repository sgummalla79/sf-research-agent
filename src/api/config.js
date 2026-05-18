const API_MAP = {
  'pragna-staging.sgummallaworks.com': 'https://api-staging.sgummallaworks.com/pragna',
  'pragna.sgummallaworks.com':         'https://api.sgummallaworks.com/pragna',
}

// Empty in dev — relative paths are proxied by Vite to localhost:8000
export const API_BASE = API_MAP[window.location.hostname] ?? ''
