# SalesBattle frontend

See the repository README for setup, configuration and API behavior.

- `npm.cmd ci` installs the locked frontend dependencies.
- `npm.cmd run dev` starts Vite with the API proxy to localhost:8000.
- `npm.cmd run build` writes `dist`, served by FastAPI.
- `npm.cmd run lint` checks React and JavaScript.
- `npm.cmd test` runs the API/request-state regression tests.

The interface shows real CRM data or explicit empty/error states. Analysis generation is an explicit user action. Keep API keys and database credentials exclusively in the backend environment.
