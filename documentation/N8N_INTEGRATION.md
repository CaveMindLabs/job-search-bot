# Sending Messages from n8n

This guide explains how to use the secure `/whatsapp/send` endpoint to send proactive WhatsApp messages directly from an n8n workflow. This allows you to trigger messages from any event in n8n (e.g., a new calendar event, a database update, a daily schedule) without needing an incoming message from a user.

This endpoint bypasses the LLM and memory services and directly uses the WhatsApp sending service.

## Prerequisites

1.  **Running Agent**: The FastAPI server must be running and publicly accessible via its URL (e.g., `https://whatsapp-agent.your_domain.com`).
2.  **API Key**: You must have the `INTERNAL_API_KEY` value from your project's `.env` file. This is the secret key used to authorize your n8n requests.

---

## Configuring the n8n "HTTP Request" Node

In your n8n workflow, add or select an "HTTP Request" node. Configure it with the following parameters.

### Step 1: Basic Request Setup

-   **Method**: `POST`
-   **URL**: Enter the full URL to the send endpoint.
    ```
    https://whatsapp-agent.your_domain.com/whatsapp/send
    ```

### Step 2: Authentication

This is the most critical step to ensure your requests are authorized.

1.  In the **Authentication** dropdown, select `Generic Credential Type`.
2.  In the **Generic Auth Type** dropdown that appears, select `Header Auth`.
3.  Click the **Header Auth** dropdown and select `+ Create new credential`.
4.  A window will pop up to configure the credential. Fill it out as follows:
    -   **Name**: `X-API-Key` (This **must** be exact).
    -   **Value**: Paste your `INTERNAL_API_KEY` from the `.env` file.
    -   **(Optional but Recommended)** Under **Allowed HTTP Request Domains**, select `Specific Domains` and enter `whatsapp-agent.your_domain.com` to ensure this key can only be used for this service.
5.  Click **Save**. The credential is now saved in n8n for future use.

> **Security Note:** This credential securely stores your API key within n8n. The `X-API-Key` header will be automatically added to every request made by this node.

### Step 3: Configuring the Message Body

This is where you define who to send the message to and what the message content is.

1.  Toggle the **Send Body** switch to ON.
2.  Set the **Body Content Type** to `JSON`.
3.  Ensure **Specify Body** is set to `Using Fields Below`. This provides an easy-to-use form.
4.  Under **Body Parameters**, you will add two parameters:
    -   **First Parameter (The Recipient):**
        -   **Name**: `to`
        -   **Value**: The recipient's WhatsApp ID, including the country code (e.g., `886985785785`). This can be a fixed value for testing or an n8n expression like `{{ $json.some_field }}` to pull it from previous nodes.
    -   **Second Parameter (The Message):**
        -   Click **Add Parameter**.
        -   **Name**: `text`
        -   **Value**: The message content you want to send. This can be fixed text or, more commonly, an n8n expression that uses data from previous nodes, like `{{ $json.body }}`.

### Step 4: (Optional) Add Headers

While n8n is usually smart enough to add the correct `Content-Type` header when sending JSON, it's good practice to add it explicitly.

1.  Toggle the **Send Headers** switch to ON.
2.  Click **Add Header**.
    -   **Name**: `Content-Type`
    -   **Value**: `application/json`

---

## Final Configuration Summary

When complete, your node settings should look like this:

-   **Method**: `POST`
-   **URL**: `https://whatsapp-agent.your_domain.com/whatsapp/send`
-   **Authentication**: `Generic Credential Type` -> `Header Auth` (using your saved credential)
-   **Send Body**: `ON`
    -   **Body Content Type**: `JSON`
    -   **Body Parameters**:
        -   `to`: (WhatsApp ID of the recipient)
        -   `text`: (The message to be sent)

## Testing the Node

Click the **Execute step** button in the top-right corner of the node's panel.

-   If successful, the node will turn green, and you should receive the message on the specified WhatsApp account.
-   If it fails, the node will turn red. Check the "Output" tab for error messages. A `403 Forbidden` error typically means the `INTERNAL_API_KEY` is incorrect. A `422 Unprocessable Entity` error means the body is missing the `to` or `text` field.
