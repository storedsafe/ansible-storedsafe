#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# (c) 2020 Fredrik Soderblom <fredrik@storedsafe.com>
# (c) 2020 AB StoredSafe

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

import os
import json
import re
import requests
import base64
import subprocess

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils._text import to_text

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):

        result = []
        display.vvvv(u"StoredSafe lookup initial terms is %s" % (terms))

        cabundle = os.getenv('STOREDSAFE_CABUNDLE') or variables.get('storedsafe_cabundle')
        skipverify = ((os.getenv('STOREDSAFE_SKIP_VERIFY') in ['1', 'true', 'True', 't']) or
                       variables.get('storedsafe_skip_verify'))

        server = os.getenv('STOREDSAFE_SERVER') or variables.get('storedsafe_server')
        token = os.getenv('STOREDSAFE_TOKEN')

        MAX_RETRIES = 5
        retry_count = 0
        # If defined, runs this script when a request to retrieve an object is
        # rejected with 403 status, and then retries to fetch it.
        update_token_script = (
            os.getenv("STOREDSAFE_TOKEN_UPDATE_SCRIPT") or
            variables.get("storedsafe_token_update_script")
        )
        def update_token():
            nonlocal retry_count
            nonlocal get_item_success

            if not update_token_script:
                raise AnsibleError('Not logged in to StoredSafe and no update script available.'
                               ' Specify token with STOREDSAFE_TOKEN environment variable'
                               ' or specify in the %s' % os.path.expanduser('~/.storedsafe-client.rc.'
                               ' Specify token update script in variable "storedsafe_token_update_script" '
                               ' or STOREDSAFE_TOKEN_UPDATE_SCRIPT environment variable.'))
            if not os.path.exists(update_token_script):
                display.vvvv(u"Given path is %s" % (update_token_script))
                raise AnsibleError("Token update script does not exist at given path.")
            try:
                display.vvvv(f"Prompting for storedsafe login with script: {update_token_script}")
                proc = subprocess.run(
                    ["/bin/sh", update_token_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                display.vvvv(f"Login script stdout: {proc.stdout}")
                display.vvvv(f"Login script stderr: {proc.stderr}")
                if proc.returncode == 0:
                    (server, token) = self._read_rc(os.path.expanduser('~/.storedsafe-client.rc'))
                    display.vvvv(f"Login script retrieved token: {token} from server: {server}")
                    get_item_success = True
                retry_count += 1
                return
            except subprocess.TimeoutExpired:
                raise AnsibleError("Failed running token update script. Timed out.")

        if not server:
            (server, token) = self._read_rc(os.path.expanduser('~/.storedsafe-client.rc'))
            if not server:
                raise AnsibleError('StoredSafe address not set. Specify with'
                                ' STOREDSAFE_SERVER environment variable, storedsafe_server Ansible variable'
                                ' or specified in the %s' % os.path.expanduser('~/.storedsafe-client.rc'))

        if not token and not update_token_script:
            raise AnsibleError('StoredSafe token not set and no update script available.'
                               ' Specify token with STOREDSAFE_TOKEN environment variable'
                               ' or specify in the %s' % os.path.expanduser('~/.storedsafe-client.rc.'
                               ' Specify token update script in variable "storedsafe_token_update_script" '
                               ' or STOREDSAFE_TOKEN_UPDATE_SCRIPT environment variable.'))

        get_item_success = False
        while not get_item_success and retry_count < MAX_RETRIES:
            try:
                url = "https://" + server + "/api/1.0"
                authed = self._auth_check(url, token, cabundle, skipverify)
                if not authed:
                    update_token()
                    continue
                display.vvvv("Token auth check success")
                get_item_success = True
            except:
                # we get here if we are not logged in.
                display.vvvv("Updating token using token update script")
                update_token()
        if not get_item_success:
            raise AnsibleError(f'Auth check failed after {retry_count} retries')

        for term in terms:
            term_split = term.split('/', 1)
            objectid = term_split[0]
            fieldname = term_split[1]
            display.vvvv(u"StoredSafe lookup using %s/%s" % (objectid, fieldname))

            MAX_RETRIES = 5
            retry_count = 0
            get_item_success = False
            while not get_item_success and retry_count < MAX_RETRIES:
                try:
                    (status_code, item) = self._get_item(url, token, objectid, fieldname, cabundle, skipverify)
                    if status_code < 400:
                        display.vvvv("Successfully retrieved item")
                        result.append(item.rstrip())
                        get_item_success = True
                    elif status_code == 403:
                        display.vvvv("Token rejected when retrieving item, updating token and retrying.")
                        update_token()
                    else:
                        raise Exception
                except:
                    raise AnsibleError('Failed to retreive information from StoredSafe.')

            if not get_item_success:
                raise AnsibleError('Token rejected, Failed updating token after %s retries.' % retry_count)
        return result

    def _get_item(self, url, token, objectid, fieldname, cabundle, skipverify):
        item = False
        payload = { 'token': token, 'decrypt': 'true' }
        if fieldname == 'download':
            payload['filedata'] = 'true'
            display.vvvv(u"StoredSafe will try to download file content.")
        if skipverify:
            req = requests.get(url + '/object/' + objectid, params=payload, verify=False)
        elif cabundle:
            req = requests.get(url + '/object/' + objectid, params=payload, verify=cabundle)
        else:
            req = requests.get(url + '/object/' + objectid, params=payload)
        data = json.loads(req.content)
        if not req.ok:
            return req.status_code, None

        if 'OBJECT' in data:
            if (len(data['OBJECT'])): # Unless result is empty
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
                        display.vvvv(u"StoredSafe returning base64 decoded file content.")

        if not item:
            raise AnsibleError('Could not find the requested information in StoredSafe.')

        return req.status_code, to_text(item)

    def _read_rc(self, rc_file):
        if os.path.isfile(rc_file):
            _file = open(rc_file, 'r')
            token = None
            for line in _file:
                if "token" in line:
                    token = re.sub('token:([a-zA-Z0-9]+)\n$', r'\1', line)
                    if token == 'none':
                        return (False, False)
                if "mysite" in line:
                    server = re.sub('mysite:([-a-zA-Z0-9_.]+)\n$', r'\1', line)
                    if server == 'none':
                        return (False, False)
            _file.close()
            return (server if server else False, token if token else False)
            if not token:
                return (False, False)
            if not server:
                return (False, False)
            return (server, token)
        else:
            return (False, False)

    def _auth_check(self, url, token, cabundle, skipverify):
        payload = { 'token': token }
        try:
            if skipverify:
                req = requests.post(url + '/auth/check', data=json.dumps(payload), verify=False)
            elif cabundle:
                req = requests.post(url + '/auth/check', data=json.dumps(payload), verify=cabundle)
            else:
                req = requests.post(url + '/auth/check', data=json.dumps(payload))
        except:
            raise AnsibleError('ERROR: Can not reach "%s"' % url)

        if not req.ok:
            return False

        data = json.loads(req.content)
        if data['CALLINFO']['status'] != 'SUCCESS':
            raise AnsibleError('ERROR: Session not authenticated with server. Token invalid?')

        return True
