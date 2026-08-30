# TaskFlow API

A small TypeScript REST API for task management. Users can register, log in, and manage their own tasks (create, list, update, delete). Incoming webhooks can mark tasks as complete when the request is signed with a shared secret.

## Tech Stack

- **Language:** TypeScript
- **Runtime:** Node.js
- **Framework:** Express
- **Database:** PostgreSQL (via Prisma ORM)
- **Cache / queue:** Redis (`ioredis`)
- **Auth:** `bcrypt` for password hashing, `jsonwebtoken` (JWT) for sessions
- **Tooling:** `ts-node-dev`, `jest`, `eslint`, `prisma`

## Getting Started

### Prerequisites

- Node.js (>= 18 recommended)
- npm
- PostgreSQL (>= 13)
- Redis (>= 6)

### Installation

```bash
npm install
cp .env.example .env
# edit .env with your local credentials
```

### Database setup

The project uses Prisma migrations against the `DATABASE_URL` configured in `.env`.

```bash
# Apply migrations and regenerate the Prisma client
npm run db:migrate

# (Optional) seed the database
npm run db:seed
```

### Running locally

```bash
npm run dev
```

The server will start on the port defined by `PORT` (default `3000`). Health check:

```bash
curl http://localhost:3000/health
# -> { "status": "ok" }
```

### Production build

```bash
npm run build
npm start
```

## Environment Variables

Defined in `.env.example`:

| Variable | Description | Example |
| --- | --- | --- |
| `PORT` | HTTP port the API listens on | `3000` |
| `DATABASE_URL` | PostgreSQL connection string used by Prisma | `postgresql://user:password@localhost:5432/taskflow` |
| `JWT_SECRET` | Secret used to sign and verify auth JWTs | `your-secret-key` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `WEBHOOK_SECRET` | Shared secret used to verify incoming webhook signatures (HMAC-SHA256) | `your-webhook-secret` |

## API Endpoints

### Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe. Returns `{ "status": "ok" }`. |

### Auth (`/api/auth`)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create a new user. Body: `{ email, password, name }`. |
| `POST` | `/api/auth/login` | Authenticate and receive a JWT. Body: `{ email, password }`. |

### Tasks (`/api/tasks`)

All task routes require a valid JWT in the `Authorization` header.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/tasks` | List the authenticated user's tasks. |
| `POST` | `/api/tasks` | Create a task. Body: `{ title, description?, dueDate? }`. |
| `PATCH` | `/api/tasks/:id` | Update fields of a task owned by the authenticated user. |
| `DELETE` | `/api/tasks/:id` | Delete a task owned by the authenticated user. |

### Webhooks (`/api/webhooks`)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/webhooks/task-complete` | Mark a task as done. Requests must be signed with HMAC-SHA256 over the JSON body using `WEBHOOK_SECRET`; the hex digest must be sent in the `x-webhook-signature` header. Body: `{ taskId, completedAt }`. |

## Available Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start the API in watch mode using `ts-node-dev` (auto-restarts on file changes). |
| `npm run build` | Compile TypeScript sources to `dist/`. |
| `npm start` | Run the compiled output (`dist/index.js`) with Node. |
| `npm test` | Run the Jest test suite. |
| `npm run lint` | Lint the `src/` tree with ESLint. |
| `npm run db:migrate` | Apply Prisma migrations in dev mode (regenerates the Prisma client). |
| `npm run db:seed` | Run `prisma/seed.ts` against the configured database. |

## License

[MIT](./LICENSE)