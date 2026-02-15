/**
 * AEGIS1 Firmware - Voice Pipeline (Main)
 * Board: ESP32 DevKit V1 (DOIT)
 *
 * Full pipeline: Mic -> AEGIS1 Bridge -> STT/Claude/TTS -> PCM -> Speaker
 * Connects to bridge at BRIDGE_HOST:BRIDGE_PORT/ws/audio.
 * Bridge contract v1: /ws/audio, binary PCM 16kHz 16-bit, 320-byte chunks, WStype_BIN TTS.
 * Source: Adapted from AEGIS prototype test_5_openclaw_voice (flashed and tested on hardware).
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <driver/i2s.h>
#include "../config.h"

WebSocketsClient webSocket;
bool cloud_connected = false;

// I2S mic config
#define I2S_PORT         I2S_NUM_0
#define I2S_SAMPLE_RATE  16000
#define I2S_BUF_COUNT    8
#define I2S_BUF_LEN      512
#define SEND_CHUNK_BYTES  (320)  // 10ms at 16kHz 16-bit mono

int16_t mic_buffer[I2S_BUF_LEN];
size_t bytes_read = 0;

// TTS playback: bridge sends 16-bit PCM at 16kHz; we play on DAC (8-bit)
#define PLAY_SAMPLE_RATE 16000
#define PLAY_BUF_SAMPLES 16000   // 1 second
#define PLAY_CHUNK       160    // 10ms per loop drain
static int16_t play_buf[PLAY_BUF_SAMPLES];
static size_t play_head = 0;
static size_t play_len = 0;

static void play_pcm_chunk() {
    if (play_len < PLAY_CHUNK) return;
    for (int i = 0; i < PLAY_CHUNK; i++) {
        int16_t s = play_buf[play_head];
        play_head++;
        play_len--;
        uint8_t dac_val = (uint8_t)(((int32_t)(s >> 8) + 128) & 0xFF);
        dacWrite(AMP_DAC_PIN, dac_val);
        delayMicroseconds(62);  // ~16kHz
    }
}

static void setup_i2s_mic() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = I2S_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = I2S_BUF_COUNT,
        .dma_buf_len = I2S_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_MIC_BCLK,
        .ws_io_num = I2S_MIC_LRCLK,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_MIC_DIN
    };
    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
}

void websocket_event(WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED: {
            Serial.println("[OK] AEGIS1 bridge connected");
            cloud_connected = true;
            digitalWrite(LED_PIN, HIGH);
            break;
        }
        case WStype_BIN: {
            size_t samples = length / 2;
            size_t space = PLAY_BUF_SAMPLES - play_len;
            size_t copy_samples = (samples < space) ? samples : space;
            if (copy_samples > 0 && payload) {
                size_t write_at = (play_head + play_len) % PLAY_BUF_SAMPLES;
                for (size_t i = 0; i < copy_samples; i++) {
                    uint8_t lo = payload[i * 2];
                    uint8_t hi = payload[i * 2 + 1];
                    int16_t s = (int16_t)(lo | (hi << 8));
                    play_buf[(write_at + i) % PLAY_BUF_SAMPLES] = s;
                }
                play_len += copy_samples;
            }
            Serial.printf("[OK] TTS %u bytes -> playing\n", (unsigned)length);
            break;
        }
        case WStype_TEXT:
            Serial.printf("[MSG] %.*s\n", (int)length, (char*)payload);
            break;
        case WStype_DISCONNECTED:
            Serial.println("[--] AEGIS1 bridge disconnected");
            cloud_connected = false;
            digitalWrite(LED_PIN, LOW);
            break;
        case WStype_ERROR:
            cloud_connected = false;
            digitalWrite(LED_PIN, LOW);
            break;
        default:
            break;
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    Serial.println("\n=== AEGIS1 Voice Firmware (Main) ===");
    Serial.printf("Target: %s:%d/ws/audio\n", BRIDGE_HOST, BRIDGE_PORT);
    Serial.println("Flow: Mic -> Bridge -> STT/Claude/TTS -> Speaker\n");

    setup_i2s_mic();
    Serial.println("[OK] Mic ready");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.println("[...] WiFi connecting...");
    int dots = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        if (++dots >= 20) { Serial.println(); dots = 0; }
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }
    Serial.println();
    Serial.printf("[OK] WiFi %s\n", WiFi.localIP().toString().c_str());

    webSocket.begin(BRIDGE_HOST, BRIDGE_PORT, "/ws/audio");
    webSocket.onEvent(websocket_event);
    webSocket.setReconnectInterval(5000);
    Serial.println("[OK] WebSocket started; speak into mic after connection\n");
}

void loop() {
    webSocket.loop();

    if (cloud_connected) {
        size_t br = 0;
        if (i2s_read(I2S_PORT, (void*)mic_buffer, SEND_CHUNK_BYTES, &br, 0) == ESP_OK && br > 0)
            webSocket.sendBIN((uint8_t*)mic_buffer, br);
    }

    play_pcm_chunk();

    static unsigned long last = 0;
    if (millis() - last >= 5000) {
        last = millis();
        if (cloud_connected)
            Serial.println("[OK] AEGIS1 bridge connected");
        else
            Serial.println("[...] Connecting...");
    }
}
