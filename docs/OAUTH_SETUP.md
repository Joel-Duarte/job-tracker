# 📬 Job Tracker: Complete OAuth 2.0 & Mailbox Setup Guide

Job Tracker features an automated **Recruitment Mailbox Synchronization Engine** that monitors your inbox for job application confirmations, interview invitations, technical assessment links, and recruiter correspondence. Incoming messages are deduplicated, parsed for key metadata, and automatically linked to your application timeline and action items.

This guide walks you through connecting your email accounts using either **Modern OAuth 2.0** (recommended for Google Gmail and Microsoft Outlook / Office 365) or **App-Specific Passwords via IMAP SSL** (fast 30-second setup for Gmail, Apple iCloud, Fastmail, Yahoo, Zoho, and custom servers).

---

## 🏗️ Architecture & Security Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Recruitment Mailbox Synchronization                   │
│                                                                          │
│  [ Google Gmail (OAuth 2.0) ]  ──┐                                       │
│  [ Microsoft 365 (OAuth 2.0) ] ──┼──► [ FastAPI Backend ]                │
│  [ Standard IMAP (SSL / TLS) ] ──┘          │                            │
│                                             ▼                            │
│                        [ Fernet Decrypt at Runtime ]                     │
│                                             │                            │
│                                             ▼                            │
│                      [ RFC 822 Message-ID Deduplication ]                │
│                                             │                            │
│                                             ▼                            │
│                       [ AI Extraction & Intent Classifier ]              │
│                          ├── Interview Invites ──► Timeline & Action Item│
│                          ├── Application Conf. ──► Kanban Stage Update   │
│                          └── Status Changes    ──► Automated Audit Trail │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Security Guarantees:
- **Zero Third-Party Relays:** All email connections are established directly between your Job Tracker instance and your email provider. Your credentials and emails are never routed through external cloud intermediaries.
- **Encrypted at Rest:** All OAuth access tokens, refresh tokens, client secrets, and IMAP app passwords are encrypted in PostgreSQL using AES-128-CBC / PKCS7 with HMAC-SHA256 via symmetric **Fernet** cryptography.
- **Granular Scopes:** OAuth configurations only request the minimum required permissions to read recruitment emails and maintain offline session tokens.

---

## ⚖️ Authentication Choices: OAuth 2.0 vs. IMAP App Passwords

| Dimension | OAuth 2.0 (Recommended) | App-Specific Passwords (IMAP) |
| :--- | :--- | :--- |
| **Supported Providers** | Google Gmail, Google Workspace, Microsoft Outlook, Office 365 | Gmail, iCloud, Fastmail, Yahoo, Zoho, Proton Bridge, Custom IMAP |
| **Setup Duration** | 2–3 minutes (One-time Cloud Console setup) | 30 seconds (Generated in account security settings) |
| **Password Exposure** | **Zero:** Authenticates via secure token exchange | Uses a dedicated 16-character generated password |
| **Multi-Factor Auth (MFA)** | Native support with biometric/2FA web login | Seamlessly bypasses MFA requirements |
| **Token Refresh** | Automatic background refresh via `offline_access` | Permanent until revoked in account settings |
| **Best For** | Primary personal/work Gmail and Outlook accounts | Quick setup, iCloud, Fastmail, or custom corporate domains |

---

## 🔗 OAuth Callback / Redirect URIs Reference

When registering OAuth applications in Google Cloud Console or Microsoft Azure Entra ID, you must register the authorized redirect URIs corresponding to your Job Tracker environment:

| Environment | Provider | Authorized Redirect URI |
| :--- | :--- | :--- |
| **Development** (Vite Dev) | **Google Gmail** | `http://localhost:5173/api/v1/email_accounts/oauth/callback/google` |
| **Development** (Vite Dev) | **Microsoft Graph** | `http://localhost:5173/api/v1/email_accounts/oauth/callback/microsoft` |
| **Production** (Docker Prod) | **Google Gmail** | `http://localhost:4173/api/v1/email_accounts/oauth/callback/google` |
| **Production** (Docker Prod) | **Microsoft Graph** | `http://localhost:4173/api/v1/email_accounts/oauth/callback/microsoft` |

> [!TIP]
> **Pro-Tip:** You can register both the development (`:5173`) and production (`:4173`) URIs inside the same Google or Azure OAuth application so your credentials work seamlessly across both environments!

---

## 🔴 Part 1: Google Cloud Console (Gmail OAuth 2.0 Setup)

Follow these steps to create your own private Google Cloud OAuth 2.0 Client credentials.

### Step 1: Create a Google Cloud Project
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top navigation bar and click **"New Project"**.
3. Set the **Project Name** to `Job Tracker` (or any name you prefer) and click **"Create"**.
4. Select your newly created project from the top dropdown.

### Step 2: Enable the Gmail API
1. In the left sidebar navigation, go to **APIs & Services** ➜ **Library**.
2. Search for **"Gmail API"** in the search bar.
3. Click on **Gmail API** in the results and click the **"Enable"** button.

### Step 3: Configure the OAuth Consent Screen
1. In the left sidebar, navigate to **APIs & Services** ➜ **OAuth consent screen**.
2. Under **User Type**, select **"External"** and click **"Create"**.
3. Fill in the required **App Information**:
   - **App name:** `Job Tracker`
   - **User support email:** Select your Gmail address.
   - **Developer contact information:** Enter your email address.
   - Click **"Save and Continue"**.
4. **Scopes:**
   - Click **"Add or Remove Scopes"**.
   - Filter and select:
     - `https://mail.google.com/` (Read, compose, send, and permanently delete all your email from Gmail) OR
     - `https://www.googleapis.com/auth/gmail.readonly` (View your email messages and settings).
   - Click **"Update"** and then **"Save and Continue"**.
5. **Test Users:**
   - Since your app will remain in "Testing" mode (private to you), click **"+ Add Users"**.
   - Enter your personal Gmail address (the one you will connect to Job Tracker).
   - Click **"Add"** and then **"Save and Continue"**.
6. Review the summary and click **"Back to Dashboard"**.

### Step 4: Create OAuth 2.0 Client ID Credentials
1. In the left sidebar, click **APIs & Services** ➜ **Credentials**.
2. Click **"+ Create Credentials"** at the top and select **"OAuth client ID"**.
3. In the **Application type** dropdown, select **"Web application"**.
4. Set the **Name** to `Job Tracker Web Client`.
5. Under **Authorized redirect URIs**, click **"+ Add URI"** and add your endpoints:
   - Development:
     ```
     http://localhost:5173/api/v1/email_accounts/oauth/callback/google
     ```
   - Production:
     ```
     http://localhost:4173/api/v1/email_accounts/oauth/callback/google
     ```
   *(Add both so switching between development and production is effortless).*
6. Click **"Create"**.
7. A dialog will appear displaying your **Client ID** (e.g., `123456789-abc.apps.googleusercontent.com`) and **Client Secret** (e.g., `GOCSPX-abc123xyz`). Copy both values.

### Step 5: Authorize in Job Tracker
1. Open Job Tracker in your browser (`http://localhost:5173` or `http://localhost:4173`).
2. Navigate to **Settings** (`/settings`) ➜ **Connected Mailboxes** (or open the **Onboarding Wizard**).
3. Click **"Add Mailbox"** and select **"Gmail"** as the provider preset.
4. Toggle authentication method to **"OAuth 2.0"**.
5. Paste your **Client ID** and **Client Secret** into the respective fields.
6. Click **"Authorize with Google"**.
7. A Google login window will open. Select your test user account:
   - If Google displays *"Google hasn't verified this app"*, click **"Advanced"** ➜ **"Go to Job Tracker (unsafe)"**.
   - Check the boxes granting access to read your emails and click **"Continue"**.
8. You will be redirected back to Job Tracker with a success notification: `Gmail connected successfully via OAuth2`.

---

## 🔵 Part 2: Microsoft Entra ID / Azure Portal (Outlook & MS 365 OAuth 2.0 Setup)

Follow these steps to connect personal Outlook/Hotmail accounts or corporate Microsoft 365 / Entra ID work accounts.

### Step 1: Open Microsoft Entra / Azure Portal
1. Navigate to the [Microsoft Entra Admin Center](https://entra.microsoft.com/) or [Azure Portal](https://portal.azure.com/).
2. Sign in with your Microsoft personal or corporate admin account.

### Step 2: Register a New Application
1. In the left navigation menu, go to **Identity** ➜ **Applications** ➜ **App registrations** (or search for **App registrations** in the search bar).
2. Click **"+ New registration"**.
3. Configure the registration details:
   - **Name:** `Job Tracker`
   - **Supported account types:** Select:
     - **"Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)"**
     *(This ensures both personal @outlook.com/@hotmail.com and corporate @company.com accounts can authenticate).*
   - **Redirect URI (optional):**
     - Platform: **Web**
     - URI:
       ```
       http://localhost:5173/api/v1/email_accounts/oauth/callback/microsoft
       ```
       *(or `http://localhost:4173/api/v1/email_accounts/oauth/callback/microsoft` for production)*.
4. Click **"Register"**.

### Step 3: Add Additional Redirect URIs (Optional but Recommended)
1. On the application overview page, click on **Authentication** in the left sidebar.
2. Under the **Web** platform tile, click **"Add URI"**.
3. Ensure both URIs are listed:
   - `http://localhost:5173/api/v1/email_accounts/oauth/callback/microsoft`
   - `http://localhost:4173/api/v1/email_accounts/oauth/callback/microsoft`
4. Click **"Save"** at the top.

### Step 4: Generate a Client Secret
1. In the left sidebar, click **Certificates & secrets**.
2. Under the **Client secrets** tab, click **"+ New client secret"**.
3. Enter a description (e.g., `Job Tracker Secret`) and choose an expiration period (e.g., **24 months**).
4. Click **"Add"**.
5. > [!IMPORTANT]
   > **Immediately copy the string in the "Value" column** (NOT the Secret ID). Microsoft hides this value permanently once you navigate away from this page.

### Step 5: Configure API Permissions
1. In the left sidebar, click **API permissions**.
2. Click **"+ Add a permission"** and select **"Microsoft Graph"**.
3. Choose **"Delegated permissions"**.
4. Search for and check the following permissions:
   - `Mail.Read` (Read user mail)
   - `Mail.ReadWrite` (Read and write access to user mail)
   - `offline_access` (Maintain access to data you have given it access to / refresh tokens)
   - `User.Read` (Sign in and read user profile)
5. Click **"Add permissions"**.
6. *(Optional)* If using a corporate tenant and you have admin rights, click **"Grant admin consent for [Organization]"**.

### Step 6: Authorize in Job Tracker
1. From the App Registration **Overview** page, copy your **Application (client) ID**.
2. Open Job Tracker ➜ **Settings** ➜ **Connected Mailboxes** ➜ **Add Mailbox**.
3. Select **"Outlook / Microsoft 365"** as the provider preset.
4. Select **"OAuth 2.0"** as the authentication method.
5. Paste your **Application (client) ID** and **Client Secret (Value)**.
6. Click **"Authorize with Microsoft"**.
7. Log in with your Microsoft account, review permissions, and click **"Accept"**.
8. You will be redirected back to Job Tracker with your account connected and active.

---

## ⚡ Part 3: App-Specific Password Setup (The 30-Second Fast Path)

If you prefer not to register developer accounts in Google Cloud or Microsoft Azure, you can connect virtually any mailbox in 30 seconds using **IMAP with SSL/TLS** and an **App-Specific Password**.

App-specific passwords generate an isolated 16-character credential that bypasses Two-Factor Authentication without compromising your master account password.

---

### 1. Google Gmail (App Password)
1. Go to your [Google Account Security Settings](https://myaccount.google.com/security).
2. Under **"How you sign in to Google"**, verify that **2-Step Verification** is turned **ON**.
3. In the search bar at the top of Google Account, type **"App passwords"** and click the result.
4. Enter an app name: `Job Tracker` and click **"Create"**.
5. Google will display a 16-letter code (e.g., `abcd efgh ijkl mnop`).
6. In Job Tracker:
   - **Preset:** `Gmail`
   - **Auth Method:** `App Password (IMAP)`
   - **Username:** `yourname@gmail.com`
   - **App Password:** Paste the 16-character code (spaces are automatically stripped).
   - **Host / Port:** `imap.gmail.com` / `993` (SSL).
   - Click **"Test & Save"**.

---

### 2. Apple iCloud Mail
1. Sign in to [appleid.apple.com](https://appleid.apple.com/).
2. In the **Sign-In and Security** section, select **"App-Specific Passwords"**.
3. Click **"Generate an app-specific password"** (or click `+`).
4. Label it `Job Tracker` and click **"Create"**.
5. Enter your Apple ID password to confirm and copy the generated password.
6. In Job Tracker:
   - **Auth Method:** `App Password (IMAP)`
   - **Username:** `yourname@icloud.com` (or `@me.com`)
   - **App Password:** Paste your generated password.
   - **IMAP Host:** `imap.mail.me.com`
   - **IMAP Port:** `993` (SSL enabled).
   - Click **"Test & Save"**.

---

### 3. Fastmail
1. Log into your Fastmail account.
2. Go to **Settings** ➜ **Password & Security** ➜ **App Passwords**.
3. Click **"New App Password"**.
4. Name the password `Job Tracker` and set access to **Mail (Read-Only or Read/Write)**.
5. In Job Tracker:
   - **Username:** `yourname@fastmail.com`
   - **App Password:** Paste generated app password.
   - **IMAP Host:** `imap.fastmail.com`
   - **IMAP Port:** `993`.

---

### 4. Yahoo Mail / AOL
1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security).
2. Scroll to the bottom and click **"Generate app password"**.
3. Enter `Job Tracker` and click **"Generate"**.
4. In Job Tracker:
   - **Username:** `yourname@yahoo.com`
   - **App Password:** Paste generated 16-character password.
   - **IMAP Host:** `imap.mail.yahoo.com` (or `imap.aol.com`)
   - **IMAP Port:** `993`.

---

### 5. Zoho Mail
1. Log into [Zoho Accounts](https://accounts.zoho.com/).
2. Navigate to **Security** ➜ **App Passwords** ➜ **Generate New Password**.
3. Enter `Job Tracker` and copy the generated password.
4. In Job Tracker:
   - **Username:** `yourname@zohomail.com`
   - **App Password:** Paste generated password.
   - **IMAP Host:** `imap.zoho.com`
   - **IMAP Port:** `993`.

---

### 6. Proton Mail (via Proton Mail Bridge)
1. Open and unlock the **Proton Mail Bridge** desktop application on your host machine.
2. In Bridge, click **"Mailbox details"** to view your local port, username, and bridge password.
3. In Job Tracker:
   - **IMAP Host:** `host.docker.internal` (or `127.0.0.1` if running outside Docker).
   - **IMAP Port:** `1143` (STARTTLS / SSL as configured in Bridge).
   - **Username & App Password:** Paste credentials from Proton Bridge.

---

### 📋 IMAP Provider Quick Reference Table

| Provider | IMAP Host | Port | Security | Username Format |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gmail** | `imap.gmail.com` | `993` | SSL / TLS | `user@gmail.com` |
| **Microsoft Outlook** | `outlook.office365.com` | `993` | SSL / TLS | `user@outlook.com` |
| **Apple iCloud** | `imap.mail.me.com` | `993` | SSL / TLS | `user@icloud.com` |
| **Fastmail** | `imap.fastmail.com` | `993` | SSL / TLS | `user@fastmail.com` |
| **Yahoo Mail** | `imap.mail.yahoo.com` | `993` | SSL / TLS | `user@yahoo.com` |
| **Zoho Mail** | `imap.zoho.com` | `993` | SSL / TLS | `user@zohomail.com` |
| **Proton Mail Bridge**| `host.docker.internal`| `1143`| STARTTLS | `user@proton.me` |

---

## ⏰ Part 4: Mailbox Synchronization Schedules & Automation

Job Tracker allows you to fine-tune how frequently each connected mailbox is scanned for recruitment emails.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      Sync Scheduling Configuration                       │
│                                                                          │
│  [ Interval Mode ]         Every [ 1h ▼ ]                                │
│                            Options: 15m, 30m, 1h, 6h, 12h, 24h, Manual   │
│                                                                          │
│  [ Daily Sweep Mode ]      Run Daily at [ 09:00 ▼ ] UTC                  │
│                                                                          │
│  [ Target Folder ]         Folder: [ INBOX                      ▼ ]      │
│                            Custom: [ [Gmail]/All Mail, Careers, etc. ]   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1. Polling Intervals
Configure automatic periodic background checks:
- **`15m` / `30m`:** Recommended during active interview rounds when rapid notifications for scheduling invites are critical.
- **`1h` (Default):** Optimal balance between timely status updates and minimal server resource utilization.
- **`6h` / `12h` / `24h`:** Ideal for passive tracking or secondary mailboxes.
- **`MANUAL`:** Disables automated polling. You can trigger syncs on demand by clicking the **"Sync Now"** icon in the UI.

### 2. Time-of-Day Scheduled Sweeps
For candidates who prefer scheduled batch updates:
- Set **Sync Schedule Time** (e.g., `09:00` or `18:00`).
- Select specific days (e.g., `MON` through `FRI` or all week).
- Job Tracker will execute an automated comprehensive sync at your designated local time.

### 3. Folder Selection & Label Filtering
By default, Job Tracker scans the standard `INBOX`. You can customize the target folder to monitor specific filters:
- **Gmail:** `INBOX`, `[Gmail]/All Mail`, `[Gmail]/Starred`, or custom labels like `Jobs` or `Applications`.
- **Outlook:** `INBOX`, `Archive`, or custom subfolders.
- **Custom IMAP:** Any valid IMAP folder string returned by your mail server.

---

## 🔍 Part 5: Diagnostics & Live Telemetry

You can verify and monitor all email synchronization activities in real time via the **Diagnostics Dashboard** (`/diagnostics`):

1. Navigate to **Diagnostics** in the sidebar.
2. Click the **"Email Sync"** filter tab.
3. Every sync run records:
   - **Operation Name:** `imap_sync_inbox`, `gmail_oauth_fetch`, or `msgraph_oauth_fetch`.
   - **Execution Duration:** Response latency in milliseconds/seconds.
   - **Extracted Messages:** Number of new emails discovered, message IDs processed, and deduplication skips.
   - **Errors & Tracebacks:** Full stack traces if authentication fails, tokens expire, or servers time out.

---

## ❓ Frequently Asked Questions (FAQ)

### Q: What happens if an OAuth token expires?
**A:** Job Tracker automatically requests a new access token using your encrypted `refresh_token` before every sync operation. As long as your OAuth app remains authorized, you never have to re-login manually.

### Q: Does Job Tracker delete or modify my emails?
**A:** **No.** Job Tracker operates in read-only mode for email ingestion. It inspects headers and message bodies to extract status updates and leaves your emails completely intact in your provider's inbox.

### Q: How does Job Tracker avoid duplicate applications?
**A:** Every email ingested is hashed by its standard RFC 822 `Message-ID` header. If an email is retrieved multiple times across different sync intervals, Job Tracker identifies the duplicate hash and skips re-processing instantly.

### Q: Can I connect multiple mailboxes at once?
**A:** **Yes.** You can connect multiple accounts simultaneously (e.g., a personal Gmail via OAuth2, a University inbox via IMAP, and a consulting Outlook account via Microsoft Graph). Each account operates on its own independent sync schedule and folder setting.

### Q: How do I revoke Job Tracker's access?
**A:** 
- **In Job Tracker:** Simply delete the mailbox entry in **Settings** ➜ **Connected Mailboxes**.
- **In Google:** Go to [Google Account Permissions](https://myaccount.google.com/connections) ➜ Select **Job Tracker** ➜ Click **"Remove Access"**.
- **In Microsoft:** Go to [Microsoft Account App Permissions](https://account.live.com/consent/Manage) ➜ Select **Job Tracker** ➜ Click **"Remove permissions"**.
