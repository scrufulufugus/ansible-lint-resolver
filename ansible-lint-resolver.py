#!/usr/bin/env python3

import argparse
import json
import sys
import re

KEY_VAL_RE = re.compile(r"^(?P<pre> *(- *)?)(?P<key>[\w_-]+)(?P<div>: *)(?P<value>\S*)(?P<post>.*)$")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Substitute ansible module names for fqcns')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--fqcn_file', help='Path to the file containing fqcns')
    args = parser.parse_args()
    return args

def bucket_problems(problems: dict):
    buckets = {}
    for issue in problems:
        issue_type = issue['check_name']
        if not buckets.get(issue_type):
            buckets[issue_type] = [issue]
        else:
            buckets[issue_type].append(issue)
    return buckets

def process_known_buckets(buckets: dict):
    if buckets.get('yaml[truthy]'):
        for issue in buckets['yaml[truthy]']:
            process_truthy(issue)
    if buckets.get('yaml[octal-values]'):
        for issue in buckets['yaml[octal-values]']:
            process_octal_values(issue)
    if buckets.get('name[casing]'):
        for issue in buckets['name[casing]']:
            process_name_casing(issue)
    if FQCNS and buckets.get('fqcn[action-core]'):
        for issue in buckets['fqcn[action-core]']:
            process_fqcn(issue)
    if FQCNS and buckets.get('fqcn[action]'):
        for issue in buckets['fqcn[action]']:
            process_fqcn(issue)

def process_truthy(issue: dict):
    truthy_dict = {
        'true': 'true',
        'false': 'false',
        'yes': 'true',
        'no': 'false'
    }

    loc = issue['location']['lines']['begin']-1
    with open(issue['location']['path'], 'r') as f:
        lines = f.readlines()
    match = KEY_VAL_RE.match(lines[loc])
    sub_val = truthy_dict.get(match.group('value').lower())
    if sub_val:
        lines[loc] = KEY_VAL_RE.sub(r"\g<pre>\g<key>: {}\g<post>".format(sub_val), lines[loc])

    with open(issue['location']['path'], 'w') as f:
        f.writelines(lines)

def process_octal_values(issue: dict):
    loc = issue['location']['lines']['begin']-1
    with open(issue['location']['path'], 'r') as f:
        lines = f.readlines()
    match = KEY_VAL_RE.match(lines[loc])
    lines[loc] = KEY_VAL_RE.sub(r'\g<pre>\g<key>: "\g<value>"\g<post>', lines[loc])

    with open(issue['location']['path'], 'w') as f:
        f.writelines(lines)

def process_name_casing(issue: dict):
    loc = issue['location']['lines']['begin']-1
    with open(issue['location']['path'], 'r') as f:
        lines = f.readlines()
    match = KEY_VAL_RE.match(lines[loc])
    sub_val = match.group('value').capitalize()
    if sub_val:
        lines[loc] = KEY_VAL_RE.sub(r"\g<pre>\g<key>: {}\g<post>".format(sub_val), lines[loc])

    with open(issue['location']['path'], 'w') as f:
        f.writelines(lines)

# Create a modules list by:
#  ansible-doc --list | awk '{print $1}' | grep '^.*\..*\..*$'
#  TODO: Handle this in code
FQCNS = {}
def store_fqcns(filename: str):
    with open(filename, 'r') as f:
        for line in f:
            line = line.rstrip()
            fqcn = line.split('.')
            name = fqcn[-1]
            collection = '.'.join(fqcn[:2])
            if FQCNS.get(name):
                FQCNS[name][collection] = line
            else:
                FQCNS[name] = {collection : line}

def get_fqcn(name: str):
    if FQCNS.get(name):
        group = FQCNS[name]
        if group.get('ansible.builtin'):
            return group['ansible.builtin']
        if group.get('ansible.posix'):
            return group['ansible.posix']
        if group.get('community.general'):
            return group['community.general']
        return next(iter(group))
    return None

# FIXME: This is a hack that assumes the module name is the first or second line of the task
#   ansible-lint need to be fixed to return the correct fail line
def process_fqcn(issue: dict):
    loc = issue['location']['lines']['begin']-1
    with open(issue['location']['path'], 'r') as f:
        lines = f.readlines()
    match = KEY_VAL_RE.match(lines[loc])
    # If our first line is a task name then skip
    if match.group('key') == 'name':
        loc+=1
        match = KEY_VAL_RE.match(lines[loc])
    sub_val = get_fqcn(match.group('key'))
    if sub_val:
        lines[loc] = KEY_VAL_RE.sub(r"\g<pre>{}\g<div>\g<value>\g<post>".format(sub_val), lines[loc])

    with open(issue['location']['path'], 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    args = parse_arguments()

    if args.fqcn_file:
        store_fqcns(args.fqcn_file)
    problems = json.load(args.infile)
    buckets = bucket_problems(problems)
    process_known_buckets(buckets)

    #print(buckets.keys())
