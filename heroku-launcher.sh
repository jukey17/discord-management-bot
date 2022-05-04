#!/bin/bash

FILE="/app/google-credentials.json"
echo "${GOOGLE_CREDENTIALS}" > $FILE

python discordbot.py