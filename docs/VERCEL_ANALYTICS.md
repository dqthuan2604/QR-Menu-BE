# Vercel Web Analytics Setup

## Overview

This document explains the Vercel Web Analytics implementation for the QR-Menu Payment Service backend.

## Implementation Details

### What Was Implemented

Since this is a **FastAPI Python backend** (not a JavaScript frontend), the standard `@vercel/analytics` npm package is **not applicable**. Instead, we've implemented Vercel Web Analytics using the **HTML/JavaScript snippet approach**.

### Components Added

1. **Landing Page** (`app/static/index.html`)
   - A modern, responsive landing page for the API service
   - Includes Vercel Analytics tracking script
   - Provides links to API documentation and health check endpoints
   - Displays service features and status

2. **Static File Serving** (Updated `app/main.py`)
   - Configured FastAPI to serve static HTML files
   - Added root route (`/`) to serve the landing page
   - Mounted static files directory for assets

3. **Dependencies** (Updated `requirements.txt`)
   - Added `aiofiles>=23.2.1` for async file operations with FastAPI

### Analytics Tracking Script

The following analytics script is included in the landing page:

```html
<!-- Vercel Web Analytics -->
<script>
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
</script>
<script defer src="/_vercel/insights/script.js"></script>
```

This script automatically tracks:
- Page views on the landing page
- User interactions
- Performance metrics

## Enabling Analytics in Vercel Dashboard

To start collecting analytics data:

1. **Go to your Vercel Project Dashboard**
   - Navigate to https://vercel.com/dashboard
   - Select your QR-Menu-BE project

2. **Enable Analytics**
   - Click on the "Analytics" tab
   - Click the "Enable" button
   - Analytics will be active after the next deployment

3. **Deploy the Project**
   ```bash
   vercel deploy
   ```

4. **Verify Analytics is Working**
   - Visit your deployed site's root URL (e.g., `https://your-project.vercel.app/`)
   - Open browser DevTools → Network tab
   - Look for requests to `/_vercel/insights/script.js` and `/_vercel/insights/view`
   - If these requests appear, analytics is working correctly

## Accessing Analytics Data

After enabling analytics and deploying:

1. Return to your Vercel Project Dashboard
2. Click on the "Analytics" tab
3. You'll see metrics including:
   - Page views
   - Unique visitors
   - Top pages
   - Top referrers
   - Devices and browsers
   - Geographic data

## Important Notes

### For Backend APIs

⚠️ **Important**: Vercel Web Analytics is designed to track **web page visits**, not API endpoint calls.

This implementation tracks:
- ✅ Visits to the landing page (`/`)
- ✅ User interactions on web pages
- ✅ Page performance metrics

This implementation **does NOT** track:
- ❌ API endpoint requests (`/api/v1/*`)
- ❌ Health check calls (`/health`)
- ❌ Backend-to-backend API calls

### For Full Application Analytics

If you have a **frontend application** (React, Next.js, Vue, etc.) that consumes this API, you should:

1. Install `@vercel/analytics` in your frontend project:
   ```bash
   npm install @vercel/analytics
   # or
   pnpm install @vercel/analytics
   ```

2. Add the Analytics component to your frontend application (framework-specific):

   **Next.js (App Router):**
   ```typescript
   // app/layout.tsx
   import { Analytics } from '@vercel/analytics/next';

   export default function RootLayout({ children }) {
     return (
       <html>
         <body>
           {children}
           <Analytics />
         </body>
       </html>
     );
   }
   ```

   **React:**
   ```javascript
   // App.jsx
   import { Analytics } from '@vercel/analytics/react';

   function App() {
     return (
       <>
         {/* Your app content */}
         <Analytics />
       </>
     );
   }
   ```

### For API Monitoring

For monitoring API endpoint performance and usage, consider:

1. **Vercel Functions Logs** - Available in Vercel Dashboard
2. **Custom Application Monitoring** - Tools like:
   - Sentry for error tracking
   - DataDog or New Relic for APM
   - Custom logging with structured logs
3. **API Analytics Services** - Tools like:
   - Posthog
   - Mixpanel
   - Custom analytics endpoints

## Testing Locally

To test the landing page locally:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Visit the landing page:**
   ```
   http://localhost:8000/
   ```

Note: The analytics script will not send data in local development. It only works when deployed to Vercel.

## Files Modified

- `app/main.py` - Added static file serving and root route
- `app/static/index.html` - Created landing page with analytics
- `requirements.txt` - Added `aiofiles` dependency
- `vercel.json` - Updated configuration
- `docs/VERCEL_ANALYTICS.md` - This documentation file

## Resources

- [Vercel Analytics Documentation](https://vercel.com/docs/analytics)
- [Vercel Analytics Quickstart](https://vercel.com/docs/analytics/quickstart)
- [FastAPI Static Files Documentation](https://fastapi.tiangolo.com/tutorial/static-files/)

## Support

For issues or questions:
- Check the [Vercel Analytics Docs](https://vercel.com/docs/analytics)
- Review the [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Open an issue in the project repository
