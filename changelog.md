# Changelog

All notable changes to Janus are documented here.
## [1.1.0] — 2026-05-13

### Bug Fixes

- Fixing setup and relasing 1.0.0


## [1.0.0] — 2026-05-12

### Bug Fixes

- Fix layout

- Fix exit when exception

- Use localhost instead of 0.0.0.0 for OAuth redirect URI
- Correct OAuth server address in log message
- Mount data directory instead of token.json to avoid Docker dir/file conflict
- Custom OAuth callback server to bind 0.0.0.0 with localhost redirect URI
- Pass full authorization_response URL to preserve PKCE code_verifier
- Use serve_forever with threaded shutdown for reliable OAuth callback
- Remove duplicate HTTPServer instantiation causing address in use error
- OAuth flow fixes and updated setup documentation
- Restore main branch trigger for Docker workflow
- Only shutdown OAuth server after receiving valid authorization code

### Documentation

- Update master→main URLs and credentials setup instructions
- Clarify Gmail focus and add credentials generation instructions
- Add Google OAuth credentials creation step to setup guide

### Features

- Multi-platform Docker build and explicit credentials volumes

### Miscellaneous

- Remove .claude worktrees from git tracking


