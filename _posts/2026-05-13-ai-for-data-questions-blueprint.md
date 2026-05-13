---
layout: post
title: "A Blueprint for AI-Powered Data Questions Inside the Organization"
comments: true
date: 2026-05-13
categories: ai, code
---

I recently listened to a great episode of [Startup for Startup](https://open.spotify.com/episode/6hsRV4ZbmY6ZUmK21pCOdO?si=sHgOLIDERNetOU0QtdXbrg) by monday.com, where they shared how they built an internal AI agent that can answer data questions across the company. What I loved about the episode is that it's not abstract hype, it's a practical blueprint. They walked through the real problems they had to solve and the architectural decisions they made along the way.

This is, in my opinion, one of the highest-leverage AI use cases inside any organization: democratizing access to data so that anyone, from a sales rep to a product manager, can ask a question in natural language and get a trustworthy answer. But getting there is harder than it sounds. Here are the main building blocks they described.

## 1. The Semantic Layer - so the AI knows *what* to query

The first problem is that raw tables and columns are meaningless to an LLM (and often to humans too). What does `usr_activ_30d_v2` mean? Is "active user" the same definition the marketing team uses and the finance team uses? Probably not.

The semantic layer is the translation between the messy reality of the data warehouse and the business concepts people actually talk about. It defines entities, metrics, dimensions, and their relationships in a way the agent can reason over. Without it, the agent is guessing.

## 2. Skills - so the AI knows *how* to query and analyze

Different disciplines in the company analyze data differently. A growth analyst thinks about funnels and cohorts. A finance analyst thinks about MRR and churn. A product analyst thinks about feature adoption and retention curves.

Rather than expecting one giant prompt to capture all of this, they built **skills** - reusable capabilities scoped to a discipline. Each skill encodes the playbook for how to approach a certain class of questions: which tables to use, which metrics to compute, which caveats to mention. This makes the agent dramatically more accurate and gives subject matter experts a place to contribute their knowledge.

## 3. Benchmarks - how do you evaluate the agent?

This is the part most teams underinvest in, and it's the part that matters most. They split evaluation into two layers:

- **Development-time benchmarks** - a curated set of questions with known correct answers, run continuously as the system evolves. This is how you know whether a prompt change, a new model, or a new skill actually improved things or quietly regressed them.
- **Per-response evaluation** - for every answer the agent returns in production, some form of evaluation is performed (LLM-as-judge, sanity checks, confidence signals) so users get a sense of how much to trust the output.

Without benchmarks, every change becomes a vibes-based decision and you accumulate invisible regressions.

## 4. Governance - who can see what?

Data access in any real company is not uniform. HR data, financial data, customer data - all have different access rules. The agent must respect them. If a user couldn't see a table by querying it directly, the agent must not surface that data either.

This means the agent has to operate on behalf of the user, with the user's permissions, and every query has to be auditable. Governance is not an afterthought you bolt on at the end - it has to be designed into the architecture from day one.

## 5. Implementation as an MCP - "bring your own agent"

Instead of building one monolithic chat product, they exposed the capabilities through MCP (Model Context Protocol). This means any agent inside the company - Claude, internal agents, future agents that don't exist yet - can consume the data-question capability as a tool.

This is a great architectural choice. It decouples the *capability* (answer data questions over our warehouse, with our semantics, our skills, our governance) from the *interface* (chat, Slack, IDE, custom workflows). The capability is built once and reused everywhere.

## 6. Customization - from one monolith to many scoped agents

They started with a single agent that tried to do everything. It worked, but business users wanted more granularity - an agent that only knows about their domain, with their custom instructions, their preferred metrics, their tone.

So they added a customization layer that lets users create **scoped agents** with a narrower focus. This is a pattern worth noting: start with a single general-purpose agent to validate the approach, then let power users carve out specialized versions once you understand what they actually need.

## What's still hard - future work

The episode was refreshingly honest about open problems:

- **Trust** - even with benchmarks and evals, how do you give users confidence in any individual answer? How do you communicate uncertainty without making the answer useless?
- **Staleness of skills** - the data warehouse changes. Definitions drift. Tables get deprecated. How do you keep skills fresh without a human babysitting every one of them?
- **From reactive to proactive** - today the agent answers questions when asked. The bigger prize is an agent that notices anomalies, surfaces insights, and flags problems before anyone thinks to ask.

## My takeaway

What stood out to me is that none of these building blocks are AI problems in the narrow sense. Semantic layers, governance, benchmarks, customization - these are *data platform* problems and *product* problems. The LLM is the easy part. The reason most "AI for data" projects fail is that they treat the LLM as the product and skip the boring infrastructure underneath.

If you're thinking about building something like this inside your own company, this episode is the closest thing to a real blueprint I've heard. Start with the semantic layer, take governance seriously from day one, invest in benchmarks before you invest in features, and expose the capability as a tool that any agent can call.
