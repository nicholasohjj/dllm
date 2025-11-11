/*
 * SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "protocol_examples_common.h"
#include "esp_log.h"
#include "mqtt_client.h"

#include "esp_check.h"
#include "bsp/esp-bsp.h"
#include "esp_camera.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "wifi_eduroam.h"
#include "esp_sleep.h"

#define SLEEP_TIME 15 // seconds
#define TASK_DELAY 5 // seconds
static const char *TAG = "mqtt5_example";

char *mqtt_url = "mqtt://172.31.122.120"; // IP address of the MQTT broker

static void log_error_if_nonzero(const char *message, int error_code)
{
	if (error_code != 0) {
		ESP_LOGE(TAG, "Last error %s: 0x%x", message, error_code);
	}
}

static esp_mqtt5_user_property_item_t user_property_arr[] = {
	{"board", "esp32"},
	{"u", "user"},
	{"p", "password"}
};

#define USE_PROPERTY_ARR_SIZE   sizeof(user_property_arr)/sizeof(esp_mqtt5_user_property_item_t)

static esp_mqtt5_publish_property_config_t publish_property = {
	.payload_format_indicator = 1,
	.message_expiry_interval = 1000,
	.topic_alias = 0,
	.response_topic = "/topic/test/response",
	.correlation_data = "123456",
	.correlation_data_len = 6,
};

static esp_mqtt5_subscribe_property_config_t subscribe_property = {
	.subscribe_id = 25555,
	.no_local_flag = false,
	.retain_as_published_flag = false,
	.retain_handle = 0,
	.is_share_subscribe = true,
	.share_name = "group1",
};

static esp_mqtt5_subscribe_property_config_t subscribe1_property = {
	.subscribe_id = 25555,
	.no_local_flag = true,
	.retain_as_published_flag = false,
	.retain_handle = 0,
};

static esp_mqtt5_unsubscribe_property_config_t unsubscribe_property = {
	.is_share_subscribe = true,
	.share_name = "group1",
};

static esp_mqtt5_disconnect_property_config_t disconnect_property = {
	.session_expiry_interval = 60,
	.disconnect_reason = 0,
};

static void print_user_property(mqtt5_user_property_handle_t user_property)
{
	if (user_property) {
		uint8_t count = esp_mqtt5_client_get_user_property_count(user_property);
		if (count) {
			esp_mqtt5_user_property_item_t *item = malloc(count * sizeof(esp_mqtt5_user_property_item_t));
			if (esp_mqtt5_client_get_user_property(user_property, item, &count) == ESP_OK) {
				for (int i = 0; i < count; i ++) {
					esp_mqtt5_user_property_item_t *t = &item[i];
					ESP_LOGI(TAG, "key is %s, value is %s", t->key, t->value);
					free((char *)t->key);
					free((char *)t->value);
				}
			}
			free(item);
		}
	}
}

//Routine to set a pixel in a framebuffer.
//You can use this for debugging or other purposes. It sets one pixel in the
//camera framebuffer to a certain rgb value. R, G and B need to be [0-255],
//x and y must be between 0 and 239, inclusive.
void fb_set_pixel(camera_fb_t *fb, int x, int y, int r, int g, int b) {
	if (x<0 || x>=fb->width) return;
	if (y<0 || y>=fb->height) return;
	//r8g8b8 to r5g6b5
	uint16_t c=((r>>3)<<11)|((g>>2)<<5)|(b>>3);
	c=(c<<8)|(c>>8); //swap bytes
	uint16_t *p=(uint16_t*)fb->buf;
	p[x+y*fb->width]=c; //set pixel
}

int connect_count = 0;
/*
 * @brief Event handler registered to receive MQTT events
 *
 *  This function is called by the MQTT client event loop.
 *
 * @param handler_args user data registered to the event.
 * @param base Event base for the handler(always MQTT Base in this example).
 * @param event_id The id for the received event.
 * @param event_data The data for the event, esp_mqtt_event_handle_t.
 */
static void mqtt5_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
	ESP_LOGD(TAG, "Event dispatched from event loop base=%s, event_id=%" PRIi32, base, event_id);
	esp_mqtt_event_handle_t event = event_data;
	esp_mqtt_client_handle_t client = event->client;
	int msg_id;

	ESP_LOGD(TAG, "free heap size is %" PRIu32 ", minimum %" PRIu32, esp_get_free_heap_size(), esp_get_minimum_free_heap_size());
	switch ((esp_mqtt_event_id_t)event_id) {
		case MQTT_EVENT_CONNECTED:
			ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
			print_user_property(event->property->user_property);
			esp_mqtt5_client_set_user_property(&publish_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
			esp_mqtt5_client_set_publish_property(client, &publish_property);
			msg_id = esp_mqtt_client_publish(client, "/topic/qos1", "data_3", 0, 1, 1);
			esp_mqtt5_client_delete_user_property(publish_property.user_property);
			publish_property.user_property = NULL;
			ESP_LOGI(TAG, "sent publish successful, msg_id=%d", msg_id);

			esp_mqtt5_client_set_user_property(&subscribe_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
			esp_mqtt5_client_set_subscribe_property(client, &subscribe_property);
			msg_id = esp_mqtt_client_subscribe(client, "/topic/qos0", 0);
			esp_mqtt5_client_delete_user_property(subscribe_property.user_property);
			subscribe_property.user_property = NULL;
			ESP_LOGI(TAG, "sent subscribe successful, msg_id=%d", msg_id);

			esp_mqtt5_client_set_user_property(&subscribe1_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
			esp_mqtt5_client_set_subscribe_property(client, &subscribe1_property);
			msg_id = esp_mqtt_client_subscribe(client, "/topic/qos1", 2);
			esp_mqtt5_client_delete_user_property(subscribe1_property.user_property);
			subscribe1_property.user_property = NULL;
			ESP_LOGI(TAG, "sent subscribe successful, msg_id=%d", msg_id);

			// esp_mqtt5_client_set_user_property(&unsubscribe_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
			// esp_mqtt5_client_set_unsubscribe_property(client, &unsubscribe_property);
			// msg_id = esp_mqtt_client_unsubscribe(client, "/topic/qos0");
			// ESP_LOGI(TAG, "sent unsubscribe successful, msg_id=%d", msg_id);
			// esp_mqtt5_client_delete_user_property(unsubscribe_property.user_property);
			// unsubscribe_property.user_property = NULL;
			break;
		case MQTT_EVENT_DISCONNECTED:
			ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
			esp_restart();
			print_user_property(event->property->user_property);
			if (connect_count < 3) {
				esp_mqtt_client_start(client); connect_count++;
			} else {
				esp_restart();
			}
			break;
		case MQTT_EVENT_SUBSCRIBED:
			ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED, msg_id=%d", event->msg_id);
			print_user_property(event->property->user_property);
			esp_mqtt5_client_set_publish_property(client, &publish_property);
			msg_id = esp_mqtt_client_publish(client, "/topic/qos0", "data", 0, 0, 0);
			ESP_LOGI(TAG, "sent publish successful, msg_id=%d", msg_id);
			break;
		case MQTT_EVENT_UNSUBSCRIBED:
			ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d", event->msg_id);
			print_user_property(event->property->user_property);
			esp_mqtt5_client_set_user_property(&disconnect_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
			esp_mqtt5_client_set_disconnect_property(client, &disconnect_property);
			esp_mqtt5_client_delete_user_property(disconnect_property.user_property);
			disconnect_property.user_property = NULL;
			esp_mqtt_client_disconnect(client);
			break;
		case MQTT_EVENT_PUBLISHED:
			ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED, msg_id=%d", event->msg_id);
			print_user_property(event->property->user_property);
			break;
		case MQTT_EVENT_DATA:
			ESP_LOGI(TAG, "MQTT_EVENT_DATA");
			print_user_property(event->property->user_property);
			ESP_LOGI(TAG, "payload_format_indicator is %d", event->property->payload_format_indicator);
			ESP_LOGI(TAG, "response_topic is %.*s", event->property->response_topic_len, event->property->response_topic);
			ESP_LOGI(TAG, "correlation_data is %.*s", event->property->correlation_data_len, event->property->correlation_data);
			ESP_LOGI(TAG, "content_type is %.*s", event->property->content_type_len, event->property->content_type);
			ESP_LOGI(TAG, "TOPIC=%.*s", event->topic_len, event->topic);
			ESP_LOGI(TAG, "DATA=%.*s", event->data_len, event->data);
			break;
		case MQTT_EVENT_ERROR:
			ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
			print_user_property(event->property->user_property);
			ESP_LOGI(TAG, "MQTT5 return code is %d", event->error_handle->connect_return_code);
			if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
				log_error_if_nonzero("reported from esp-tls", event->error_handle->esp_tls_last_esp_err);
				log_error_if_nonzero("reported from tls stack", event->error_handle->esp_tls_stack_err);
				log_error_if_nonzero("captured as transport's socket errno",  event->error_handle->esp_transport_sock_errno);
				ESP_LOGI(TAG, "Last errno string (%s)", strerror(event->error_handle->esp_transport_sock_errno));
			}
			break;
		default:
			ESP_LOGI(TAG, "Other event id:%d", event->event_id);
			break;
	}
}

static esp_mqtt_client_handle_t mqtt5_app_start(void)
{
	esp_mqtt5_connection_property_config_t connect_property = {
		.session_expiry_interval = 10,
		.maximum_packet_size = 1024,
		.receive_maximum = 65535,
		.topic_alias_maximum = 2,
		.request_resp_info = true,
		.request_problem_info = true,
		.will_delay_interval = 10,
		.payload_format_indicator = true,
		.message_expiry_interval = 10,
		.response_topic = "/test/response",
		.correlation_data = "123456",
		.correlation_data_len = 6,
	};

	esp_mqtt_client_config_t mqtt5_cfg = {
		.broker.address.uri = mqtt_url,
		.session.protocol_ver = MQTT_PROTOCOL_V_5,
		.network.disable_auto_reconnect = true,
		.credentials.username = "123",
		.credentials.authentication.password = "456",
		.session.last_will.topic = "/topic/will",
		.session.last_will.msg = "i will leave",
		.session.last_will.msg_len = 12,
		.session.last_will.qos = 1,
		.session.last_will.retain = true,
	};

#if CONFIG_BROKER_URL_FROM_STDIN
	char line[128];

	if (strcmp(mqtt5_cfg.uri, "FROM_STDIN") == 0) {
		int count = 0;
		printf("Please enter url of mqtt broker\n");
		while (count < 128) {
			int c = fgetc(stdin);
			if (c == '\n') {
				line[count] = '\0';
				break;
			} else if (c > 0 && c < 127) {
				line[count] = c;
				++count;
			}
			vTaskDelay(10 / portTICK_PERIOD_MS);
		}
		mqtt5_cfg.broker.address.uri = line;
		printf("Broker url: %s\n", line);
	} else {
		ESP_LOGE(TAG, "Configuration mismatch: wrong broker url");
		abort();
	}
#endif /* CONFIG_BROKER_URL_FROM_STDIN */

	esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt5_cfg);

	/* Set connection properties and user properties */
	esp_mqtt5_client_set_user_property(&connect_property.user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
	esp_mqtt5_client_set_user_property(&connect_property.will_user_property, user_property_arr, USE_PROPERTY_ARR_SIZE);
	esp_mqtt5_client_set_connect_property(client, &connect_property);

	/* If you call esp_mqtt5_client_set_user_property to set user properties, DO NOT forget to delete them.
	 * esp_mqtt5_client_set_connect_property will malloc buffer to store the user_property and you can delete it after
	 */
	esp_mqtt5_client_delete_user_property(connect_property.user_property);
	esp_mqtt5_client_delete_user_property(connect_property.will_user_property);

	/* The last argument may be used to pass data to the event handler, in this example mqtt_event_handler */
	esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt5_event_handler, NULL);
	esp_mqtt_client_start(client);

	return client;
}

void app_main(void)
{
	ESP_LOGI(TAG, "Enable timer wakeup");
	ESP_ERROR_CHECK(esp_sleep_enable_timer_wakeup(SLEEP_TIME * 1000000));

	ESP_LOGI(TAG, "[APP] Startup..");
	ESP_LOGI(TAG, "[APP] Free memory: %" PRIu32 " bytes", esp_get_free_heap_size());
	ESP_LOGI(TAG, "[APP] IDF version: %s", esp_get_idf_version());

	esp_log_level_set("*", ESP_LOG_INFO);
	esp_log_level_set("mqtt_client", ESP_LOG_VERBOSE);
	esp_log_level_set("mqtt_example", ESP_LOG_VERBOSE);
	esp_log_level_set("transport_base", ESP_LOG_VERBOSE);
	esp_log_level_set("esp-tls", ESP_LOG_VERBOSE);
	esp_log_level_set("transport", ESP_LOG_VERBOSE);
	esp_log_level_set("outbox", ESP_LOG_VERBOSE);

	ESP_ERROR_CHECK(nvs_flash_init());
	ESP_ERROR_CHECK(esp_netif_init());
	ESP_ERROR_CHECK(esp_event_loop_create_default());

	/* This helper function configures Wi-Fi or Ethernet, as selected in menuconfig.
	 * Read "Establishing Wi-Fi or Ethernet Connection" section in
	 * examples/protocols/README.md for more information about this function.
	 */
	// ESP_ERROR_CHECK(example_connect());
	initialise_wifi();

	ESP_LOGI(TAG, "Start MQTT");
	esp_mqtt_client_handle_t client = mqtt5_app_start();

	ESP_LOGI(TAG, "Init Cam");
	// The camera and other parts need I2C to work. We initialize it here.
	ESP_ERROR_CHECK(bsp_i2c_init());

	// The ESP32-S3-EYE is shipped with 1.3inch ST7789 display controller.
	// It features 16-bit colors and 240x240 resolution. We initialize it here.

	// The configuration. It only needs a SPI max transfer size, which doesn't really matter.
	
	// bsp_display_config_t disp_cfg={
	// 	.max_transfer_sz = 4096
	// };
	// esp_lcd_panel_handle_t panel;
	// esp_lcd_panel_io_handle_t panel_io;
	// // Create the display driver and initialize it.
	// ESP_ERROR_CHECK(bsp_display_new(&disp_cfg, &panel, &panel_io));
	// // Turn it on and set full backlight.
	// ESP_ERROR_CHECK(bsp_display_brightness_init());
	// ESP_ERROR_CHECK(bsp_display_brightness_set(100));

	// ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel, true));
        
	// The default configuration configures the camera to spit out 240x240 frames 
	// of 16-bit 565RGB data, which is ideal to send to the LCD. (Note it may not
	// be ideal for other things; in that case you need to modify the config.)
	camera_config_t camera_config = BSP_CAMERA_DEFAULT_CONFIG;
	// camera_config.fb_location = CAMERA_FB_IN_DRAM;

	ESP_ERROR_CHECK(esp_camera_init(&camera_config));
	int pic_quality = 100;

	// while(1) {
	// cam_op(&p?anel);
	// 	// Grab a frame from the camera...
	camera_fb_t * fb = esp_camera_fb_get();
	// 	// ...draw it on the LCD
	// 	// ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(panel, 0, 0, fb->width, fb->height, fb->buf));
	// 	// ...and tell the camera driver we're done with the frame so it can re-use it.
	ESP_LOGI(TAG, "Cam buffer data len:%d, width: %d, height:%d", fb->len, fb->width, fb->height);
	size_t jpeg_len = 0;
	uint8_t *jpeg_buf;
	frame2jpg(fb, pic_quality, &jpeg_buf, &jpeg_len);

	ESP_LOGI(TAG, "quality %d, JPEG data len:%d", pic_quality, jpeg_len);

	esp_mqtt_client_publish(client, "/cam/room", (char *)jpeg_buf, jpeg_len, 1, 1);
	free(jpeg_buf);

	esp_camera_fb_return(fb);
	// 	vTaskDelay(SECOND_DELAY * 1000 / portTICK_PERIOD_MS);
	// 	// pic_quality = pic_quality > 100 ? 0 : pic_quality + 5;
	// }
	ESP_LOGI(TAG, "Start deep sleep");
	vTaskDelay(TASK_DELAY * 1000 / portTICK_PERIOD_MS);

	// Start deep sleep
	esp_deep_sleep_start();
}
