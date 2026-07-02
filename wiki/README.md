# GitHub Wiki Content

This directory contains markdown files that are automatically synced to the GitHub Wiki via GitHub Actions.

**Last Test: 2024-12-19 15:30 UTC** - Testing GitHub Actions workflow

## How It Works

1. **Automatic Sync**: When files in this `wiki/` directory are pushed to the main branch, a GitHub Actions workflow automatically copies them to the GitHub Wiki repository.

2. **Manual Trigger**: You can also manually trigger the sync by going to the "Actions" tab in GitHub and running the "Sync Wiki Content" workflow.

3. **Workflow Location**: The sync workflow is defined in `.github/workflows/sync-wiki.yml`

## Wiki Pages

The following pages are automatically maintained:

- **Development-Process.md** - Development process using Cursor and Taskmaster
- **Vercel-Blob-Storage.md** - Vercel Blob Storage implementation and usage
- **Cursor-Vercel-Integration.md** - Integration between Cursor and Vercel
- **Neon-Database.md** - Neon PostgreSQL database setup and usage
- **Testing-Strategy.md** - Testing strategy and implementation
- **Roadmap.md** - Development roadmap and future plans

## Editing Wiki Content

To update wiki content:

1. Edit the markdown files in this `wiki/` directory
2. Commit and push to the main branch
3. The GitHub Actions workflow will automatically sync changes to the GitHub Wiki

## Workflow Features

- **Path-based triggers**: Only runs when files in `wiki/` are changed
- **Change detection**: Only commits if there are actual changes
- **Descriptive commits**: Includes details about what was synced
- **Error handling**: Provides clear feedback on success/failure

## Manual Sync

If you need to manually sync the wiki content:

1. Go to the GitHub repository
2. Click on the "Actions" tab
3. Select "Sync Wiki Content" workflow
4. Click "Run workflow" button
5. Select the branch (usually main) and click "Run workflow"

This will immediately sync all wiki files to the GitHub Wiki repository.
