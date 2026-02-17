---
paths:
  - "dashboard/**"
---

# Dashboard Rules (React SPA)

- React + Vite + TypeScript + Shadcn/ui + TanStack Query
- Strict TypeScript — no `any` types without justification
- Components in `dashboard/src/components/`
- Pages in `dashboard/src/pages/`
- API hooks in `dashboard/src/hooks/`
- API client functions in `dashboard/src/api/`

## Conventions
- Functional components only (no class components)
- Use TanStack Query for all server state (not useState for API data)
- Use Shadcn/ui components — don't create custom components that duplicate Shadcn functionality
- No inline styles — use Tailwind CSS classes
- Colocate tests with components: `ComponentName.test.tsx` next to `ComponentName.tsx`

## WebSocket
- Single WebSocket connection managed in a React context
- Reconnection logic with exponential backoff
- All WebSocket messages are typed with TypeScript interfaces
