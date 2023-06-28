# ansible-lint-resolver
A simple script to solve the most common ansible linting issues

## Current Status

This script is currently being prototyped. Resolvers work with **major** caveats and _will probably break some playbooks_.

## Usage

Create a list of modules:
``` sh
ansible-doc --list | awk '{print $1}' | grep '^.*\..*\..*$' > module_list.txt
```

Run on `ansible-lint` output:
``` sh
ansible-lint -f json | python ansible-lint-resolver.py --fqcn_file ansible_fqcns.txt
```
