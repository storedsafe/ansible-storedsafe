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

        if not server:
            (server, token) = self._read_rc(os.path.expanduser('~/.storedsafe-client.rc'))
            if not server:
                raise AnsibleError('StoredSafe address not set. Specify with'
                                   ' STOREDSAFE_SERVER environment variable, storedsafe_server Ansible variable'
                                   ' or specified in the %s' % os.path.expanduser('~/.storedsafe-client.rc'))
        if not token:
            raise AnsibleError('StoredSafe token not set. Specify with'
                               ' STOREDSAFE_TOKEN environment variable'
                               ' or specify in the %s' % os.path.expanduser('~/.storedsafe-client.rc'))
            
        try:
            url = "https://" + server + "/api/1.0"
            self._auth_check(url, token, cabundle, skipverify)
        except:
            raise AnsibleError('Not logged in to StoredSafe.')

        for term in terms:
            term_split = term.split('/', 1)
            objectid = term_split[0]
            fieldname = term_split[1]
            display.vvvv(u"StoredSafe lookup using %s/%s" % (objectid, fieldname))

            try:
                item = self._get_item(url, token, objectid, fieldname, cabundle, skipverify)
                result.append(item.rstrip())
            except:
                raise AnsibleError('Failed to retreive information from StoredSafe.')

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
            raise AnsibleError('Failed to communicate with StoredSafe.')

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

        return to_text(item)

    def _read_rc(self, rc_file):
        if os.path.isfile(rc_file):
            _file = open(rc_file, 'rU')
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
            raise AnsibleError('Not logged in to StoredSafe.')

        data = json.loads(req.content)
        if data['CALLINFO']['status'] != 'SUCCESS':
            raise AnsibleError('ERROR: Session not authenticated with server. Token invalid?')

        return True
