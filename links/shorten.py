#!/usr/bin/env python3

"""
short.py generates unique short URLs.

This script reads lines from stdin or files named as arguments, then:

1. retrieves or creates new short URLs, taking into account existing RedirectTemp
   directives in custom.htaccess or short.htaccess;
2. appends RedirectTemp directives for newly created short URLs to short.htaccess;
3. outputs the list of (short, long) URLs retrieved or created.

"""

import fileinput
import itertools
from collections.abc import Iterator
from time import strftime

HTACCESS_CUSTOM = 'custom.htaccess'
HTACCESS_SHORT = 'short.htaccess'
HTACCESS_FILES = (HTACCESS_CUSTOM, HTACCESS_SHORT)
BASE_DOMAIN = 'fpy.li'


def load_redirects() -> tuple[dict, dict]:
    redirects = {}
    targets = {}
    for filename in HTACCESS_FILES:
        with open(filename) as fp:
            for line in fp:
                if line.startswith('RedirectTemp'):
                    _, short, long = line.split()
                    short = short[1:]  # Remove leading slash
                    assert short not in redirects, f'{filename}: duplicate redirect from {short}'
                    # htaccess.custom is live since 2022, we can't change it remove duplicate targets
                    if filename != HTACCESS_CUSTOM:
                        assert long not in targets, f'{filename}: duplicate redirect to {long}'
                    redirects[short] = long
                    targets[long] = short
    return redirects, targets


SDIGITS = '23456789abcdefghjkmnpqrstvwxyz'


def gen_short(start_len=1) -> Iterator[str]:
    """Generate every possible sequence of SDIGITS, starting with start_len"""
    length = start_len
    while True:
        for short in itertools.product(SDIGITS, repeat=length):
            yield ''.join(short)
        length += 1


def gen_unused_short(redirects: dict) -> Iterator[str]:
    """Generate next available short URL of len >= 2."""
    for short in gen_short(2):
        if short not in redirects:
            yield short


def shorten(urls: list[str]) -> list[tuple[str, str]]:
    """Return (short, long) pairs, appending directives to HTACCESS_SHORT as needed."""
    redirects, targets = load_redirects()
    iter_short = gen_unused_short(redirects)
    pairs = []
    timestamp = strftime('%Y-%m-%d %H:%M:%S')
    with open(HTACCESS_SHORT, 'a') as fp:
        for long in urls:
            assert BASE_DOMAIN not in long, f'{long} is a {BASE_DOMAIN} URL'
            if long in targets:
                short = targets[long]
            else:
                short = next(iter_short)
                redirects[short] = long
                targets[long] = short
                if timestamp:
                    fp.write(f'\n# appended: {timestamp}\n')
                    timestamp = None
                fp.write(f'RedirectTemp /{short} {long}\n')
            pairs.append((short, long))

    return pairs


def main() -> None:
    """read URLS from filename arguments or stdin"""
    urls = [line.strip() for line in fileinput.input(encoding='utf-8')]
    for short, long in shorten(urls):
        print(f'{BASE_DOMAIN}/{short}\t{long}')


if __name__ == '__main__':
    main()
