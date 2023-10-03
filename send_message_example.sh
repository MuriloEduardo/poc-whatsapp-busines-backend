#!/bin/bash

source .env

curl -i -X POST 'https://graph.facebook.com/v17.0/109628212037229/messages' \
  -H "Authorization: Bearer $WHATSAPP_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{ \"messaging_product\": \"whatsapp\", \"to\": \"$WHATSAPP_NUMBER\", \"type\": \"template\", \"template\": { \"name\": \"hello_world\", \"language\": { \"code\": \"en_US\" } } }"
