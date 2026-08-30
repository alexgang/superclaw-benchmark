# Competitive Analysis: GitHub Copilot vs. Cursor vs. Kilo Code

*A comparison of three AI code assistants in the IDE — August 2026*

---

## Comparison at a Glance

| Dimension | **GitHub Copilot** | **Cursor** | **Kilo Code** |
|---|---|---|---|
| **Vendor** | GitHub / Microsoft | Anysphere | Kilo (open source community) |
| **Form factor** | Extension (VS Code, JetBrains, Visual Studio, IDEs); also CLI & cloud agent | Standalone IDE (VS Code fork) | Extension (VS Code, JetBrains); also CLI & cloud |
| **Free tier** | Yes (limited: 2,000 completions/mo, limited chat/agent) | Yes ("Hobby" — limited Agent + Tab completions) | Yes — extension itself is free; pay only the model provider at cost |
| **Individual paid** | Pro $10/mo, Pro+ $39/mo, Max $100/mo | Pro $20/mo, Pro+ $60/mo, Ultra $200/mo | Pay-as-you-go via provider (no markup); Kilo credits optional |
| **Team / Enterprise** | Business $19/seat, Enterprise $39/seat | Teams $40/user (or $120 Premium), Enterprise custom | Self-host or pay-as-you-go; Enterprise via sales |
| **Billing model** | Subscription + AI Credits (token-based, post-June 2026) | Subscription + credits ≈ monthly price; overages on demand | Pass-through model provider pricing (zero markup) |
| **Code completion** | Yes (unlimited on paid plans) | Yes (Tab; unlimited on paid) | Yes (smart autocomplete) |
| **Chat** | Yes (Copilot Chat) | Yes (in-editor + cmd-K) | Yes (Ask / Architect / Debug modes) |
| **Multi-file editing** | Yes (Copilot Edits / Agent mode) | Yes (Composer / Agent) | Yes (Code / Orchestrator modes) |
| **Agent mode** | Yes (coding agent, cloud agent on Business+) | Yes (Cursor Agent, Background/Cloud Agents) | Yes (parallel agents, subagent delegation) |
| **Tool use / MCP** | MCP support | MCP support | MCP support + curated marketplace |
| **Models** | GPT-4o, GPT-5 family, Claude, Gemini, others | GPT, Claude, Gemini, Grok + first-party "Composer" | 500+ models (frontier, open-weight, local) |
| **BYOK (own API key)** | Limited / via enterprise | Yes (OpenAI, Anthropic, Google, xAI keys) | Yes — fully supported, encouraged |
| **Cloud-free / offline** | No — cloud required | No — cloud required | Partially — can route to local models / Ollama |
| **Open source** | No (proprietary) | No (proprietary, VS Code fork) | Yes — open source core |
| **License** | Closed | Closed | Apache-2.0 / MIT-licensed core (extension on Marketplace) |
| **Self-hostable** | No | No (client + cloud) | Yes — fork, modify, self-host |
| **3M+ downloads / scale** | Largest install base | Popular individual dev choice | 3M+ "Kilo Coders", #1 on OpenRouter |

---

## 1. GitHub Copilot

The incumbent: deep GitHub integration, broad IDE support, and the largest deployment of any AI coding tool.

### Pricing

As of June 2026, Copilot moved to **usage-based billing** ("AI Credits") on top of subscription fees. Code completions and "Next Edit" suggestions stay included and do **not** consume credits.

| Plan | Price | AI Credits / mo | Audience |
|---|---|---|---|
| Free | $0 | Limited chat & agent; 2,000 completions/mo | Trying it out |
| Pro | $10/mo | $10 of AI Credits included | Solo developers |
| Pro+ | $39/mo | $39 of AI Credits | Power users / heavy agent workflows |
| Max | $100/mo | ~$200 of AI Credits (~20,000 unit allowance) | High-volume agent work |
| Business | $19/seat/mo | $19/seat AI Credits (existing customers got promotional $30 through Aug 2026) | Teams needing admin policy controls |
| Enterprise | $39/seat/mo | $39/seat AI Credits (existing customers got promotional $70) | Large orgs on GitHub Enterprise Cloud |

Promo note: existing Business/Enterprise customers received bonus credits ($30/$70) through August 2026 to ease the migration.

### Features

- **Code completion** — original flagship; unlimited on every paid plan, 2,000/mo on Free.
- **Chat** — Copilot Chat in-IDE and on GitHub.com (Enterprise).
- **Multi-file editing** — "Copilot Edits" and agent mode for cross-file changes.
- **Agent mode** — Coding agent that can plan, edit, run commands, and open PRs. **Cloud agent** available on Business and Enterprise for asynchronous background work.
- **Tool use & MCP** — supports the Model Context Protocol for connecting external tools/data sources.
- **Copilot Spaces** — bundled context packs; included on every plan.
- **Code review & PR summaries** — Enterprise tier adds GitHub.com chat, codebase indexing, and priority model access.

### Model support

Copilot routes across multiple providers. Catalog includes **OpenAI GPT-4o / GPT-5 family**, **Anthropic Claude**, **Google Gemini**, and other premium models. **BYOK is not a primary path** for individual plans; it's available in enterprise configurations and via paid premium-model routing. The user typically picks a model inside Copilot rather than supplying their own key.

### Privacy / data

- **Free / Pro / Pro+**: as of April 24, 2026, GitHub uses interaction data (prompts, code suggestions, comments) for model training **unless you opt out**. Opt-out is in account settings under *Settings → Copilot → Features / Privacy*. Students/teachers and verified OSS contributors are exempt from training.
- **Business / Enterprise**: training is **off by default** — customer data is not used to train models, with retention and isolation guarantees.
- Code is sent to GitHub's cloud (or the model's provider) for inference — **no fully offline mode**.

### Open source

Closed source. Cannot be self-hosted.

---

## 2. Cursor

A standalone AI-first IDE (a fork of VS Code) built by Anysphere. Known for the smoothest "Tab" completion experience and aggressive agent workflows ("Composer").

### Pricing

Cursor uses a **credit-based subscription**: monthly price maps roughly to a credit pool; premium models and Max mode burn credits faster; on-demand overages apply when the pool is exhausted.

| Plan | Price | Included usage | Notes |
|---|---|---|---|
| Hobby | Free | Limited Agent + Tab completions | No credit card required |
| Pro | $20/mo (~$16/mo annual) | $20 of model usage | Standard tier for daily developers |
| Pro+ | $60/mo | $70 of usage | Heavy individual Agent users |
| Ultra | $200/mo | $400 of usage | Power users running agents all day |
| Teams (Standard) | $40/user/mo | $20/user usage | Admin & team billing |
| Teams (Premium) | $120/user/mo | 5× Standard usage | Added in June 2026 |
| Enterprise | Custom | — | Audit, compliance, SSO |

**Annual billing saves ~20%.** Auto mode and smaller/faster models stretch credits further.

### Features

- **Tab completion** — Cursor's signature feature; predictive multi-line edits that flow from prior changes.
- **Chat / cmd-K** — inline chat and quick-edit commands.
- **Multi-file editing & Composer** — agent mode that plans across files, applies a diff preview, and iterates.
- **Agent mode** — both interactive agent and **Background / Cloud Agents** for async long-running work.
- **MCP support** — connect external tools, databases, and context servers.
- **Max context window** — long-context model access on paid plans.
- **Skills & Hooks** — workflow automation primitives (Pro+).

### Model support

Cursor offers **frontier models across providers**: OpenAI (GPT-5 family), Anthropic Claude, Google Gemini, and xAI Grok, plus first-party **Composer** models optimized for its editor.

- **BYOK**: yes — OpenAI, Anthropic, Google Vertex, xAI keys can be plugged in directly so usage is billed to your account rather than Cursor's credit pool.

### Privacy / data

- **Default state**: Cursor and its model providers may retain telemetry for product improvement.
- **Privacy Mode** (new, in settings): Cursor will not train on your data; **zero-data-retention (ZDR) agreements** are enforced with OpenAI, Anthropic, Google Vertex, and xAI Grok — providers cannot store or train on your data.
- **Privacy Mode (Legacy)**: same guarantees plus no code storage at all; some features (e.g. Background Agent) are disabled.
- **Abuse detection carve-out**: even in Privacy Mode, abuse-classifier hits can still be stored. Model providers' own policies may also apply (e.g., special handling during Grok "free period").
- Code is processed in the cloud — **no fully offline mode**.

### Open source

Closed source. Cursor is a fork of VS Code but the AI features, Composer model, and infrastructure are proprietary and not self-hostable.

---

## 3. Kilo Code

An open-source "agentic engineering platform" with the same portable core available as a **VS Code extension**, **JetBrains plugin**, and **CLI** (`kilo`). Marketed as "the most popular open source coding agent," with 3M+ "Kilo Coders" and 40T+ tokens processed. Backed by the open-source foundation **OpenCode**.

### Pricing

Open pricing philosophy: **pay the model provider's rate with zero markup**. The extension itself is free; the optional Kilo-managed account adds convenience but no surcharge.

| Plan | Price | Notes |
|---|---|---|
| Free extension | $0 | Bring your own provider key, or sign up with no API keys required to start |
| Pay-as-you-go via Kilo | Pass-through | Provider cost + 0% markup; charged for tokens used |
| Bring-your-own-key (BYOK) | Provider's rate | Use your OpenAI / Anthropic / Google / etc. account |
| Local models (Ollama etc.) | $0 inference | Route through OpenAI-compatible local endpoint |
| Enterprise / Team | Contact sales | Self-host, custom deployments |

**Key differentiator**: 500+ models — frontier (GPT-5.5, Claude Opus 4.7, Claude Sonnet 4.6, Gemini 3.1 Pro Preview), open-weight (Llama, Qwen, DeepSeek), and local — **all switchable mid-task** with **no silent model swaps**.

### Features

- **Specialized modes**: Ask, Architect, Code, Debug, Orchestrator — distinct personas for different stages of development.
- **Smart autocomplete** (Tab) — inline code completion.
- **Multi-file editing** — Code mode handles cross-file changes.
- **Agent mode** — including **parallel agents** and **subagent delegation** (delegating to specialized subagents).
- **Tool use & MCP** — full MCP support, plus a curated **Kilo Marketplace** of Skills, MCP servers, and Modes.
- **Sandboxed auto mode** — workspace-only writes and network-deny controls so agents can run without giving them the whole machine.
- **Cross-platform sessions** — start in VS Code, hand off to the CLI, continue in the cloud.
- **Automatic failure recovery**, hallucination mitigation, deep context awareness.

### Model support

The widest model flexibility of the three:

- **500+ models** across providers — frontier (GPT-5.5, Claude Opus 4.7/4.6, Gemini 3.1 Pro), open-weight (Llama, Qwen, DeepSeek, Mistral), and **local models** via Ollama or any OpenAI-compatible endpoint.
- **BYOK**: fully supported and encouraged — drop in keys for OpenAI, Anthropic, Google, OpenRouter, etc.
- **Mid-task model switching** — change models without losing context.
- **No silent model switching** — what you pick is what runs.

### Privacy / data

- **Source code visibility**: prompts, context window, and decisions are **inspectable** in MIT-licensed source.
- **Self-hostable**: can run entirely against local models via Ollama, so **no code leaves your machine**.
- **Cloud path (Kilo-managed)**: when using Kilo's hosted access, prompts are routed to your chosen provider — privacy posture depends on the provider's policy (ZDR-style agreements vary by provider).
- **Best-in-class local mode**: the only one of the three that can realistically operate fully offline against local models.

### Open source

- **Yes** — extension and core are open source.
- **License**: Apache-2.0 (kilocode repo); marketplace components MIT.
- **Self-hostable** — fork, modify, self-host.
- **Public roadmap / issues** on GitHub (kilo-org/kilocode), 39+ public repos.
- Built on **OpenCode** as the open-source foundation.

---

## Bottom Line — Recommendations by Profile

### 🧑‍💻 Hobbyist / Student

- **Best choice: Kilo Code** — free, open source, BYOK to cheap or local models. Total cost of ownership can be effectively zero using Ollama + a small open-weight model.
- **Runner-up: GitHub Copilot Free** — if you just want a polished experience with no setup, the 2,000 completions/mo + limited chat is enough to learn.
- **Cursor Hobby** is fine for evaluation but the editor switch is a bigger commitment than an extension.

### 🚀 Startup Developer / Solo Founder

- **Best choice: GitHub Copilot Pro ($10/mo)** for the lowest-friction experience and unmatched GitHub integration (PRs, issues, code review).
- **Best for AI-heavy workflows: Cursor Pro ($20/mo)** — if you live inside the agent loop and want the best Tab + Composer experience, the extra $10/mo pays for itself in saved context-switching.
- **Best for cost control & model choice: Kilo Code with BYOK** — especially valuable when you want to mix frontier models with cheaper open-weight models for routine tasks; sandbox mode helps when letting agents run unattended on a real codebase.

### 🏢 Enterprise Team

- **Best overall: GitHub Copilot Business ($19/seat) or Enterprise ($39/seat)** — the only product in this comparison with mature enterprise controls: SSO, policy management, audit, IP indemnity, and training-off-by-default data guarantees. Required for many regulated buyers.
- **Best for AI-first engineering orgs that already use VS Code: Cursor Teams ($40/user Standard, $120/user Premium)** — strong DX, MCP support, Privacy Mode + ZDR with major providers. Consider Enterprise for SOC 2 / DPA / GDPR commitments.
- **Best for security-sensitive / regulated / air-gapped: Kilo Code (self-hosted)** — the **only** option of the three that can be **self-hosted, audited, and run against local models**. If your code cannot leave the network, Kilo is the realistic choice. Requires more DevOps investment.

### 🎯 Decision Cheat Sheet

| Your priority | Pick |
|---|---|
| Lowest friction + GitHub-native | **Copilot Pro / Business** |
| Best agentic editing UX | **Cursor Pro / Teams** |
| Lowest cost / model flexibility | **Kilo Code + BYOK / local** |
| Strict data residency / air-gap | **Kilo Code (self-hosted)** |
| Open source mandate | **Kilo Code** |
| Enterprise compliance + IP indemnity | **Copilot Enterprise** |
| Maximum credits for heavy agent work | **Copilot Max** or **Cursor Ultra** |

---

*Sources: GitHub Copilot official plans page (`docs.github.com/en/copilot/get-started/plans`, `github.com/features/copilot/plans`) and `github.blog` usage-based billing announcement; Cursor official pricing and `cursor.com/data-use` privacy page; Kilo Code at `kilo.ai` and `github.com/kilo-org/kilocode`. Pricing and policy details reflect published information as of August 2026 and may change.*