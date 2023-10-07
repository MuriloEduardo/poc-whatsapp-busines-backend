import json


def mount_whatsapp_messages(messages):
    data = []

    for document in messages:
        document_data = json.loads(json.dumps(document, default=str))
        if "messages" in document_data:
            for message in document_data["messages"]:
                timestamp = document["_id"].generation_time
                timestamp_datetime = timestamp.timestamp()
                message["timestamps"] = timestamp_datetime

        data.append(document_data)

    return data
