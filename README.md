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

## Stopping the Application

1.  Press `Ctrl + C` in Terminal 2 to stop the Cloudflare Tunnel.
2.  Press `Ctrl + C` in Terminal 1 to stop the FastAPI server.
