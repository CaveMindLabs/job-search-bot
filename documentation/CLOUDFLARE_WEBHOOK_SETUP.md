# Cloudflare Tunnel Setup for the WhatsApp Webhook

This document details the process of creating a persistent, public-facing URL for the local FastAPI server using a Cloudflare Tunnel. This setup replaces temporary solutions like ngrok, providing a stable endpoint for development and testing that never changes.

## Goal

To expose the local FastAPI server running on `http://localhost:8000` to the public internet via a permanent subdomain, `https://whatsapp-agent.cavemindlabs.com`, so it can receive webhooks from Meta's WhatsApp Cloud API.

---

## One-Time Infrastructure Setup

These steps only need to be performed once to create and configure the tunnel.

### Step 1: Install and Authenticate `cloudflared` CLI

Ensure the `cloudflared` command-line tool is installed and authenticated with your Cloudflare account.

```bash
# Check version (and if it's installed)
cloudflared --version

# If not yet authenticated, run this once to link to your account
cloudflared tunnel login
```

### Step 2: Create a Named Tunnel

Create a persistent, named tunnel. This reserves a connection path on Cloudflare's network.

```bash
cloudflared tunnel create whatsapp-agent-tunnel
```

This command will output the tunnel's UUID and create a corresponding credentials file in `C:\Users\<Your-Username>\.cloudflared\`. This file is the secret key to your tunnel.

### Step 3: Configure the Project

We will store the tunnel's configuration locally within this project for portability and to keep it self-contained.

1.  **Create a local config directory:**
    ```bash
    # From the project root
    mkdir .cloudflared
    ```

2.  **Copy the credentials file into the project:**
    Find the credentials file created in Step 2 (e.g., `4f63f9cf-....json`) and copy it into the project, renaming it for simplicity.
    ```bash
    # Replace the UUID with the one generated for you
    copy C:\Users\<Your-Username>\.cloudflared\<tunnel-uuid>.json .\.cloudflared\cred.json
    ```

> **IMPORTANT: Update `.gitignore`**
>
> Add the `.cloudflared` directory to your `.gitignore` file to prevent committing your secret tunnel credentials to version control.
>
> ```gitignore
> # .gitignore
>
> # Cloudflare Tunnel credentials
> /.cloudflared
> `

3.  **Create the local `config.yml` file:**
    Create a file named `config.yml` inside the `.\.cloudflared` directory and add the following content.

    ```yaml
    # The name of the tunnel to run
    tunnel: whatsapp-agent-tunnel

    # The full, absolute path to the credentials file.
    # Using a full path with single quotes is the most robust method on Windows,
    # as it prevents issues with spaces and special characters like backslashes.
    credentials-file: 'C:\Users\gilda\OneDrive\Documents\My_Projects\AI_Based_Projects\whatsapp-fastapi-agent\.cloudflared\cred.json'

    # Ingress rules define how traffic is routed
    ingress:
      # Rule 1: Route traffic from your public hostname to your local server
      - hostname: whatsapp-agent.cavemindlabs.com
        service: http://localhost:8000
    
      # Rule 2: A mandatory catch-all that returns a 404 for any other traffic
      - service: http_status:404
    ```

### Step 4: Route DNS to the Tunnel

Create a `CNAME` record in your Cloudflare DNS to point your public subdomain to the tunnel.

```bash
cloudflared tunnel route dns whatsapp-agent-tunnel whatsapp-agent.cavemindlabs.com
```

### Step 5: Configure the Meta Webhook (Final Connection)

This is the final step to link WhatsApp to your new endpoint. This only needs to be done once.

1.  Go to your **Meta App Dashboard** (`developers.facebook.com`).
2.  Navigate to **WhatsApp -> Configuration**.
3.  Click **Edit** on the Webhook section.
4.  Set the following values:
    *   **Callback URL**: `https://whatsapp-agent.cavemindlabs.com/whatsapp/webhook`
    *   **Verify token**: The secret token from your project's `.env` file.
5.  Click **Verify and save**. You should see a `GET` request in your running terminals, confirming the connection is successful.

---

## Daily Development Workflow

To run the application, you need two separate terminals.

### Terminal 1: Start the FastAPI Server

This terminal runs the Python application.

```bash
# Navigate to the project directory
cd C:\Users\gilda\OneDrive\Documents\My_Projects\AI_Based_Projects\whatsapp-fastapi-agent

# Activate the conda environment
conda activate whatsapp-agent

# Start the server with hot-reloading
uvicorn main:app --reload
```

### Terminal 2: Start the Cloudflare Tunnel

This terminal runs the `cloudflared` client, which connects to Cloudflare and forwards traffic to your FastAPI server.

```bash
# Navigate to the project directory
cd C:\Users\gilda\OneDrive\Documents\My_Projects\AI_Based_Projects\whatsapp-fastapi-agent

# Run the tunnel using the project's local config file
cloudflared tunnel --config .\.cloudflared\config.yml run whatsapp-agent-tunnel
```

---

## Key Lessons & Troubleshooting

*   **YAML Path Handling:** The `credentials-file` path in `config.yml` can be tricky.
    *   Unquoted paths work *only if they have no spaces or special characters*.
    *   Double-quoted paths (`"C:\..."`) will fail because the backslash (`\`) is an escape character in YAML.
    *   **The safest method is to use single quotes (`'C:\...'`) which treats the path as a literal string.**
*   **Credentials File Not Found:** If you get this error, it's almost always an issue with the path in `config.yml`. Ensure it's the full, absolute path to the `cred.json` file inside your project.
*   **Webhook Verification Fails:**
    1.  Ensure both the FastAPI server and the Cloudflare Tunnel are running.
    2.  Double-check for typos in the Callback URL in the Meta dashboard.
    3.  Confirm the `VERIFY_TOKEN` in your `.env` file exactly matches the one you entered in the Meta dashboard.
