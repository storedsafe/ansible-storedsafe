# ansible-storedsafe lookup module

This is a lookup module for information stored in [StoredSafe](https://storedsafe.com/). Supports Ansible 2.4 or better.

Support for previous versions of StoredSafe (pre v2.1.0) can be found in the legacy branch.

## Installation

This plugin requires Ansible v2.4 and the Python [```requests```](http://docs.python-requests.org/en/master/) library.

It has been developed and tested using Python v2.7.17 and Python v3.6.9, on Ubuntu 18.04.4 LTS.

Most of the required libraries are installed by default, but requests require manual installation.

**requests:**

```bash
sudo -H pip install requests
```

Lookup plugins can be loaded from several different locations similar to `$PATH`, see
[lookup_plugins](https://docs.ansible.com/ansible/latest/plugins/lookup.html).

The source for the plugin can be pointed to via a _requirements.yml_ file, and accessed via [`ansible-galaxy`](https://docs.ansible.com/ansible/latest/cli/ansible-galaxy.html).

## Configuration

Both the StoredSafe server address and the StoredSafe token can be read from the file `$HOME/.storedsafe.rc`, which can be created and maintained by [`storedsafe-tokenhandler`](https://github.com/storedsafe/tokenhandler).

Or it can be done with environment variables or Ansible variables. If any parameter is set by both an environment variable and an alternative means, the environment variable takes precedence.

To specify the address to the StoredSafe server:

```bash
    export STOREDSAFE_SERVER=safe.domain.cc
```

To specify a StoredSafe auth token:

```bash
    export STOREDSAFE_TOKEN=<StoredSafe-Token>
```

The StoredSafe token intentionally can **not** be set via an Ansible variable, as this is generally checked into revision control and would be a bad security practice, defeating the purpose of using StoredSafe.

The plugin also supports specifying the list of trusted CAs either thru by using the ```STOREDSAFE_CABUNDLE``` variables which can either point to a single file or a directory.

```bash
    export STOREDSAFE_CABUNDLE=/etc/pki/tls/ca.crt
    export STOREDSAFE_CABUNDLE=/etc/pki/tls
```

To disable verification (**NOT RECOMMENDED**) the ```STOREDSAFE_SKIP_VERIFY``` variable can be set.

```bash
    export STOREDSAFE_SKIP_VERIFY=True
```

The StoredSafe server address, CA bundle path and validation can also be set via the Ansible variables ```storedsafe_server```, ```storedsafe_cabundle```, and ```storedsafe_skip_verify```, respectively.

## Usage

ansible-storedsafe works as any other lookup plugin.

```yaml
- debug: msg="{{ lookup('storedsafe', '919/password') }}"
```

Where ```919```is the object-id of the requested item. The object-id is visible in the StoredSafe web-ui.

```yaml
# templates/example.j2

# Generic secrets
{{ lookup('storedsafe', '919/password') }} # foobar
# Specify field inside lookup
{{ lookup('storedsafe', '919/cryptedinfo') }} # foobar
```

If the desired value is stored within StoredSafe, within a task, the lookup can also be performed with:

```yaml
with_storedsafe:
- 919/objectname
- 919/username
- 919/password
```

And then referenced with `"{{ item }}"`

This only work within tasks, though. You can **not** use the `with_storedsafe:` syntax within a variable definition file.

## File content

Using ```download``` as the fieldname will return content of any file object.

```yaml
- debug: msg="the content of the file object-id 42 is {{lookup('storedsafe', '42/download') }}"

- name: display multiple file contents
  debug: var=item
  with_storedsafe:
    - 8552/download
    - 743/download
    - 48/download

```

## Example

```bash
$ cat test.yml
---
- hosts: localhost
  gather_facts: False
  vars:
     contents: "{{ lookup('storedsafe', '21/objectname', '21/username', '21/password') }}"
  tasks:
     - name: lookup password via vars
       debug: msg="the returned value is {{ contents }}"
     - name: lookup password in loop
       debug: msg="{{ item }}"
       with_storedsafe:
        - 855/username
        - 855/password
        - 855/cryptedinfo
        - 980/username
        - 980/password
        - 1438/download

$ ansible-playbook test.yml

PLAY [localhost] ***************************************************************

TASK [lookup password via vars] ************************************************
ok: [localhost] => {
    "msg": "the returned value is fw.storedsafe.com,root,>%b\\zR2r[=^52b2T,&`XRdnaVxEr<)@t=$h5w$/s"
}

TASK [lookup password in loop] *************************************************
ok: [localhost] => (item=None) => {
    "msg": "root"
}
ok: [localhost] => (item=None) => {
    "msg": "366Gta:.O8t[xCekWv7q6mqcDT7XO7am3ZK5Nkfv"
}
ok: [localhost] => (item=None) => {
    "msg": "Old root pw was CekWv7q6mqcDT7X"
}
ok: [localhost] => (item=None) => {
    "msg": "root"
}
ok: [localhost] => (item=None) => {
    "msg": "pun-top-mild-cage-cave-bulk-fate-cash-he-tun-feud-goat"
}
ok: [localhost] => (item=None) => {
    "msg": "-----BEGIN CERTIFICATE-----\r\nMIIIODCCByCgAwIBAgIQCXNzhfKoEd4lY7cUjp/oHDANBgkqhkiG9w0BAQsFADB1\r\nMQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3\r\nd3cuZGlnaWNlcnQuY29tMTQwMgYDVQQDEytEaWdpQ2VydCBTSEEyIEV4dGVuZGVk\r\nIFZhbGlkYXRpb24gU2VydmVyIENBMB4XDTE5MDYxMjAwMDAwMFoXDTIxMDgxMjEy\r\nMDAwMFowgbgxHTAbBgNVBA8MFFByaXZhdGUgT3JnYW5pemF0aW9uMRMwEQYLKwYB\r\nBAGCNzwCAQMTAlNFMRMwEQYDVQQFEwo1NTY4NTQwODM0MQswCQYDVQQGEwJTRTES\r\nMBAGA1UECBMJU3RvY2tob2xtMRMwEQYDVQQHDApKw6RyZsOkbGxhMR4wHAYDVQQK\r\nExVBQiBTdG9yZWRTYWZlIFN2ZXJpZ2UxFzAVBgNVBAMTDnN0b3JlZHNhZmUuY29t\r\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA2OkYJBkdCG4l0TRqTrMR\r\nqsTgwnCRT18gR1/r4QWqYSOuVMuaODJXcAtP7PqNI+cNdGyYD2zCB9dtcIA29DKb\r\nrs7ehUWw/bdyRvWk9/2cCFYVWiYpcv0FP6UyExIGhJ5isEdzVTs+fyaml+l18FuV\r\ntQ8zZwdNCbARg1MB37KXxACvCJkKxx4lf61Unfvs+LwCTgOIn4KnpOY0k7DjGizo\r\nFHRedPrCvs4aBlEcKJn5qv8DR75A4Q4ivqE5uLRiPqWXeoGRNgMXYfh4HpqV0Aqp\r\nwoCkJJxeufhIthM6Qob0M+wGyZ7VfpPAEMAPVex9upalf0ey9eBZxv/5bJolCX0c\r\njLRdbExE7sTKsERZEUAOrCqJCkMGZMvpAA2vCzvtZ2X+sAiAhuqeYsAK9pm8UOv/\r\naq8Gz9GixtSIjBAN56Mxqp+YVyHn/+AP+jsKE30wootybrqc6fxLsybOJu36o2wJ\r\nF4D2Ut5f6Sqlg4n6YuCCUVyt7rodt3ygExBU6flub01XZZoI7Llf0qO5Gtevn92G\r\nwVaEDirDRCgEE5ZVOXr/5/uRGOzBUH/nYAwZukF5JFGqEmpAgIpvi+n+0q03aI8i\r\naJKhhLRrjvuRiuT12Sn6qWhQQYBNoGJ7YqdcivtkNRTIwsrp3qtR3BJJaxgr4iAS\r\nTHE5t2IAX0rVHHwQgqmUZnUCAwEAAaOCA34wggN6MB8GA1UdIwQYMBaAFD3TUKXW\r\noK3u80pgCmXTIdT4+NYPMB0GA1UdDgQWBBTpWS3LSgq1EDofN/eBgW4gCEOAnDAt\r\nBgNVHREEJjAkgg5zdG9yZWRzYWZlLmNvbYISd3d3LnN0b3JlZHNhZmUuY29tMA4G\r\nA1UdDwEB/wQEAwIFoDAdBgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwdQYD\r\nVR0fBG4wbDA0oDKgMIYuaHR0cDovL2NybDMuZGlnaWNlcnQuY29tL3NoYTItZXYt\r\nc2VydmVyLWcyLmNybDA0oDKgMIYuaHR0cDovL2NybDQuZGlnaWNlcnQuY29tL3No\r\nYTItZXYtc2VydmVyLWcyLmNybDBLBgNVHSAERDBCMDcGCWCGSAGG/WwCATAqMCgG\r\nCCsGAQUFBwIBFhxodHRwczovL3d3dy5kaWdpY2VydC5jb20vQ1BTMAcGBWeBDAEB\r\nMIGIBggrBgEFBQcBAQR8MHowJAYIKwYBBQUHMAGGGGh0dHA6Ly9vY3NwLmRpZ2lj\r\nZXJ0LmNvbTBSBggrBgEFBQcwAoZGaHR0cDovL2NhY2VydHMuZGlnaWNlcnQuY29t\r\nL0RpZ2lDZXJ0U0hBMkV4dGVuZGVkVmFsaWRhdGlvblNlcnZlckNBLmNydDAMBgNV\r\nHRMBAf8EAjAAMIIBewYKKwYBBAHWeQIEAgSCAWsEggFnAWUAdQDuS723dc5guuFC\r\naR+r4Z5mow9+X7By2IMAxHuJeqj9ywAAAWtMC6wxAAAEAwBGMEQCICz/lLzYgK1O\r\nhcwcNsR6xF79jLBmvh00CtzloPGs0VWiAiAgTWpRa9zIx4H9pC/JAVZ9FGRo0+dc\r\nsnxf3s//Ie0nLAB1AFYUBpov18Ls0/XhvUSyPsdGdrm8mRFcwO+UmFXWidDdAAAB\r\na0wLrEoAAAQDAEYwRAIgfO3N9Rw0EvF5JnvmDCJoFK/byoEE2Z+aNGnmIMllhrcC\r\nIHlWCLOaAcjCK+f6RAlRiEA7JAfKFagbuUJ125LA98+5AHUAh3W/51l8+IxDmV+9\r\n827/Vo1HVjb/SrVgwbTq/16ggw8AAAFrTAutlAAABAMARjBEAiALTnGCAfyJ8lXZ\r\nRJC/10Zj29XeE6ejwofioEY05eAUwgIgfxsIMTKAP9HhsdX8Qqkvy+qBBFS9ptyn\r\nL2Oil6rMPBQwDQYJKoZIhvcNAQELBQADggEBAEVh28A/oOhzZusxKCxQphrVv5RZ\r\n77cVVfVjDoK915dVycQrJmCVUCA2z86rQgxzxWWpSQUUlszx49ryTk/MbormCLFr\r\nRv14cNQ5W5vgS7q0cRuFKcdRbUCUQKgL2QJr1Y0ZydQDkmDlbU/OzKywcRjUXG6b\r\nB7Kw9/q4rsO8dkyKA0nxykBgAxtame0FZLDgCOX9ZRC+Kj6+DkavvxbJkTsO5Lwj\r\n9T+lOEKtutXbNX+LC9W2WqeOAsXGvXfeV7BM4PUadaD8sNs8LE6FA2HYizMnkloa\r\nkClyGuHXJZ5LbUY4XwQ6bG9VlvYwFPX3CtQ8RZWwWSKYT1H3tFQERCiT2i8=\r\n-----END CERTIFICATE-----"
}

PLAY RECAP *********************************************************************
localhost                  : ok=2    changed=0    unreachable=0    failed=0
```

## Thanks

To [Johan Haals](https://github.com/jhaals) for writing the [ansible-vault](https://github.com/jhaals/ansible-vault) lookup module, which has been an inspiration and boilerplate for this plugin.

## Limitations / Known issues

Referencing objects via it's objectname is not yet implemented.

## Contributors

Oscar Mattsson  

## License

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
