# Orca Embedded Browser Controls

Orca contains an integrated Chromium browser for previewing local development servers, inspecting web UI changes, and taking screenshots.

## Commands

### 1. Open URL in Orca Tab
```bash
ORCA open-url --url http://localhost:3000
```
Focuses or opens a dedicated browser tab inside the Orca workspace.

### 2. Capture Headless Screenshot
```bash
ORCA browser screenshot --url http://localhost:3000 --path /tmp/preview.png
```
Takes a high-resolution screenshot of the rendered web page for visual verification.
