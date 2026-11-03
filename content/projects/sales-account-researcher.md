---
id: sales-account-researcher
name: Sales Account Researcher
status: Idea
topics: [Sales, Agents, RAG]
stack: [hermes-agent, Playwright, Archon, n8n]
repo:
---

An agent that prepares a one-page brief before every sales call. Given a
company name, it browses the company's site, recent filings, press releases,
and job postings, extracts who the buyers are, what they are hiring for, and
which initiatives were just announced, and drafts three tailored talking points
with a citation behind every claim.

The research loop is a tool-using agent driving a headless browser, a
knowledge-base layer stores what it learns so the next brief on the same
account starts warm, and a workflow-automation tool kicks off a brief whenever
a meeting lands on the calendar and files the result into the CRM. It shares
the "answer only with a source" rule of the document intelligence engine,
pointed at the open web instead of a filing cabinet.
