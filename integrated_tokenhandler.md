# Integrating token handler with ansible.

To avoid having to consistently check for valid storedsafe token, this can be integrated directly into handler using a tokenhandler login script 

## wrapper.sh 

Create a simple script that utilizes tokenhandler to check for valid token, and log in if none is found

For example:

```
#!/bin/env bash

TOKENHANDLER_PATH=$(find /home/ -name "tokenhandler.py" 2>/dev/null | head -n1)
TOKENHANDLER="python3 $TOKENHANDLER_PATH"
if [ -f $TOKENHANDLER_PATH ]; then
  ${TOKENHANDLER} check > /dev/null
  if [ $? -eq 1 ]; then
    ${TOKENHANDLER} login
  else
    exit 0
  fi
else
  echo "No tokenhandler found"
  exit 1
fi

```

## Usage
Add the location of the wrapper.sh script to either environment variables using `STOREDSAFE_TOKEN_UPDATE_SCRIPT` or as an ansible var using `storedsafe_token_update_script`

`export STOREDSAFE_TOKEN_UPDATE_SCRIPT="/home/$USER/git/tools/wrapper.sh"`
(This is of course inserted in to your .bashrc or similar start-up script)

or, in any relevant group_vars:

`storedsafe_token_update_script: /home/$USER/git/tools/wrapper.sh`
(Note: unqouted)

