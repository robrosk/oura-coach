# Oura Coach Web

Mobile-friendly React website for Oura Coach. Provides landing pages, legal documents (Privacy Policy, Terms of Service), and OAuth integration entry point.

## Features

- **Landing page** with app overview
- **Privacy Policy** and **Terms of Service** pages (markdown-based, easy to edit)
- **Terms acceptance gate** - users must scroll through and accept terms before accessing the app
- **OAuth flow UI** - Connect Oura button that initiates backend OAuth
- **Dark theme** - minimal, iOS-friendly design
- **PWA-ready** - can be added to home screen on iOS/Android

## Getting Started

### Prerequisites

- Node.js 20.19+ or 22.12+
- npm

### Install dependencies

```bash
cd web
npm install
```

### Configure environment

Copy the example env file and configure:

```bash
cp .env.example .env
```

Edit `.env` to set your backend URL:

```
VITE_BACKEND_BASE_URL=http://localhost:8000
```

### Run development server

```bash
npm run dev
```

Opens at http://localhost:5173

### Build for production

```bash
npm run build
```

Output is in `dist/` folder.

### Preview production build

```bash
npm run preview
```

## Project Structure

```
web/
├── public/
│   ├── manifest.json      # PWA manifest
│   └── favicon.svg        # Site favicon
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Layout.tsx
│   │   ├── MarkdownPage.tsx
│   │   ├── ScrollableTerms.tsx
│   │   └── TermsGate.tsx
│   ├── content/           # Markdown content (editable)
│   │   ├── privacy.md
│   │   └── terms.md
│   ├── lib/               # Utilities
│   │   ├── api.ts         # Backend API client
│   │   ├── storage.ts     # localStorage helpers
│   │   └── terms.ts       # Terms version management
│   ├── pages/             # Route pages
│   │   ├── Home.tsx
│   │   ├── Privacy.tsx
│   │   ├── Terms.tsx
│   │   ├── Accept.tsx
│   │   └── app/
│   │       ├── AppHome.tsx
│   │       ├── Connect.tsx
│   │       └── Welcome.tsx
│   ├── types/             # TypeScript types
│   │   └── index.ts
│   ├── App.tsx            # Main app with routes
│   ├── main.tsx           # Entry point
│   └── index.css          # Global styles + Tailwind
├── .env.example           # Environment template
└── README.md
```

## Routes

| Route | Description | Protected |
|-------|-------------|-----------|
| `/` | Landing page | No |
| `/privacy` | Privacy Policy | No |
| `/terms` | Terms of Service | No |
| `/accept` | Terms acceptance gate | No |
| `/app` | App home (placeholder) | Yes |
| `/app/connect` | Oura OAuth initiation | Yes |
| `/app/welcome` | Post-OAuth landing | Yes |

Protected routes redirect to `/accept` if terms haven't been accepted.

## Editing Content

Privacy Policy and Terms of Service are stored as markdown files in `src/content/`. Edit these files directly and rebuild.

### Updating Terms Version

When you make material changes to Terms of Service:

1. Edit `src/content/terms.md`
2. Update the version in `src/lib/terms.ts`:
   ```ts
   export const CURRENT_TERMS_VERSION = '2026-01-05'; // new date
   ```
3. Users will need to re-accept the new version

## Terms Acceptance Flow

The `/accept` page requires users to:

1. Scroll to the bottom of the Terms content
2. Check "I have read and accept the Terms of Service"
3. Check "I have read the Privacy Policy"

Only then can they continue to the app.

Acceptance is stored in localStorage with:
- `termsAccepted: true`
- `termsAcceptedAt: ISO timestamp`
- `termsVersion: "2026-01-04"`
- `privacyAcknowledged: true`

## OAuth Flow

The "Connect Oura" button calls `GET {BACKEND_URL}/oura/connect/start` expecting:

```json
{
  "auth_url": "https://cloud.ouraring.com/oauth/authorize?..."
}
```

The frontend then redirects the browser to `auth_url`. The backend handles the OAuth callback and token exchange.

## Deployment

### GitHub Pages

1. Update `vite.config.ts` with your base path if needed:
   ```ts
   export default defineConfig({
     base: '/your-repo-name/',
     // ...
   })
   ```

2. Build and deploy the `dist/` folder

### Other Platforms

Build with `npm run build` and deploy the `dist/` folder to any static hosting (Vercel, Netlify, Cloudflare Pages, etc.)

## Development Notes

- **Contact email**: Search for `<YOUR_CONTACT_EMAIL>` in content files to replace with your actual email
- **PWA icons**: Add `icon-192.png` and `icon-512.png` to `public/` for full PWA support
- **Reset acceptance**: Click the subtle "Reset acceptance (dev)" link in the footer for testing
