"""
ESP32 Configuration Helper — Generate firmware code snippets for auto-connect.

This module helps configure ESP32 to:
1. Connect to WiFi automatically
2. Discover AEGIS1 bridge server via mDNS
3. Auto-connect to WebSocket endpoint
"""

# ============================================================================
# ESP32 FIRMWARE CODE SNIPPET - WiFi + mDNS Auto-Discovery
# ============================================================================
# Add this to your test_5_openclaw_voice.cpp or similar firmware
#
# Requirements:
# - ESP32 with WiFi + mDNS support
# - Arduino IDE with ESP32 board package
# - Libraries: WiFi.h, esp_mdns.h, WebSocketsClient.h
#
# Usage:
# 1. Copy the code below into your firmware
# 2. Update WiFi SSID and password
# 3. Flash to ESP32
# 4. Server will auto-discover and connect!
# ============================================================================

ESP32_FIRMWARE_SNIPPET = '''
#include <WiFi.h>
#include <esp_mdns.h>
#include <WebSocketsClient.h>
#include "driver/i2s.h"

// ============= CONFIGURATION =============
const char* WIFI_SSID = "your-wifi-ssid";        // Change this
const char* WIFI_PASSWORD = "your-wifi-password"; // Change this
const char* MDNS_SERVICE_NAME = "aegis1";        // Match MDNS_SERVICE_NAME in .env
const int SERVER_PORT = 8000;                    // Match BRIDGE_PORT in .env

// ============= GLOBAL STATE =============
String serverIP;
int serverPort = SERVER_PORT;
WebSocketsClient webSocket;

// ============= SETUP =============
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\\n\\nESP32 AEGIS1 Pendant Startup");
    Serial.println("============================");
    
    // 1. Connect to WiFi
    Serial.printf("Connecting to WiFi: %s...\\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("✓ Connected! IP: %s\\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("✗ WiFi connection failed");
        return;
    }
    
    // 2. Initialize mDNS
    Serial.println("Initializing mDNS...");
    mdns_init();
    mdns_hostname_set("esp32-aegis1");
    
    // 3. Discover AEGIS1 server via mDNS
    Serial.printf("Discovering %s service via mDNS...\\n", MDNS_SERVICE_NAME);
    
    mdns_result_t* results = mdns_query_ptr(
        "_tcp",                      // Service type: _tcp
        MDNS_SERVICE_NAME,           // Service name
        2000,                        // Timeout: 2 seconds
        10                           // Max results
    );
    
    if (results) {
        mdns_result_t* r = results;
        serverIP = r->addr->u_addr.ip4.addr;
        serverPort = r->port;
        Serial.printf("✓ Found server: %s:%d\\n", serverIP.c_str(), serverPort);
        mdns_query_results_free(results);
    } else {
        Serial.println("✗ Server not found via mDNS, using default");
        serverIP = "192.168.1.100";  // Fallback
        serverPort = SERVER_PORT;
    }
    
    // 4. Connect to WebSocket
    connectToWebSocket();
    
    // 5. Initialize audio hardware
    initializeAudioHardware();
    
    Serial.println("Setup complete!");
}

// ============= WEBSOCKET SETUP =============
void connectToWebSocket() {
    String url = "/ws/audio";
    
    Serial.printf("Connecting to WebSocket: ws://%s:%d%s\\n",
                  serverIP.c_str(), serverPort, url.c_str());
    
    webSocket.begin(serverIP.c_str(), serverPort, url.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("WebSocket disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("✓ WebSocket connected to AEGIS1");
            break;
        case WStype_BIN:
            // Received PCM audio from server
            playAudioToSpeaker(payload, length);
            break;
        case WStype_TEXT:
            // Received JSON status message
            handleStatusMessage((char*)payload);
            break;
        default:
            break;
    }
}

// ============= MAIN LOOP =============
void loop() {
    webSocket.loop();
    
    // Get audio from microphone and send to server
    uint8_t audioBuffer[320];  // 10ms @ 16kHz = 320 bytes
    if (getAudioFromMicrophone(audioBuffer, 320)) {
        webSocket.sendBIN(audioBuffer, 320);
    }
    
    delay(10);
}

// ============= AUDIO FUNCTIONS =============
void initializeAudioHardware() {
    // Initialize I2S microphone input
    // Configure GPIO pins, I2S settings, etc.
    // [Your audio hardware initialization code here]
}

bool getAudioFromMicrophone(uint8_t* buffer, size_t bufferSize) {
    // Read audio from INMP441 microphone via I2S
    // [Your microphone reading code here]
    return true;
}

void playAudioToSpeaker(uint8_t* audioData, size_t length) {
    // Play audio to PAM8403 speaker via I2S DAC
    // [Your speaker output code here]
}

void handleStatusMessage(char* jsonMessage) {
    // Parse JSON status message from server
    // Example: {"type": "connected", "message": "AEGIS1 ready"}
    Serial.printf("Status: %s\\n", jsonMessage);
}
'''

# ============================================================================
# CONFIGURATION INSTRUCTIONS
# ============================================================================

SETUP_INSTRUCTIONS = """
╔════════════════════════════════════════════════════════════════════════════╗
║              ESP32 AUTO-DISCOVERY SETUP INSTRUCTIONS                      ║
╚════════════════════════════════════════════════════════════════════════════╝

## STEP 1: Server Configuration (.env)

Add to your .env file:

    # mDNS Service Discovery (for ESP32 auto-discovery)
    SERVER_DISCOVERY=true
    MDNS_SERVICE_NAME=aegis1

    # Local LLM (optional - for testing without API tokens)
    USE_LOCAL_MODEL=false   # Set to true if using Ollama locally


## STEP 2: Start AEGIS1 Bridge Server

    python3 -m bridge.main

Expected output:
    
    mDNS Service Discovery:
       Service: aegis1.local:8000
       ESP32 can auto-discover and connect


## STEP 3: Configure ESP32 Firmware

Copy the firmware snippet above (ESP32_FIRMWARE_SNIPPET) to your Arduino IDE:

1. Open: test_5_openclaw_voice.cpp (or similar)
2. Add required includes:
   #include <esp_mdns.h>
   #include <WebSocketsClient.h>

3. Update WiFi credentials:
   const char* WIFI_SSID = "your-network-name";
   const char* WIFI_PASSWORD = "your-network-password";

4. Ensure these match your .env:
   const char* MDNS_SERVICE_NAME = "aegis1";
   const int SERVER_PORT = 8000;


## STEP 4: Flash ESP32

1. Select Board: Tools → Board → ESP32 → ESP32 Dev Module
2. Select Port: Tools → Port → /dev/cu.usbserial-...
3. Click: Upload


## STEP 5: Verify Connection

Open Serial Monitor (9600 baud):

Expected sequence:
    ✓ Connected! IP: 192.168.1.100
    Discovering aegis1 service via mDNS...
    ✓ Found server: 192.168.1.50:8000
    Connecting to WebSocket: ws://192.168.1.50:8000/ws/audio
    ✓ WebSocket connected to AEGIS1
    
    [Ready to receive speech!]


## TROUBLESHOOTING

### Problem: "Server not found via mDNS"
- Check server is running: python3 -m bridge.main
- Verify mDNS is enabled: SERVER_DISCOVERY=true in .env
- Check WiFi is same network (ESP32 and laptop on same router)
- Fallback: Replace mDNS with hardcoded server IP

### Problem: "WebSocket connection failed"
- Verify server is running on port 8000
- Check firewall allows port 8000
- Verify ESP32 and server are on same WiFi network

### Problem: "No audio response"
- Check microphone is connected to GPIO33 (BCLK=13, LRCLK=14)
- Check speaker is connected to GPIO25 (DAC1)
- Test with: http://localhost:8000/health


## RAPID TESTING WITH LOCAL OLLAMA (Free!)

To test without consuming Anthropic API tokens:

1. Install Ollama: https://ollama.ai
2. Pull model: ollama pull phi3
3. Start Ollama: ollama serve (in another terminal)
4. Update .env:
   USE_LOCAL_MODEL=true
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=phi3

5. Start server: python3 -m bridge.main
6. Server will now use local Phi-3-mini (no API cost!)

Response time: ~200-500ms (faster than Claude)
Cost: FREE (perfect for development iteration)
"""

# Print instructions when module is imported
if __name__ == "__main__":
    print(SETUP_INSTRUCTIONS)
    print("\n" + "=" * 80)
    print("FIRMWARE CODE SNIPPET:")
    print("=" * 80)
    print(ESP32_FIRMWARE_SNIPPET)
