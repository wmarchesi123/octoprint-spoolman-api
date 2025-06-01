# OctoPrint-Spoolman-API

This plugin provides a REST API for external applications to interact with the [OctoPrint-Spoolman](https://github.com/Donkie/Spoolman-Octoprint) plugin. It enables programmatic selection of spools, making it possible for applications like barcode scanners, NFC readers, or web interfaces to automatically update which spool is loaded in OctoPrint.

## Overview

The OctoPrint-Spoolman-API plugin acts as a bridge between external applications and the OctoPrint-Spoolman plugin. It exposes REST API endpoints that allow you to:

- Set which spool is currently loaded for each tool
- Get the currently selected spool for a tool
- List available tools/extruders

This is particularly useful for automated spool management systems where you want to update OctoPrint's spool selection without using the web interface.

## Requirements

- **OctoPrint** 1.4.0 or newer
- **Python** 3.6 or newer
- **[OctoPrint-Spoolman](https://github.com/Donkie/Spoolman-Octoprint)** plugin must be installed and configured
- **[Spoolman](https://github.com/Donkie/Spoolman)** server must be running and accessible

## Installation

**⚠️ Note**: This plugin is not available in the OctoPrint Plugin Repository and must be installed manually.

### Install via Plugin Manager

1. Open OctoPrint Settings
2. Navigate to **Plugin Manager** → **Get More**
3. Enter the URL:

   ```txt
   https://github.com/wmarchesi123/octoprint-spoolman-api/archive/main.zip
   ```

4. Click **Install**
5. Restart OctoPrint when prompted

### Install via Command Line

SSH into your OctoPrint server and run:

```bash
~/oprint/bin/pip install https://github.com/wmarchesi123/octoprint-spoolman-api/archive/main.zip
```

Then restart OctoPrint:

```bash
sudo service octoprint restart
```

### Install via Docker

If running OctoPrint in Docker, install inside the container:

```bash
docker exec -it <container_name> /opt/octoprint/bin/pip install https://github.com/wmarchesi123/octoprint-spoolman-api/archive/main.zip
```

## Configuration

This plugin requires no configuration. It automatically detects and integrates with the OctoPrint-Spoolman plugin if it's installed.

## API Documentation

All API endpoints are available at `/api/plugin/spoolman_api`

### Authentication

Use your OctoPrint API key in the `X-Api-Key` header for all requests:

```bash
X-Api-Key: YOUR_OCTOPRINT_API_KEY
```

### Endpoints

#### Set Current Spool

Sets which spool is currently loaded for a specific tool.

**Request:**

```http
POST /api/plugin/spoolman_api
Content-Type: application/json
X-Api-Key: YOUR_API_KEY

{
  "command": "set_spool",
  "spool_id": "123",
  "tool": 0
}
```

**Parameters:**

- `command` (required): Must be `"set_spool"`
- `spool_id` (required): The ID of the spool from Spoolman
- `tool` (optional): Tool/extruder index (default: 0)

**Response:**

```json
{
  "success": true,
  "spool_id": "123",
  "tool": 0,
  "message": "Spool 123 set for tool 0"
}
```

#### Get Current Spool

Retrieves the currently selected spool for a specific tool.

**Request:**

```http
POST /api/plugin/spoolman_api
Content-Type: application/json
X-Api-Key: YOUR_API_KEY

{
  "command": "get_current_spool",
  "tool": 0
}
```

**Parameters:**

- `command` (required): Must be `"get_current_spool"`
- `tool` (optional): Tool/extruder index (default: 0)

**Response:**

```json
{
  "success": true,
  "tool": 0,
  "spool_id": "123"
}
```

If no spool is selected, `spool_id` will be `null`.

#### List Tools

Lists all available tools/extruders.

**Request:**

```http
POST /api/plugin/spoolman_api
Content-Type: application/json
X-Api-Key: YOUR_API_KEY

{
  "command": "list_tools"
}
```

**Response:**

```json
{
  "success": true,
  "tools": [
    {"id": 0, "name": "Tool 0"},
    {"id": 1, "name": "Tool 1"}
  ]
}
```

## Usage Examples

### Bash/cURL

Set spool 42 for tool 0:

```bash
curl -X POST http://octoprint.local/api/plugin/spoolman_api \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{"command": "set_spool", "spool_id": "42", "tool": 0}'
```

Get current spool:

```bash
curl -X POST http://octoprint.local/api/plugin/spoolman_api \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{"command": "get_current_spool", "tool": 0}'
```

### Python

```python
import requests

# Set spool
response = requests.post(
    'http://octoprint.local/api/plugin/spoolman_api',
    headers={
        'X-Api-Key': 'YOUR_API_KEY',
        'Content-Type': 'application/json'
    },
    json={
        'command': 'set_spool',
        'spool_id': '42',
        'tool': 0
    }
)

if response.json()['success']:
    print("Spool set successfully!")
```

### JavaScript

```javascript
fetch('http://octoprint.local/api/plugin/spoolman_api', {
    method: 'POST',
    headers: {
        'X-Api-Key': 'YOUR_API_KEY',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        command: 'set_spool',
        spool_id: '42',
        tool: 0
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Spool set successfully!');
    }
});
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

func setActiveSpool(spoolID string, tool int) error {
    payload := map[string]interface{}{
        "command":  "set_spool",
        "spool_id": spoolID,
        "tool":     tool,
    }
    
    jsonData, err := json.Marshal(payload)
    if err != nil {
        return err
    }
    
    req, err := http.NewRequest("POST", "http://octoprint.local/api/plugin/spoolman_api", bytes.NewBuffer(jsonData))
    if err != nil {
        return err
    }
    
    req.Header.Set("X-Api-Key", "YOUR_API_KEY")
    req.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    var result map[string]interface{}
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return err
    }
    
    if success, ok := result["success"].(bool); ok && success {
        fmt.Println("Spool set successfully!")
    }
    
    return nil
}
```

## Troubleshooting

### API Returns 404

The plugin is not installed correctly. Verify installation:

1. Check Plugin Manager for "Spoolman API"
2. Check logs: Settings → Logs → octoprint.log
3. Reinstall the plugin

### "Spoolman plugin not available" Error

The OctoPrint-Spoolman plugin is not installed or not loaded:

1. Install [OctoPrint-Spoolman](https://github.com/Donkie/Spoolman-Octoprint) first
2. Restart OctoPrint
3. Verify Spoolman plugin is enabled in Plugin Manager

### "No command specified" Error

This actually indicates the plugin is working! Check your request:

- Ensure you're sending JSON with `Content-Type: application/json`
- Verify the `command` field is included in your request body
- Check that you're using POST, not GET

### Permission Denied

Your API key may not have sufficient permissions:

1. Generate a new API key with full permissions
2. Or ensure your current key has "Plugin:Spoolman" permissions

## Use Cases

This plugin is designed for:

- **Spool Scanner Systems**: QR code or NFC-based spool identification systems
- **Automation Scripts**: Automatically switch spools based on print jobs
- **Multi-Printer Management**: Centralized spool assignment across multiple printers
- **Mobile Apps**: Custom interfaces for spool management
- **Integration Tools**: Connect OctoPrint with other workshop management systems

## Known Limitations

- Requires OctoPrint-Spoolman plugin to be installed
- Does not provide direct access to Spoolman server data
- Cannot create or modify spool information (only selection)

## License

This plugin is licensed under the Apache License 2.0. See [LICENSE.md](LICENSE.md) for details.

## Acknowledgments

- [Donkie](https://github.com/Donkie) for creating the Spoolman ecosystem
