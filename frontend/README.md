# SalesBattle Frontend Client

Modern, responsive React 19 single-page application built with Vite for Paramantra Sales Intelligence.

---

## Component Structure

```
frontend/src/
├── components/
│   ├── Header.jsx              # Navigation header, lead selector, live DB status
│   ├── Sidebar.jsx             # Collapsible primary navigation
│   ├── DealHealthGauge.jsx     # Radial 0-10 gauge, emotional meters, channel pulse
│   ├── CompetitorRadar.jsx     # Detected competitors, objection angles, CRM push
│   ├── DealSimulator.jsx       # Interactive What-If deal scenario simulator
│   ├── RepActionCoPilot.jsx    # Recommended next best action & scripted talk tracks
│   ├── SentimentDrivers.jsx    # Quoted positive momentum & deal friction attribution
│   ├── LeadProfile.jsx         # Contact banner, pipeline stage, and quick actions
│   ├── OmnichannelTimeline.jsx # Unified timeline across WhatsApp, Calls, Emails
│   ├── RightUtilityPanel.jsx   # Quick action buttons & recent interactions
│   └── Modals.jsx              # Proposal draft, company profile, edit lead, search
├── useLeadData.js              # Custom hook handling API calls & SSE streaming
├── App.jsx                     # Root application container & tab router
└── index.css                   # Enterprise dark-theme CSS design system
```

---

## Development Setup

```bash
cd frontend
npm install

# Run unit tests
npm test

# Run Oxlint linter
npm run lint

# Start Vite dev server on port 5173
npm run dev

# Build for production
npm run build
```

---

## Key Features & UI Modules

1. **Dashboard Tab**:
   - Radial Deal Health Gauge with color-coded classification (`🔥 Hot`, `⚡ Warm`, `❄️ Cold`).
   - Emotional & Commercial Stance meters (Trust & Rapport, Commercial Urgency, Negotiation Stance).
   - Channel Sentiment Pulse highlighting score by medium.
   - Competitor Radar with 3 objection rebuttal angles (Value, Technical, SLA).
   - What-If Strategy Simulator with dynamic score projections.
2. **Leads Matrix Tab**:
   - Pipeline-wide table of all opportunities.
   - Dynamic stage filters (`ALL`, `Proposal Under Review`, `Negotiation`, `Discovery`, `Progress`).
   - Live search across contact name, company, ID, or assigned rep.
3. **Accounts Dossier Tab**:
   - Multi-stakeholder view and account-level overview.
4. **Reports Tab**:
   - Executive deal review deck with one-click print-to-PDF formatting.
