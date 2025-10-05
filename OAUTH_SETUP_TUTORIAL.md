# Tastytrade OAuth Setup Tutorial

This tutorial will guide you through the complete process of setting up API access for Tastytrade, from creating an OAuth grant to running the setup script.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Creating an OAuth Grant](#creating-an-oauth-grant)
3. [Obtaining Client ID and Client Secret](#obtaining-client-id-and-client-secret)
4. [Running the Setup Script](#running-the-setup-script)
5. [What Gets Created](#what-gets-created)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Prerequisites

Before you begin, make sure you have:

- ✅ An active Tastytrade account
- ✅ A web browser

> **🔒 Security Note**: This application only requires **"Read"** permission to access market data and account information. You should NOT grant "Trade" or other permissions. Only granting Read access ensures the application cannot place or modify trades on your account.

---

## Creating an OAuth Grant

### Step 1: Log in to Tastytrade Web Trading Platform

1. Open your web browser and navigate to [https://trade.tastytrade.com/](https://trade.tastytrade.com/)

2. Log in with your Tastytrade credentials

### Step 2: Navigate to API Settings

1. After logging in, look for **"Manage"** in the top navigation menu or account section

2. Click on **"Manage"** then select **"My Profile"**

3. In the profile menu, find and click on **"API"**

### Step 3: Enable API Access

1. Look for **"Open API Access"** section

2. Click on **"Opt in"** if you haven't already enabled API access
   - This grants your account permission to use the API
   - You only need to do this once per account

### Step 4: Create a New Grant

1. Once API access is enabled, look for a button or link to **"Create Grant"**

2. Click **"Create Grant"** to start creating a new OAuth application

3. You'll be presented with a form to fill out:

   **Permissions/Scopes:**
   - Select **"Read"** only
   - ✅ **Read** - View account information, positions, orders
   
   > **⚠️ IMPORTANT**: For the SPX Option Chain Fetcher, you only need **"Read"** permission. Do NOT select "Trade" or other permissions unless specifically instructed. Only granting Read access is the safest option and is all that's required for this application to work.

   **Redirect URI:**
   - **IMPORTANT**: Enter exactly: `http://localhost:8000`
   - This is required for the OAuth flow to work properly
   - Do NOT use HTTPS - use HTTP
   - Do NOT change the port number
   - Do NOT add a trailing slash

   **Application Name:** (if asked)
   - Enter a descriptive name for your reference
   - Example: "SPX Option Chain Fetcher" or "My Trading Bot"

4. Click **"Create"** or **"Submit"** to create the grant

---

## Obtaining Client ID and Client Secret

### Step 5: Copy Your Client ID and Client Secret

After creating the grant, you'll be shown your **Client ID** and **Client Secret**:

⚠️ **CRITICAL**: The **Client Secret** is only shown ONCE. You cannot retrieve it later!

1. You should see a screen displaying:
   ```
   Client ID: a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
   Client Secret: s3cr3t-t0k3n-th4t-y0u-mu5t-s4v3-n0w
   ```

2. **Copy both values immediately** and save them somewhere safe temporarily:
   - **Copy the Client ID** - you'll need this when running the script
   - **Copy the Client Secret** - you'll need this when running the script
   - You can paste them in a temporary text file (just for the next few minutes)
   - Or better yet, save them directly to a password manager

3. If you lose the Client Secret:
   - You'll need to delete this grant and create a new one
   - The Client Secret cannot be retrieved or regenerated

### Where to Find Your Credentials Later

If you need to find your **Client ID** again (but NOT the secret):

1. Log in to the Tastytrade web trading platform
2. Navigate to **Manage** → **My Profile** → **API**
3. Find your grant in the list of OAuth applications
4. The Client ID will be visible
5. The Client Secret will be hidden (shown as `••••••••`)
6. If you need the Client Secret again, you must create a new grant

---

## Running the Setup Script

Now that you have your OAuth grant set up, let's generate and store your refresh token.

### Step 6: Run the Setup Script

Double-click the script file named `get_refresh_token.py`.

### Step 7: Complete the Setup Process

When you run the script, here's what will happen:

1. **Browser Opens Automatically:**
   - A browser window/tab will open showing an authorization page
   - The web address will be something like `http://localhost:8000`

2. **Enter Your Application Credentials:**
   - You'll see a form asking for:
     - **Client ID** → Paste the Client ID you copied earlier
     - **Client Secret** → Paste the Client Secret you copied earlier
   - Click **"Connect"** or **"Submit"**

3. **Log in to Tastytrade:**
   - You may be prompted to log in to your Tastytrade account
   - Use your normal Tastytrade username and password
   - This is NOT the Client ID/Secret - this is your trading account login

4. **Authorize the Application:**
   - You'll see a screen asking you to authorize your application
   - It will show which scopes (permissions) you're granting
   - Click **"Authorize"** or **"Allow"**

5. **Refresh Token Displayed:**
   - After successful authorization, you should see your refresh token displayed
   - It looks something like: `refresh_token_abc123def456ghi789...`

### Step 8: Enter Your Credentials

In the command window that appears, you'll be prompted to enter information:

1. **Paste your Client ID** when asked and press Enter

2. **Paste your Client Secret** when asked and press Enter

### Step 9: Setup Complete!

If everything worked correctly, you should see a success message. Your credentials have been saved securely.

---

## What Gets Created

After running the setup script, a file named `.secrets` will be created in your project folder. This file contains:

- Your Client ID
- Your Client Secret  
- Your Refresh Token

**Important**: This file is automatically protected. Keep it safe and never share it with anyone.

---

## Troubleshooting

### Issue: Browser didn't open automatically

**Solution:**
- Look at the command window - there should be a web address shown
- Copy and paste that address into your web browser manually
- Continue with the setup process

### Issue: "Redirect URI mismatch" error

**Solution:**
- Make sure you entered **exactly** `http://localhost:8000` in the Redirect URI field when creating the grant
- Check for typos and make sure there's no extra space or slash at the end
- If needed, delete the grant and create a new one with the correct Redirect URI

### Issue: Lost my Client Secret

**Solution:**
- Unfortunately, the Client Secret cannot be viewed again after you close the page
- You'll need to delete your existing grant and create a new one
- Go to **Manage → My Profile → API** in the Tastytrade web platform
- Delete the old grant and create a new one
- This time, save the Client Secret immediately!

### Issue: Script won't run or shows errors

**Solution:**
- Make sure you have all the required software installed
- Contact your system administrator or the person who set up the application for assistance

---

## Security Best Practices

### ✅ DO:

1. **Keep your `.secrets` file secure**
   - Never share it with anyone
   - Never post it online or in chat messages
   - The file is automatically protected

2. **Save your credentials safely**
   - Store Client ID and Client Secret in a password manager (like 1Password, LastPass, or Bitwarden)
   - Keep a secure backup

3. **Only grant necessary permissions**
   - The SPX Option Chain Fetcher only needs "Read" permission
   - Never grant "Trade" or other permissions unless absolutely required
   - More permissions = more risk if credentials are compromised

4. **Review your access periodically**
   - Check your OAuth grants in Tastytrade occasionally
   - Delete grants you no longer use

### ❌ DON'T:

1. **Never share your credentials**
   - Don't email or message your Client Secret or Refresh Token
   - Don't share your screen when the `.secrets` file is visible

2. **Never post online**
   - Don't post your credentials in forums, Discord, Slack, or any public place
   - Don't include them in screenshots

3. **Keep it private**
   - These credentials give full access to your Tastytrade account
   - Treat them like your password

---

## Quick Reference Guide

Save this for quick access:

| What You Need | Where to Find It |
|---------------|------------------|
| **Tastytrade Login** | https://trade.tastytrade.com/ |
| **Create OAuth Grant** | Manage → My Profile → API → Create Grant |
| **Redirect URI** | `http://localhost:8000` |
| **Required Permission** | Select: **Read ONLY** (do not select Trade) |
| **Setup Script** | Double-click `get_refresh_token.py` |
| **Credentials Saved In** | `.secrets` file |

---

## Summary

Congratulations! 🎉 You've successfully set up your Tastytrade API access!

You've completed:
- ✅ Created a Tastytrade OAuth grant
- ✅ Obtained your Client ID and Client Secret
- ✅ Generated a refresh token
- ✅ Saved everything securely in `.secrets` file

**Good news**: The refresh token never expires, so you only need to do this setup once!

If you need help or encounter issues not covered in this tutorial, contact Tastytrade support or the person who provided you with this application.

---

**Last Updated**: October 2025
