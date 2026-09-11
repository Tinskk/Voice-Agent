# Workflows — the instruction layer

Markdown SOPs. Each one briefs the agent on a job the way you'd brief a
teammate: the objective, what it needs, which tools to run in what order,
what "done" looks like, and what to do when a step fails.

One workflow per file, named for the job: `deploy_agent_server.md`,
`provision_phone_number.md`.

## Ground rules

- **These are durable instructions, not scratch notes.** Don't create or overwrite a
  workflow without asking first.
- **They get better over time.** When a run surfaces a rate limit, a timing quirk, or
  a better method, fold it back into the workflow so the next run starts smarter.
- **They name tools, they don't reimplement them.** A workflow says "run
  `tools/seed_menu_sheet.py --sample-data`"; the how lives in the tool.
- **Edge cases are part of the spec.** Empty results, auth expiry, and partial
  failures are the steps most worth writing down.

Start from `_template.md`.

## About `app/`

This project also has an `app/` directory — the always-on voice-agent webhook
server. It is deliberately **not** part of the tools/workflows pattern: nobody
runs it on demand, it just runs continuously once deployed. The workflows
here that concern it (`deploy_agent_server.md`, `setup_vapi_assistant.md`) are
about setting it up and deploying it, not about invoking it step by step.
