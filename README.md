# ansible-storedsafe lookup module

This is a lookup module for information stored in [StoredSafe](https://storedsafe.com/). Supports Ansible 2.4 or better.

## Installation

This plugin requires Ansible v2.4 and the Python [```requests```](http://docs.python-requests.org/en/master/) library. 

It has been developed and tested using Python v2.7.12, on Ubuntu 16.04.3 LTS.

Most of the required libraries are installed by default, but requests require manual installation.

**requests:**
```
sudo -H pip install requests
```

Lookup plugins can be loaded from several different locations similar to `$PATH`, see
[lookup_plugins](http://docs.ansible.com/ansible/intro_configuration.html#lookup-plugins).

The source for the plugin can be pointed to via a _requirements.yml_ file, and accessed via [`ansible-galaxy`](http://docs.ansible.com/ansible/galaxy.html).

## Configuration

Both the StoredSafe server address and the StoredSafe token can be read from the file `$HOME/.storedsafe.rc`, which can be created and maintained by [`storedsafe-tokenhandler`](https://github.com/storedsafe/tokenhandler).

Or it can be done with environment variables or Ansible variables. If any parameter is set by both an environment variable and an alternative means, the environment variable takes precedence.

To specify the address to the StoredSafe server:

    export STOREDSAFE_SERVER=safe.domain.cc

To specify a StoredSafe auth token:

    export STOREDSAFE_TOKEN=<StoredSafe-Token>

The StoredSafe token intentionally can **not** be set via an Ansible variable, as this is generally checked into revision control and would be a bad security practice, defeating the purpose of using StoredSafe. 


The plugin also supports specifying the list of trusted CAs either thru by using the ```STOREDSAFE_CABUNDLE``` variables which can either point to a single file or a directory.

	export STOREDSAFE_CABUNDLE=/etc/pki/tls/ca.crt
	export STOREDSAFE_CABUNDLE=/etc/pki/tls

To disable verification (**NOT RECOMMDED**) the ```STOREDSAFE_SKIP_VERIFY``` variable can be set.

	export STOREDSAFE_SKIP_VERIFY=True

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

## Thanks

To [Johan Haals](https://github.com/jhaals) for writing the [ansible-vault](https://github.com/jhaals/ansible-vault) lookup module, which has been an inspiration and boilerplate for this plugin.

## Limitations / Known issues

Referencing objects via it's objectname is not yet implemented.

## License
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
