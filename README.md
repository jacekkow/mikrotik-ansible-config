# Mikrotik configuration using Ansible

Automatic reconfiguration of selected configuration subtrees
(`/interface bonding`, `/interface bridge port`,
`/interface bridge vlan`, `/interface ethernet switch port`)
using Ansible + network_cli and custom filters.

Python filters in filter_plugins directory contain functions
to parse and diff `export terse` outputs.

This example assumes that you have a switch at `192.168.88.1`
and you can directly connect to it via SSH.

Note that running `mikrotik.yml` playbook will make you loose
connectivity by default as it configures `ether1` PVID to `10`,
while not configuring any interfaces there!

You can dry-run playbook by skipping the `apply` tag:
`ansible-playbook mikrotik.yml --skip-tags apply`
