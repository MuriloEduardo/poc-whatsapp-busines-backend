#!/bin/bash

source .env

curl -i -X POST "https://graph.facebook.com/v18.0/$WHATSAPP_SENDER_NUMBER/messages" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $WHATSAPP_TOKEN" \
  -d "{ \"messaging_product\": \"whatsapp\", \"to\": \"$WHATSAPP_RECEIVER_NUMBER\", \"type\": \"template\", \"template\": { \"name\": \"hello_world\", \"language\": { \"code\": \"en_US\" } } }"
