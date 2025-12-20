# Generating a Permanent WhatsApp Cloud API Access Token

## Contents
- [Generating a Permanent WhatsApp Cloud API Access Token](#generating-a-permanent-whatsapp-cloud-api-access-token)
  - [Contents](#contents)
  - [1. Introduction](#1-introduction)
    - [The Problem This Solves](#the-problem-this-solves)
    - [The Goal](#the-goal)
  - [2. Prerequisites](#2-prerequisites)
  - [3. Step-by-Step Guide](#3-step-by-step-guide)
    - [Step 3.1: Navigate to Business Settings](#step-31-navigate-to-business-settings)
    - [Step 3.2: Create a System User](#step-32-create-a-system-user)
    - [Step 3.3: Assign Assets to the System User](#step-33-assign-assets-to-the-system-user)
      - [Part A: Assign the App](#part-a-assign-the-app)
      - [Part B: Assign the WhatsApp Account](#part-b-assign-the-whatsapp-account)
    - [Step 3.4: Generate the Permanent Token](#step-34-generate-the-permanent-token)
  - [4. Using the New Token](#4-using-the-new-token)
  - [5. FAQ / Notes](#5-faq--notes)
---

## 1. Introduction

This document outlines the step-by-step process for generating a permanent, long-lived **System User Access Token** for the WhatsApp Cloud API.

### The Problem This Solves

The "Temporary Access Token" provided in the Meta App Dashboard is designed for initial testing only. It expires frequently (often within an hour, despite claiming 24 hours), causing `401 Unauthorized` errors and service interruptions. This makes it unsuitable for any stable development or production environment.

### The Goal

To create a permanent token that is tied to a "System User" within the Meta Business Account. This token has a 60-day lifespan and can be easily refreshed, making it the standard for production applications.

---

## 2. Prerequisites

Before you begin, ensure you have:

1.  A **Meta Business Account**. This is managed at [business.facebook.com](https://business.facebook.com).
2.  A **Meta Developer App** with the "WhatsApp Business" product added.
3.  Admin access to the Meta Business Account that owns the App.

---

## 3. Step-by-Step Guide

The entire process takes place within the **Meta Business Settings**.

### Step 3.1: Navigate to Business Settings

-   Go to [**business.facebook.com/settings**](https://business.facebook.com/settings).
-   Select the correct Business Account from the dropdown menu on the top left.

### Step 3.2: Create a System User

A System User is a machine account that can perform actions on behalf of your business.

1.  In the left-hand navigation menu, under **Users**, click on **System Users**.
2.  Click the blue **+ Add** button.
3.  **Accept** the non-discrimination policy if prompted.
4.  **System User Name:** Enter a descriptive name.
    -   *Example:* `whatsapp_agent_user`
5.  **System User Role:** Select **Admin**. This simplifies permissions.
6.  Click **Create system user**.

### Step 3.3: Assign Assets to the System User

The new user needs permission to access your App and your WhatsApp account.

1.  After creating the user, click the **Add Assets** button.
2.  A new window will open. You must assign **two** types of assets.

#### Part A: Assign the App

1.  In the "Select asset type" column on the left, select **Apps**.
2.  In the middle "Select assets" column, check the box next to your application (e.g., `fastapi-first-app`).
3.  In the right "Assign permissions" column, under **Full Control**, enable the toggle for **Manage app**.

#### Part B: Assign the WhatsApp Account

1.  In the "Select asset type" column on the left, select **WhatsApp accounts**.
2.  In the middle column, check the box next to your WhatsApp Business Account (e.g., `Test WhatsApp Business Account`).
3.  In the right column, under **Full Control**, enable the toggle for **Everything**.
4.  Click the blue **Save Changes** button. You will see a confirmation that the assets were assigned.

### Step 3.4: Generate the Permanent Token

This is the final step where you create the token string itself.

1.  You should now be back on the System Users page. With your `whatsapp_agent_user` selected, click the **Generate new token** button.
2.  A multi-step dialog will appear. Follow it carefully:
    -   **Step 1: Select app:** Choose your app (e.g., `fastapi-first-app`) from the dropdown menu. Click `Next`.
    -   **Step 2: Set expiration:** Choose **60 days**. Click `Next`.
    -   **Step 3: Assign permissions:** This is the most critical step. Check the boxes for the following two permissions:
        -   `whatsapp_business_management`
        -   `whatsapp_business_messaging`
    -   **Step 4: Done:** Click **Generate Token**.

3.  The dialog will now display your new token.

> **CRITICAL:** Copy this token immediately and store it securely. You will **NOT** be shown this token again.

---

## 4. Using the New Token

1.  Open your project's `.env` file.
2.  Find the `WHATSAPP_TOKEN` variable and replace its value with the new permanent token you just copied.

    ```env
    # .env file
    
    # ... other variables ...
    WHATSAPP_TOKEN="EAA...your_new_long_permanent_token_here..." # <-- PASTE THE NEW TOKEN HERE
    # ... other variables ...
    ```

3.  **Save** the `.env` file.
4.  **Restart your FastAPI server**. This is necessary for the application to load the updated environment variable.

Your application is now authenticated with a stable, long-lived token and will no longer suffer from frequent `401 Unauthorized` errors.

---

## 5. FAQ / Notes

-   **Why is my account called "Test WhatsApp Business Account"?**
    -   Meta automatically creates a free "Test" account and provides a test phone number when you add the WhatsApp product to a new app. This is for development purposes so you don't need to go through business verification immediately.
-   **What if I lose the token?**
    -   You cannot recover a lost token. You must go back to the System User page, click **Revoke tokens** to invalidate the old one, and then generate a completely new one by following Step 3.4 again.
