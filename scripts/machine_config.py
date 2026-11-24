#!/usr/bin/env python3
"""Machine configs: configs/machines/<name>.yaml, validated (unknown keys rejected).

Usage:
  machine_config.py detect             print the machine whose hostname patterns match
  machine_config.py show [NAME]        print the validated config (default: detected)
  machine_config.py validate           validate every configs/machines/*.yaml

The files use a strict YAML subset parsed with the standard library: block mappings,
block lists of scalars, plain or quoted scalars, `#` comments. Anything else (flow
collections, anchors, multi-line strings, tabs) is an error, never a guess. All values
are strings; `unknown` marks a fact not verified yet (scripts treat it as unavailable).
Standard library only; runs on Python >= 3.6.
"""
import argparse
import fnmatch
import json
import re
import socket
import sys
from pathlib import Path

DEFAULT_REPO = Path(__file__).resolve().parent.parent
UNKNOWN = "unknown"

# Schema: dict = mapping with exactly these keys; [str] = non-empty list of strings;
# str = string. Every key is required; unknown keys are rejected.
SCHEMA = {
    "name": str,
    "hostnames": [str],
    "scheduler": str,
    "cost": {"unit": str, "source": str},
    "storage": {
        "repo_parent": str,
        "store_parent": str,
        "purge": str,
        "notes": str,
    },
    "partitions": [str],
    "toy_job_partition": str,
    "modules": {"cp2k": str, "gromacs": str, "lammps": str},
    "python": {"conda_sh": str, "module": str, "envs": [str]},
}
ALLOWED = {"scheduler": {"slurm"}, "cost.source": {"sacct", UNKNOWN}}


class ConfigError(Exception):
    pass


# ---------- strict YAML subset ----------
def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text, where):
    t = text.strip()
    if not t:
        raise ConfigError("{}: empty value".format(where))
    if t[0] in "'\"":
        if len(t) < 2 or t[-1] != t[0]:
            raise ConfigError("{}: unterminated quote".format(where))
        return t[1:-1]
    if t[0] in "[{&*!|>@`%":
        raise ConfigError("{}: unsupported YAML syntax {!r}".format(where, t))
    return t


def parse_yaml(text, src="<yaml>"):
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise ConfigError("{}:{}: tab character".format(src, n))
        body = _strip_comment(raw)
        if body.strip() in ("---", "..."):
            raise ConfigError("{}:{}: document markers not supported".format(src, n))
        if body.strip():
            lines.append((n, len(body) - len(body.lstrip(" ")), body.strip()))
    if not lines:
        raise ConfigError("{}: empty file".format(src))
    value, pos = _block(lines, 0, lines[0][1], src)
    if pos != len(lines):
        n = lines[pos][0]
        raise ConfigError("{}:{}: unexpected indentation".format(src, n))
    return value


def _block(lines, pos, indent, src):
    if lines[pos][2].startswith("- ") or lines[pos][2] == "-":
        return _list(lines, pos, indent, src)
    return _mapping(lines, pos, indent, src)


def _list(lines, pos, indent, src):
    out = []
    while pos < len(lines) and lines[pos][1] == indent:
        n, _, body = lines[pos]
        if not body.startswith("- "):
            raise ConfigError("{}:{}: expected '- item'".format(src, n))
        item = body[2:]
        if re.match(r"^[^'\"]*:(\s|$)", item):
            raise ConfigError("{}:{}: lists of mappings not supported".format(src, n))
        out.append(_scalar(item, "{}:{}".format(src, n)))
        pos += 1
    return out, pos


def _mapping(lines, pos, indent, src):
    out = {}
    while pos < len(lines) and lines[pos][1] == indent:
        n, _, body = lines[pos]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$", body)
        if not m:
            raise ConfigError("{}:{}: expected 'key: value'".format(src, n))
        key, rest = m.group(1), m.group(2)
        if key in out:
            raise ConfigError("{}:{}: duplicate key {!r}".format(src, n, key))
        pos += 1
        if rest:
            out[key] = _scalar(rest, "{}:{}".format(src, n))
        else:
            if pos >= len(lines) or lines[pos][1] <= indent:
                raise ConfigError("{}:{}: {!r} has no value".format(src, n, key))
            out[key], pos = _block(lines, pos, lines[pos][1], src)
    if pos < len(lines) and lines[pos][1] > indent:
        raise ConfigError("{}:{}: unexpected indentation".format(src, lines[pos][0]))
    return out, pos


# ---------- schema ----------
def _check(value, schema, path, errors):
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            errors.append("{}: expected a mapping".format(path or "<root>"))
            return
        for k in sorted(set(value) - set(schema)):
            errors.append("{}: unknown key".format(".".join(filter(None, [path, k]))))
        for k in sorted(set(schema) - set(value)):
            errors.append("{}: missing key".format(".".join(filter(None, [path, k]))))
        for k in sorted(set(schema) & set(value)):
            _check(value[k], schema[k], ".".join(filter(None, [path, k])), errors)
    elif isinstance(schema, list):
        if not isinstance(value, list) or not value:
            errors.append("{}: expected a non-empty list".format(path))
            return
        for i, v in enumerate(value):
            _check(v, schema[0], "{}[{}]".format(path, i), errors)
    elif not isinstance(value, str):
        errors.append("{}: expected a string".format(path))
    elif path in ALLOWED and value not in ALLOWED[path]:
        errors.append("{}: {!r} not in {}".format(path, value, sorted(ALLOWED[path])))


def validate(cfg, expected_name):
    errors = []
    _check(cfg, SCHEMA, "", errors)
    if not errors:
        if cfg["name"] != expected_name:
            errors.append("name: {!r} does not match file name {!r}".format(cfg["name"], expected_name))
        tp = cfg["toy_job_partition"]
        if tp != UNKNOWN and tp not in cfg["partitions"]:
            errors.append("toy_job_partition: {!r} not in partitions".format(tp))
    if errors:
        raise ConfigError("{}.yaml:\n  {}".format(expected_name, "\n  ".join(errors)))
    return cfg


# ---------- API ----------
def machines_dir(repo):
    return Path(repo) / "configs" / "machines"


def load(name, repo=DEFAULT_REPO):
    path = machines_dir(repo) / "{}.yaml".format(name)
    if not path.is_file():
        raise ConfigError("no config for machine {!r} ({})".format(name, path))
    with open(str(path)) as f:
        return validate(parse_yaml(f.read(), str(path)), name)


def load_all(repo=DEFAULT_REPO):
    return {p.stem: load(p.stem, repo) for p in sorted(machines_dir(repo).glob("*.yaml"))}


def detect(repo=DEFAULT_REPO, hostname=None):
    host = hostname or socket.gethostname()
    names = {host, host.split(".")[0]}
    hits = sorted(n for n, c in load_all(repo).items()
                  if any(fnmatch.fnmatchcase(h, pat) for h in names for pat in c["hostnames"]))
    if len(hits) != 1:
        raise ConfigError("hostname {!r} matches {} machine configs: {}".format(
            host, len(hits), hits or "none"))
    return hits[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help=argparse.SUPPRESS)
    ap.add_argument("cmd", choices=["detect", "show", "validate"])
    ap.add_argument("name", nargs="?")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "detect":
            print(detect(a.repo))
        elif a.cmd == "show":
            print(json.dumps(load(a.name or detect(a.repo), a.repo), indent=2))
        else:
            cfgs = load_all(a.repo)
            if not cfgs:
                raise ConfigError("no configs in {}".format(machines_dir(a.repo)))
            for n in cfgs:
                print("OK {}".format(n))
        return 0
    except ConfigError as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
