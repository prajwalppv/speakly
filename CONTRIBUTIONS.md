# 🤝 Contributing to Speakly

Thanks for your interest in helping build a production-grade voice transcription platform! This guide walks contributors through the logistics of working on Speakly and the quality bar we expect before merging code.

---

## 🧭 Contribution Workflow at a Glance

1. **Fork + clone** the repository (or create a branch if you have push access).
2. **Bootstrap with Docker** (`docker compose up --build`) and confirm the stack is healthy.
3. **Create a feature branch** from `main`.
4. **Develop iteratively**, commit often, and keep commits focused.
5. **Run pre-commit hooks** locally (`uv run pre-commit run --all-files`) to ensure lint/type/test gates pass.
6. **Open a pull request** once everything is green, referencing the related issue(s).
7. **Respond to reviews** promptly and keep the conversation going until merged.

---

## ✅ Prerequisites

- Docker Desktop (or an equivalent Docker environment)
- Docker Compose v2
- Git 2.40+
- Optional (for host-based workflows):
  - [uv](https://docs.astral.sh/uv/getting-started/install/) for Python dependency management
  - Node.js ≥ 20 and npm ≥ 10

---

## 🛠️ Preferred Development Environment (Docker-first)

All services (backend, frontend, Postgres) can be launched together:

```bash
cp .env.example .env         # fill in API keys/secrets
docker compose up --build    # start backend + frontend + db + support services
```

Hot reload is enabled for both backend and frontend through bind mounts, so edits are immediately reflected.

### Helpful Compose Commands

```bash
# Restart a single service (e.g. backend)
docker compose restart backend

# Tail logs
docker compose logs -f backend

# Run the backend unit/integration test suite inside the container
docker compose run --rm backend-tests

# Reset volumes/data if needed
docker compose down --volumes
```

---

## 🔁 Optional Local Workflows

If you prefer running commands directly on your host:

```bash
# Backend
cd backend
uv sync --extra dev
uv run pre-commit run --all-files
uv run pytest -m "not slow and not integration"

# Frontend
cd frontend
npm install
npm run dev
```

This workflow mirrors CI but allows you to iterate without containers.

---

## 🧹 Code Quality Gates

| Gate | Command | Notes |
|------|---------|-------|
| Formatting & linting | `uv run pre-commit run --all-files` | Covers Black, isort, Ruff, mypy (targeted), Prettier, backend unit tests |
| Backend unit tests | `docker compose run --rm backend-tests` | Preferred before PR; equivalent to host `uv run pytest` |
| Frontend type-check | `npm run typecheck` | Ensures TypeScript stays happy |
| Frontend build (optional) | `npm run build` | Useful when touching build tooling |

Pre-commit hooks are enforced in CI, so please address issues locally before pushing. Hook outputs should not modify tracked files; if they do, commit the generated changes.

---

## 🧾 Branching & Commit Guidelines

- **Branches**: `feature/<ticket-or-topic>` (e.g. `feature/journeys-filtering`)
- **Commits**: Use clear, active-voice descriptions (e.g. `Add docker-first onboarding section to README`)
- **Force pushes**: Allowed on personal feature branches; never rewrite history on `main`
- **Issues**: Link issues in commit messages and PR descriptions when applicable (`Fixes #123`)

---

## 📦 Pull Request Checklist

- [ ] Branch is up to date with `main`
- [ ] Added/updated documentation when functionality changes
- [ ] Added/updated tests when fixing bugs or adding features
- [ ] `uv run pre-commit run --all-files` succeeds
- [ ] Docker stack boots without errors (`docker compose up`)
- [ ] Included screenshots or curl snippets for significant UI/API changes (if relevant)
- [ ] PR description explains _why_ and _how_ the change was made

---

## 🔁 Code Review Expectations

- Be concise and respectful—assume good intent.
- Highlight trade-offs and design decisions in your PR description.
- Reviewers aim for 24–48 hour turnaround; ping in comments if you need more eyes.
- Approved PRs are merged by the author (or a maintainer) once feedback is addressed and CI passes.

---

## 🧑‍💼 Roles & Permissions

- **Maintainers**: Guard the health of `main`, release new versions, and coordinate roadmaps.
- **Contributors**: Anyone opening issues, submitting code, improving docs, or helping triage bugs.
- **Reviewers**: Maintainers and trusted contributors with merge history on the project.

We welcome new maintainers—show consistent, high-quality contributions and let us know!

---

## 📣 Communication

- **Issues**: Primary venue for bugs, feature ideas, and architectural discussions.
- **PR comments**: Discuss implementation specifics; keep a changelog of major updates.
- **Security disclosures**: Please email maintainers privately (contact details forthcoming) instead of opening public issues.

---

## 🛡️ Security & Compliance

- Never include secrets in code or commit history. Use `.env` files and secret managers.
- Follow least-privilege principles when provisioning API keys or database users.
- Report suspected vulnerabilities privately; we’ll respond within 72 hours.

---

## 🌱 Roadmap & Opportunities

Check the [Issues tab](https://github.com/your-org/speakly/issues) for `good first issue` and `help wanted` labels. Popular areas include:

- Expanding integrations (Notion, Todoist, Slack)
- Enhancing AI summarisation and tagging quality
- Improving analytics, audit trails, and observability
- Strengthening test coverage and load testing

---

## 🙌 Thank You

Your time and expertise keep Speakly healthy, secure, and innovative. We’re excited to build alongside you—see you in the issues and PRs! 🎧
