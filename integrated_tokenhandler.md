# Integrating token handler with ansible.

To avoid having to consistently check for valid storedsafe token, this can be integrated directly into ansible via a pre_task.

## ansible pre task example

In a playbook that requires a valid token, or site.yml, add the following:

```
- hosts: all
  gather_facts: True
  pre_tasks:
    - name: obtain storedsafe toke
  ansible.builtin.command:
    cmd: ../../tokenhandler/wrapper.sh
  delegate_to: localhost
  become: no
  run_once: true
```
run_once is necessary to only call login once. 
wrapper.sh is just a simple wrapper:

```
#!/usr/bin/bash
# relative to ansible/playbooks/
TOKENHANDLER=../../tokenhandler/tookenhandler.py 
${TOKENHANDLER} check > /dev/null
if [ $? -eq 1 ]; then
  ${TOKENHANDLER} login
else
  exit 0
fi
```
