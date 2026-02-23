# Frontend — Tailwind CSS • Bootstrap • React

This app uses **Tailwind CSS**, **Bootstrap**, and **React** (Vite). Use it for dashboards or customer sites that call the Clawbot API.

## Stack

- **Tailwind CSS** (v4) — utility-first CSS via `@tailwindcss/vite`
- **Bootstrap** (v5) — components and grid (imported in `src/index.css`)
- **React** (v18) — UI (Vite + `@vitejs/plugin-react`)

## Commands

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
npm run build
npm run preview
```

With the dev server running, `/audit` and `/website-customers` are proxied to the Clawbot API at `http://localhost:8000` (start the API separately).

## Vue or Svelte instead of React

To use **Vue** or **Svelte** with the same Tailwind + Bootstrap stack:

- **Vue:** `npm create vite@latest frontend-vue -- --template vue`, then `cd frontend-vue && npm i tailwindcss @tailwindcss/vite bootstrap` and add the Tailwind Vite plugin and `@import 'tailwindcss'` and Bootstrap in your main CSS.
- **Svelte:** `npm create vite@latest frontend-svelte -- --template svelte`, then add Tailwind and Bootstrap the same way.

The backend (audit, website-customers) is framework-agnostic; any of these frontends can call the same API.
