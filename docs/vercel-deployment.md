# Vercel Deployment Guide

This document describes how to deploy the Viewer application to Vercel using the automated GitHub Actions workflow.

## Overview

The application is automatically deployed to Vercel when changes are pushed to the `main` branch, or can be manually triggered via workflow dispatch.

## Setup Instructions

### Prerequisites

1. A Vercel account (sign up at [vercel.com](https://vercel.com))
2. A Vercel project created for this repository
3. Access to configure GitHub repository secrets

### Required GitHub Secrets

The following secrets must be configured in your GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

1. **VERCEL_TOKEN**: Your Vercel authentication token
   - Generate at: https://vercel.com/account/tokens
   - Select appropriate scope (recommended: full access for deployment)

2. **VERCEL_ORG_ID**: Your Vercel organization/team ID
   - Find in your Vercel project settings
   - Navigate to: `Project Settings` → `General`
   - Look for "Organization ID" or "Team ID"

3. **VERCEL_PROJECT_ID**: Your Vercel project ID
   - Find in your Vercel project settings
   - Navigate to: `Project Settings` → `General`
   - Look for "Project ID"

### Environment Variables

The application requires the following environment variables to be set in Vercel:

1. **DATABASE_URL**: Database connection string
   - For SQLite (development): `sqlite:///secureapp.db`
   - For PostgreSQL (production): `postgresql://username:password@host/database`

2. **SESSION_SECRET**: Flask session secret key
   - Generate a secure random string
   - Example: `python -c "import secrets; print(secrets.token_hex(32))"`

3. **TESTING** (optional): Set to "False" for production

Configure these in Vercel project settings:
- Navigate to: `Project Settings` → `Environment Variables`
- Add each variable with appropriate values

### Optional Environment Variables

- **LOGFIRE_API_KEY**: Enable Logfire observability
- **LOGFIRE_PROJECT_URL**: Link to Logfire project
- **LANGSMITH_API_KEY**: Enable LangSmith integration
- **LANGSMITH_PROJECT_URL**: Link to LangSmith project

## Deployment Workflow

### Automatic Deployment

The workflow automatically deploys to Vercel when:
- Changes are pushed to the `main` branch

### Manual Deployment

To manually trigger a deployment:

1. Go to the "Actions" tab in your GitHub repository
2. Select "Deploy to Vercel" from the workflows list
3. Click "Run workflow"
4. Select the branch (typically `main`)
5. Click "Run workflow" to start the deployment

## Vercel Configuration

The `vercel.json` file in the repository root configures the deployment:

- **Entry point**: `api/index.py` - Vercel serverless function entry point
- **Routes**: All requests are routed to the Flask application
- **Build**: Uses `@vercel/python` builder for Python applications

## Project Structure

```
.
├── api/
│   └── index.py          # Vercel entry point
├── app.py                # Flask application factory
├── vercel.json           # Vercel configuration
└── .github/
    └── workflows/
        └── vercel-deploy.yml  # Deployment workflow
```

## Troubleshooting

### Deployment Fails

1. **Check GitHub Secrets**: Ensure all required secrets are correctly configured
2. **Review Logs**: Check the GitHub Actions logs for specific error messages
3. **Vercel Dashboard**: Check the Vercel dashboard for deployment logs

### Application Doesn't Start

1. **Database Connection**: Verify DATABASE_URL is correctly set
2. **Dependencies**: Ensure all dependencies in `requirements.txt` are compatible
3. **Environment Variables**: Check that all required environment variables are set

### Database Issues

- Vercel serverless functions are stateless
- Use an external database (PostgreSQL recommended)
- SQLite is not recommended for production on Vercel

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Python Runtime](https://vercel.com/docs/runtimes#official-runtimes/python)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
