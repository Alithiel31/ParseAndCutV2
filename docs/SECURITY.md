# Security Policy

🇫🇷 [Version française](./SECURITY.fr.md)

## Supported versions

**Meetup Killer** (ParseAndCutV2) is a small, actively developed project deployed from the `main` branch. Only the latest version running at [parseandcut.alithiel31.dev](https://parseandcut.alithiel31.dev) is supported — there are no maintained older releases.

## Reporting a vulnerability

If you find a security issue (e.g. a way to bypass upload validation, abuse the API to run up Groq costs, access another user's data, or escape the Docker container), please **do not open a public GitHub issue**.

Instead, report it privately by email: **contact@alithiel31.dev**

Please include:
- A description of the issue and its potential impact
- Steps to reproduce (a minimal example is ideal)
- Any suggested fix, if you have one

You should get an acknowledgement within a few days. As this is a single-maintainer, non-professional project, there's no formal SLA, but valid reports will be fixed as a priority and credited in the changelog unless you'd prefer otherwise.

## Scope

This covers the backend API (`app/`) and the frontend PWA (`frontend/`) in this repository. Third-party services this project depends on (Groq, Cloudflare) should be reported directly to those vendors.
