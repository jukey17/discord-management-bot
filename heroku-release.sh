#!/bin/bash

FILE="/app/google-credentials.json"

if [ ! -e $FILE ];then
  echo "File not exists."
fi
echo "${GOOGLE_CREDENTIALS}" > $FILE
if [ -e $FILE ]; then
  echo "write ${FILE}"
fi