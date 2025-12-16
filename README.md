# WhatsApp FastAPI Agent

This project runs a FastAPI server to act as a webhook for the WhatsApp Cloud API, process messages with an LLM, and send replies.

## Prerequisites

1.  **Conda Environment**: Ensure the `whatsapp-agent` conda environment is created and activated.
2.  **Environment Variables**: A `.env` file must be present in the root directory with the required API keys and tokens.
3.  **Cloudflare Tunnel**: This project uses a project-local Cloudflare Tunnel configuration located in the `.cloudflared` directory.

---

## Running the Application (Local Development)

You will need two separate terminals open to run the application.

### Terminal 1: Start the FastAPI Server

This terminal runs the Python web application using `uvicorn`.

```bash
# Navigate to the project directory
cd path\to\whatsapp-fastapi-agent

# Activate the conda environment
conda activate whatsapp-agent

# Start the server
uvicorn main:app --reload
```

The server will be running on `http://127.0.0.1:8000`.

### Terminal 2: Start the Cloudflare Tunnel

This terminal creates a secure, public-facing URL that forwards traffic to your local FastAPI server.

```bash
# Navigate to the project directory
cd path\to\whatsapp-fastapi-agent

# Run the tunnel using the project's config file
cloudflared tunnel --config .\.cloudflared\config.yml run whatsapp-agent-tunnel
```

The application will now be publicly accessible at `https://whatsapp-agent.cavemindlabs.com`.

---

## Testing the Webhook Locally

You can test the entire application flow without sending a real WhatsApp message by sending a simulated webhook request from your local machine. This is extremely useful for debugging.

For this test, the FastAPI server must be running (Terminal 1), but the Cloudflare Tunnel is not required.

### Step 1: Prepare the Test Payload

Ensure you have a `test_payload.json` file in the root of your project with the following content.

> **Important:** Replace `YOUR_REAL_WA_ID` with your own personal WhatsApp number (the one verified for testing in the Meta dashboard), including the country code. This ensures the API call to send a reply succeeds.

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "123456789",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "15550001234",
              "phone_number_id": "YOUR_BUSINESS_PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": { "name": "Local Test User" },
                "wa_id": "YOUR_REAL_WA_ID"
              }
            ],
            "messages": [
              {
                "from": "YOUR_REAL_WA_ID",
                "id": "wamid.your_test_message_id",
                "timestamp": "1701108242",
                "text": { "body": "Hello from a local test!" },
                "type": "text"
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

### Step 2: Send the Test Request

Open a **third terminal** (PowerShell is recommended on Windows) and run the following command to send the payload to your local server.

```powershell
# Ensure you are in the project's root directory
cd path\to\whatsapp-fastapi-agent
# Then run:
$headers = @{
    "Content-Type" = "application/json"
}

$body = Get-Content -Raw -Path .\test_payload.json

Invoke-WebRequest -Uri http://127.0.0.1:8000/whatsapp/webhook -Method POST -Headers $headers -Body $body
```

### Step 3: Check the Logs

If the test is successful, you will see a `200 OK` response in your PowerShell terminal. More importantly, in your FastAPI server terminal (Terminal 1), you should see a series of logs confirming the entire flow:

1.  `INFO - Received webhook payload...`
2.  `INFO - Calling OpenAI for user...`
3.  `INFO - Successfully generated reply for user...`
4.  `INFO - Sending message to ...`
5.  `INFO - Message sent successfully to ...`
6.  `INFO - Logged message for user ...`

This confirms that the application logic is working correctly from end to end.

---

## Stopping the Application

1.  Press `Ctrl + C` in Terminal 2 to stop the Cloudflare Tunnel.
2.  Press `Ctrl + C` in Terminal 1 to stop the FastAPI server.



## Testing the Model List Endpoint
$headers = @{
    "X-API-Key" = "EIqXHvdJmbF+Fetu4VaqXymgK+PoXBOd68mduJRQMp8="
}
Invoke-WebRequest -Uri https://whatsapp-agent.cavemindlabs.com/whatsapp/models -Method GET -Headers $headers -UseBasicParsing

Invoke-WebRequest -Uri http://127.0.0.1:8000/whatsapp/models -Method GET -Headers $headers -UseBasicParsing
