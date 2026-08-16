# GitHub Repository Setup Guide

To ensure this repository is as professional and secure as possible, please apply the following settings manually in your remote GitHub repository.

## 1. Branch Protection Rules

It's highly recommended to protect your primary branch (e.g., `main`).

1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Branches** > **Add branch protection rule**.
3. Under **Branch name pattern**, enter `main` (or your primary branch name).
4. Enable the following settings:
   - [x] **Require a pull request before merging**
     - [x] **Require approvals** (Set to at least 1 or 2 approvals depending on team size)
     - [x] **Dismiss stale pull request approvals when new commits are pushed**
   - [x] **Require status checks to pass before merging**
     - [x] **Require branches to be up to date before merging**
     - Search for and select the following status checks (they will appear after your first CI run):
       - `Lint & Test` (from the Backend CI workflow)
       - `Build & Verify` (from the Frontend CI workflow)
   - [x] **Require conversation resolution before merging**
   - [x] **Do not allow bypassing the above settings** (Optional, but recommended for strict compliance)

## 2. Pull Request Settings

Configure how pull requests are merged to maintain a clean Git history.

1. Navigate to **Settings** > **General**.
2. Scroll down to the **Pull Requests** section.
3. Enable the following settings:
   - [x] **Allow squash merging** (Recommended for keeping the main branch history clean)
   - [x] **Automatically delete head branches** (Keeps the repository clean after PRs are merged)

## 3. Dependabot Configuration

We have already included a `.github/dependabot.yml` file to automatically check for dependency updates.

1. Navigate to **Settings** > **Code security and analysis**.
2. Ensure **Dependabot alerts** and **Dependabot security updates** are **Enabled**.
3. (Optional) Enable **Secret scanning** to prevent accidentally committing API keys or credentials.

## 4. Issue and PR Templates

We have included standard issue templates and a pull request template in the `.github` folder. When creating a new issue or PR, GitHub will automatically suggest these templates to contributors to ensure quality reporting and feature requests.
