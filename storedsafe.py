#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# (c) 2020 Fredrik Soderblom <fredrik@storedsafe.com>
# (c) 2020 AB StoredSafe

from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError, AnsibleParserError
import subprocess
import base64
import requests
import time
import re
import json
import os

DOCUMENTATION = """
    lookup: storedsafe
    author: Fredrik Soderblom <fredrik@storedsafe.com>
    version_added: "2.4"
    short_description: retreive information from vaults in StoredSafe
    description:
      - retreive information from vaults in StoredSafe
      - Optional: add a tokenhandler script using environment variable STOREDSAFE_TOKEN_UPDATE_SCRIPT or ansible variable storedsafe_token_update_script
    options:
      <objectid>:
        description: queried object
        required: True
      <fieldname>:
        description: retrieve value from this field (use "download" on file objects to get content of file returned)
        required: True
"""

EXAMPLES = """
---
- hosts: 127.0.0.1
  tasks:
    - set_fact: foo_password="{{ lookup('storedsafe', '1337/password') }}"
    - debug: msg="var is {{ foo_password }} "

    - debug: msg="{{ lookup('storedsafe', '655/pin') }}"

    - name: lookup password in loop
      debug: msg="{{ item }}"
      with_storedsafe:
        - 628/username
        - 628/password
        - 628/objectname

# templates/example.j2

# Generic lookup
{{ lookup('storedsafe', '7893/password') }} # foobar

# Download file, content will be returned as a string
{{ lookup('storedsafe', '1718/download') }} # get content of file

"""

RETURN = """
  _list:
    description: requested value/s
"""

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

MAX_RETRIES = 5
UPDATE_WAIT_SLEEP = 3
UPDATE_RETRY_DELAY = 1
UPDATE_LOCK_FILE = os.path.expanduser('/tmp/.storedsafe_token_update_lock')


class TokenUpdateScriptNotFoundError(AnsibleError):
    pass


class TokenUpdateTimeoutError(AnsibleError):
    pass


class TokenUpdateFailedError(AnsibleError):
    pass


class UnexpectedStatusCodeError(AnsibleError):
    pass


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        result = []
        display.vvvv(f"StoredSafe lookup initial terms is {terms}")

        self.retries = 0
        self.ansible_variables = variables
        self.cabundle = (
            os.getenv('STOREDSAFE_CABUNDLE') or
            variables.get('storedsafe_cabundle')
        )
        self.skipverify = (
            (os.getenv('STOREDSAFE_SKIP_VERIFY') in ['1', 'true', 'True', 't']) or
            variables.get('storedsafe_skip_verify')
        )
        self.rc_file = (
            os.getenv('STOREDSAFE_RC_FILE') or
            variables.get('storedsafe_rc_file') or
            os.path.expanduser('~/.storedsafe-client.rc')
        )

        url, token = self._get_url_and_token()
        display.vvvv(f"Using RC file: {self.rc_file}")

        for term in terms:
            term_split = term.split('/', 1)
            objectid = term_split[0]
            fieldname = term_split[1]
            display.vvvv(f"StoredSafe lookup using {objectid}/{fieldname}")

            while self.retries < MAX_RETRIES:
                try:
                    (status_code, item) = self._get_item(url, token,
                                                         objectid, fieldname, self.cabundle, self.skipverify)
                    if status_code < 400:
                        display.vvvv("Successfully retrieved item")
                        result.append(item.rstrip())
                        break
                    elif status_code == 403:
                        display.vvvv(
                            "Token rejected when retrieving item, updating token and retrying.")
                        url, token = self._get_url_and_token(variables)
                    else:
                        raise UnexpectedStatusCodeError(
                            f"Status code: {status_code}")
                except:
                    raise AnsibleError(
                        "Failed to retreive information from StoredSafe.")
                self.retries += 1

            if self.retries == MAX_RETRIES:
                raise AnsibleError(
                    f"Token rejected, Failed updating token after {self.retries} retries.")
        return result

    def _get_url_and_token(self):
        # Get environment/ansible variables
        server = (
            os.getenv('STOREDSAFE_SERVER') or
            self.ansible_variables.get('storedsafe_server')
        )
        token = os.getenv('STOREDSAFE_TOKEN')
        update_token_script = (
            os.getenv("STOREDSAFE_TOKEN_UPDATE_SCRIPT") or
            self.ansible_variables.get("storedsafe_token_update_script")
        )

        # Try rc file
        if not server:
            server, token = self._read_rc()
            if not server:
                raise AnsibleError('StoredSafe address not set. Specify with'
                                   ' STOREDSAFE_SERVER environment variable, storedsafe_server Ansible variable'
                                   f' or specified in the {self.rc_file}')
        if not token and not update_token_script:
            raise AnsibleError('StoredSafe token not set and no update script available.'
                               ' Specify token with STOREDSAFE_TOKEN environment variable'
                               f' or specify in the {self.rc_file}.'
                               ' Specify token update script in variable "storedsafe_token_update_script" '
                               ' or STOREDSAFE_TOKEN_UPDATE_SCRIPT environment variable.')
        url = self._server_to_url(server)

        # Try to update token if auth check fails
        if not self._auth_check(url, token):
            while self.retries < MAX_RETRIES:
                while os.path.isfile(UPDATE_LOCK_FILE):
                    time.sleep(UPDATE_WAIT_SLEEP)
                open(UPDATE_LOCK_FILE, 'w').close()
                try:
                    server, token = self._update_token(update_token_script)
                    url = self._server_to_url(server)
                    return url, token
                except (TokenUpdateTimeoutError, TokenUpdateFailedError) as e:
                    display.vvvv(e)
                finally:
                    if os.path.isfile(UPDATE_LOCK_FILE):
                        os.unlink(UPDATE_LOCK_FILE)
                self.retries += 1
            raise TokenUpdateFailedError(
                "Failed running token update script. Maximum retries reached.")
        return url, token

    def _server_to_url(self, server):
        return f"https://{server}/api/1.0"

    def _update_token(self, update_token_script):
        if not update_token_script:
            raise TokenUpdateScriptNotFoundError('Not logged in to StoredSafe and no update script available.'
                                                 ' Specify token with STOREDSAFE_TOKEN environment variable'
                                                 f' or specify in the {self.rc_file}.'
                                                 ' Specify token update script in variable "storedsafe_token_update_script" '
                                                 ' or STOREDSAFE_TOKEN_UPDATE_SCRIPT environment variable.')
        if not os.path.exists(update_token_script):
            display.vvvv(f"Given path is {update_token_script}")
            raise TokenUpdateScriptNotFoundError(
                "Token update script does not exist at given path.")
        try:
            display.vvvv(
                f"Prompting for storedsafe login with script: {update_token_script}")
            proc = subprocess.run(
                ["/bin/sh", update_token_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            display.vvvv(f"Login script stdout: {proc.stdout}")
            display.vvvv(f"Login script stderr: {proc.stderr}")
            if proc.returncode == 0:
                server, token = self._read_rc()
                display.vvvv(
                    f"Login script retrieved token: {token} from server: {server}")
                return server, token
            else:
                raise TokenUpdateFailedError("")
        except subprocess.TimeoutExpired:
            raise TokenUpdateTimeoutError(
                "Failed running token update script. Timed out.")

    def _get_item(self, url, token, objectid, fieldname, cabundle, skipverify):
        item = False
        payload = {'token': token, 'decrypt': 'true'}
        if fieldname == 'download':
            payload['filedata'] = 'true'
            display.vvvv(u"StoredSafe will try to download file content.")
        if skipverify:
            req = requests.get(url + '/object/' + objectid,
                               params=payload, verify=False)
        elif cabundle:
            req = requests.get(url + '/object/' + objectid,
                               params=payload, verify=cabundle)
        else:
            req = requests.get(url + '/object/' + objectid, params=payload)
        data = json.loads(req.content)
        if not req.ok:
            return req.status_code, None

        if 'OBJECT' in data:
            if (len(data['OBJECT'])):  # Unless result is empty
                try:
                    item = data['OBJECT'][0]["crypted"][fieldname]
                except:
                    try:
                        item = data['OBJECT'][0]["public"][fieldname]
                    except:
                        try:
                            item = data['OBJECT'][0][fieldname]
                        except:
                            item = False

            if fieldname == 'download':
                if 'FILEDATA' in data:
                    if (len(data['FILEDATA'])):
                        item = base64.b64decode(data['FILEDATA'])
                        display.vvvv(
                            "StoredSafe returning base64 decoded file content.")

        if not item:
            raise AnsibleError(
                'Could not find the requested information in StoredSafe.')

        return req.status_code, to_text(item)

    def _read_rc(self):
        server = None
        token = None
        if os.path.isfile(self.rc_file):
            with open(self.rc_file) as _file:
                for line in _file:
                    if "token" in line:
                        token = re.sub('token:([a-zA-Z0-9]+)\n$', r'\1', line)
                    if "mysite" in line:
                        server = re.sub(
                            'mysite:([-a-zA-Z0-9_.]+)\n$', r'\1', line)
        return (server, token)

    def _auth_check(self, url, token):
        headers = {'x-http-token': token}
        path = f"{url}/auth/check"
        try:
            if self.skipverify:
                req = requests.post(path, headers=headers, verify=False)
            elif self.cabundle:
                req = requests.post(path, headers=headers,
                                    verify=self.cabundle)
            else:
                req = requests.post(path, headers=headers)
        except Exception as e:
            display.vvvv(e)
            raise AnsibleError('ERROR: Can not reach "%s"' % url)

        if not req.ok:
            return False

        data = req.json()
        if data['CALLINFO']['status'] != 'SUCCESS':
            raise AnsibleError(
                'ERROR: Session not authenticated with server. Token invalid?')

        return True
