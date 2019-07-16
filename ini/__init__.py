import json
import os
import re

__version__ = '1.0.0'


def encode(obj, opt=None):
    children = []
    out = ''

    if isinstance(opt, str):
        opt = {
            'section': opt,
            'whitespace': True
        }
    else:
        opt = opt or {}
        opt['whitespace'] = opt.get('whitespace', True)

    separator = ' = ' if opt['whitespace'] else '='

    for k, v in obj.items():
        if v and isinstance(v, list):
            for item in v:
                out += safe(k + '[]') + separator + safe(item) + '\n'
        elif v and isinstance(v, dict):
            children.append(k)
        else:
            out += safe(k) + separator + safe(v) + '\n'

    if opt.get('section') and len(out):
        out = '[' + safe(opt['section']) + ']' + '\n' + out

    for k in children:
        nk = '.'.join(_dot_split(k))
        section = (opt['section'] + '.' if opt.get('section') else '') + nk
        child = encode(obj[k], {
            'section': section,
            'whitespace': opt['whitespace']
        })
        if len(out) and len(child):
            out += '\n'
        out += child

    return out


def _dot_split(string):
    return re.sub(r'\\\.', '\u0001', string).split('.')


def decode(string):
    out = {}
    p = out
    section = None
    regex = re.compile(r'^\[([^\]]*)\]$|^([^=]+)(=(.*))?$', re.IGNORECASE)
    lines = re.split(r'[\r\n]+', string)

    for line in lines:
        if not line or re.match(r'^\s*[;#]', line):
            continue
        match = regex.match(line)
        if not match:
            continue
        if match[1]:
            section = unsafe(match[1])
            p = out[section] = out.get(section, {})
            continue
        key = unsafe(match[2])
        value = unsafe(match[4]) if match[3] else True
        if value in ('true', 'True'):
            value = True
        elif value in ('false', 'False'):
            value = False
        elif value in ('null', 'None'):
            value = None

        # Convert keys with '[]' suffix to an array
        if len(key) > 2 and key[-2:] == '[]':
            key = key[:-2]
            if key not in p:
                p[key] = []
            elif not isinstance(p[key], list):
                p[key] = [p[key]]

        # safeguard against resetting a previously defined
        # array by accidentally forgetting the brackets
        if isinstance(p.get(key), list):
            p[key].append(value)
        else:
            p[key] = value

    # {a:{y:1},"a.b":{x:2}} --> {a:{y:1,b:{x:2}}}
    # use a filter to return the keys that have to be deleted.
    for k in out.keys():
        if not out[k] or not isinstance(out[k], dict) or isinstance(out[k], list):
            continue
        # see if the parent section is also an object.
        # if so, add it to that, and mark this one for deletion
        parts = _dot_split(k)
        p = out
        l = parts.pop()
        nl = re.sub(r'\\\.', '.', l)
        for part in parts:
            if part not in p or not isinstance(p[part], dict):
                p[part] = {}
            p = p[part]
        if p == out and nl == l:
            continue
        p[nl] = out[k]
        del out[k]

    return out


def _is_quoted(val):
    return (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")


def safe(val):
    return json.dumps(val) if \
        (not isinstance(val, str) or
         re.match(r'[=\r\n]', val) or
         re.match(r'^\[', val) or
         (len(val) > 1 and _is_quoted(val)) or
         val != val.strip()) else \
        val.replace(';', '\\;').replace('#', '\\#')


def unsafe(val):
    val = (val or '').strip()
    if _is_quoted(val):
        # remove the single quotes before calling JSON.parse
        if val[0] == "'":
            val = val[1:-1]
        try:
            val = json.loads(val)
        except:
            pass
    else:
        # walk the val to find the first not-escaped ; character
        esc = False
        unesc = ''
        for i in range(len(val)):
            c = val[i]
            if esc:
                if c in '\\;#':
                    unesc += c
                else:
                    unesc += '\\' + c
                esc = False
            elif c in ';#':
                break
            elif c == '\\':
                esc = True
            else:
                unesc += c
        if esc:
            unesc += '\\'
        return unesc.strip()
    return val


parse = decode
stringify = encode