# Security Policy

le-tour is early-access software that can control trainer resistance. Please
report security and safety-sensitive issues responsibly.

## Supported Versions

Only the latest code on the default branch and the latest alpha release are
currently supported for security fixes.

## Reporting a Vulnerability

Do not open a public GitHub issue for vulnerabilities.

Use GitHub's private vulnerability reporting feature if it is enabled for the
repository. If it is not enabled, contact the project maintainer privately and
include enough detail to reproduce the issue.

Please include:

- affected version or commit
- operating system and browser
- trainer or heart-rate monitor model, if relevant
- clear reproduction steps
- logs with secrets and personal data removed

## Sensitive Areas

Please report privately if you find issues involving:

- leaked secrets, tokens, or `.env` values
- local ride data exposure
- unsafe trainer-control behavior in ERG or SIM mode
- unauthorized Bluetooth device control
- CSV export path traversal or unexpected file writes
- cross-site scripting or local web-server exposure

## Safety Issues

If a bug can cause unexpected resistance, uncontrolled ERG targets, incorrect
SIM grade control, or any behavior that could physically affect a rider, treat it
as security-sensitive and report it privately.

## No Bug Bounty

There is currently no paid bug bounty program.
