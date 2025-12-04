# AWM Pilot Frontend

A modern multi-agent dashboard for document verification and mortgage loan processing. Built with Next.js 16 and React 19.

![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?logo=tailwindcss)

## Overview

AWM Pilot provides a unified interface for managing and monitoring AI agent pipelines that automate document verification, disclosure processing, and loan officer assistance workflows.

### Agent Pipelines

| Agent | Description | Sub-Agents |
|-------|-------------|------------|
| **DrawDocs** | Document extraction and verification | Preparation → Drawcore → Verification → OrderDocs |
| **Disclosure** | Loan Estimate processing & TRID compliance | Verification → Preparation → Send |
| **LOA** | Loan Officer Assistant | Verification → Generation → Delivery |

## Features

- 🎯 **Agent Hub Dashboard** - Central view of all agent pipelines with status indicators
- 📊 **Run Management** - Create, monitor, and inspect agent runs with real-time updates
- ⏱️ **Live Polling** - Automatic 2-second refresh for active runs
- 🔍 **Run Detail View** - Timeline events, field review, and final reports
- 📱 **Collapsible Sidebar** - Space-efficient navigation
- 🎨 **Modern UI** - Built with shadcn/ui components and Tailwind CSS

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | [Next.js 16](https://nextjs.org/) (App Router) |
| UI Library | [React 19](https://react.dev/) |
| Language | [TypeScript 5.6](https://www.typescriptlang.org/) |
| Data Fetching | [TanStack React Query 5](https://tanstack.com/query) |
| Styling | [Tailwind CSS 3.4](https://tailwindcss.com/) |
| UI Components | [shadcn/ui](https://ui.shadcn.com/) (Radix primitives) |
| Icons | [Lucide React](https://lucide.dev/) |
| Date Utilities | [date-fns 4](https://date-fns.org/) |

## Getting Started

### Prerequisites

- Node.js 18+
- npm, yarn, or pnpm

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000).

### Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# Backend API URL (defaults to http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── dashboard/          # Agent Hub page
│   │   ├── disclosure/         # Disclosure agent pages
│   │   │   └── runs/           # Disclosure runs list & detail
│   │   ├── drawdocs/           # DrawDocs agent pages
│   │   │   └── runs/           # DrawDocs runs list & detail
│   │   ├── loa/                # LOA agent pages
│   │   │   └── runs/           # LOA runs list & detail
│   │   ├── documents/          # Documents management
│   │   ├── runs/               # Generic runs view
│   │   ├── globals.css         # Global styles & CSS variables
│   │   ├── layout.tsx          # Root layout with providers
│   │   └── page.tsx            # Root redirect to dashboard
│   │
│   ├── components/
│   │   ├── dashboard/          # Dashboard-specific components
│   │   │   ├── activity-feed.tsx
│   │   │   ├── agent-hub.tsx
│   │   │   └── agent-tile.tsx
│   │   ├── disclosure/         # Disclosure-specific components
│   │   ├── layout/             # Layout components
│   │   │   ├── header.tsx
│   │   │   ├── nav-section.tsx
│   │   │   └── sidebar.tsx
│   │   ├── providers/          # React context providers
│   │   │   └── query-provider.tsx
│   │   ├── runs/               # Run management components
│   │   │   ├── agent-progress-indicator.tsx
│   │   │   ├── agent-status-card.tsx
│   │   │   ├── field-review-tab.tsx
│   │   │   ├── final-report-tab.tsx
│   │   │   ├── overview-tab.tsx
│   │   │   ├── run-detail-header.tsx
│   │   │   ├── run-filters.tsx
│   │   │   ├── run-list-item.tsx
│   │   │   ├── run-trigger-form.tsx
│   │   │   ├── timeline-event.tsx
│   │   │   └── timeline-tab.tsx
│   │   ├── shared/             # Shared components
│   │   │   └── sub-agent-pipeline.tsx
│   │   └── ui/                 # shadcn/ui components
│   │       ├── agent-icon.tsx
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── dialog.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── tabs.tsx
│   │       └── ... (more UI primitives)
│   │
│   ├── hooks/                  # Custom React hooks
│   │   └── use-runs.ts         # Run data fetching hooks
│   │
│   ├── lib/                    # Utilities and API
│   │   ├── api.ts              # Backend API client
│   │   ├── log-parser.ts       # Log parsing utilities
│   │   └── utils.ts            # General utilities (cn, etc.)
│   │
│   └── types/                  # TypeScript definitions
│       ├── agents.ts           # Agent configs & sub-agents
│       ├── index.ts            # Type exports
│       └── log-events.ts       # Log event types
│
├── tailwind.config.ts          # Tailwind configuration
├── components.json             # shadcn/ui configuration
├── tsconfig.json               # TypeScript configuration
└── package.json
```

## Key Concepts

### Agent Configuration

Agent pipelines are configured in `src/types/agents.ts`:

```typescript
import { AGENT_CONFIG_MAP, getAgentConfig } from "@/types/agents";

// Get config for a specific agent
const drawdocsConfig = getAgentConfig("drawdocs");
console.log(drawdocsConfig.subAgents); // Sub-agent definitions
```

### Data Fetching

The app uses TanStack React Query with custom hooks in `src/hooks/use-runs.ts`:

```typescript
import { useRuns, useRunDetail, useCreateRun } from "@/hooks/use-runs";

// Fetch all runs (polls every 2s)
const { data: runs, isLoading } = useRuns();

// Fetch runs for specific agent
const { data: disclosureRuns } = useRuns({ agentType: "disclosure" });

// Fetch single run detail
const { data: runDetail } = useRunDetail(runId);

// Create new run
const { mutate: createRun } = useCreateRun({
  onSuccess: (data) => console.log("Created run:", data.run_id),
});
```

### API Client

The API client in `src/lib/api.ts` communicates with the backend:

```typescript
import { getRuns, getRunDetail, createRun } from "@/lib/api";

// Fetch runs
const runs = await getRuns("drawdocs");

// Create a run
const response = await createRun({
  loan_id: "12345",
  agent_type: "drawdocs",
  demo_mode: true,
});
```

## Design System

### Colors

The app uses an emerald-based color scheme defined in `tailwind.config.ts`:

| Token | Color | Usage |
|-------|-------|-------|
| `primary` | Emerald 500 | Primary actions, active states |
| `success` | Emerald 500 | Success indicators |
| `warning` | Amber 500 | Warning states |
| `destructive` | Red 500 | Errors, failed states |
| `muted` | Slate 100 | Backgrounds, disabled states |

### Status Colors by Agent Type

| Agent | Color | CSS Class |
|-------|-------|-----------|
| DrawDocs | Emerald | `bg-emerald-100 text-emerald-700` |
| Disclosure | Blue | `bg-blue-100 text-blue-700` |
| LOA | Amber | `bg-amber-100 text-amber-700` |

## Adding shadcn/ui Components

This project uses shadcn/ui. To add new components:

```bash
npx shadcn@latest add [component-name]
```

Components are installed to `src/components/ui/`.

## Backend Integration

The frontend expects a REST API backend running on port 8000 (configurable via `NEXT_PUBLIC_API_URL`).

### API Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/runs` | List all runs |
| GET | `/api/runs?agent_type={type}` | List runs by agent type |
| GET | `/api/runs/{runId}` | Get run details |
| POST | `/api/runs` | Create new run |

### Request/Response Types

See `src/lib/api.ts` for full TypeScript interfaces:
- `RunSummary` - Run list item
- `RunDetail` - Full run details with logs
- `CreateRunRequest` - New run parameters
- `CreateRunResponse` - Created run info

## License

Private - All rights reserved.

