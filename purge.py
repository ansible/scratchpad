#!/usr/bin/env python
"""Purge old tags from a quay.io repository."""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import typing as t
import urllib
import urllib.request

T = t.TypeVar('T')


def main() -> None:
    """Main program entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', help='repository to purge')
    parser.add_argument('age', type=int, help='minimum tag age in seconds to purge')
    parser.add_argument('--purge', action='store_true', help='purge the matching tags')

    args = parser.parse_args()

    token = os.environ['QUAY_TOKEN']
    config = deserialize(args.__dict__, Config)
    headers = dict(Authorization=f'Bearer {token}')
    endpoint = f'https://quay.io/api/v1/repository/{config.repository}/tag/'

    request = urllib.request.Request(url=f'{endpoint}?onlyActiveTags=true', headers=headers)

    with urllib.request.urlopen(request) as response:
        data = json.load(response)

    tags = [deserialize(value, Tag) for value in data['tags']]
    expired_tags = [tag for tag in tags if tag.age.total_seconds() > config.age]

    for tag in expired_tags:
        print(f'{config.repository}:{tag.name}  {int(tag.age.total_seconds())}  [{tag.age}]', end='  ' if config.purge else '\n')

        if config.purge:
            request = urllib.request.Request(url=f'{endpoint}{tag.name}', method='DELETE', headers=headers)
            urllib.request.urlopen(request)
            print('deleted')


def deserialize(value: t.Dict[str, t.Any], value_type: t.Type[T]) -> T:
    """Deserialize the given dict as the specified dataclass type and return the result."""
    kvp = {field.name: value.get(field.name) for field in dataclasses.fields(value_type)}
    return value_type(**kvp)


@dataclasses.dataclass(frozen=True)
class Config:
    """Command line arguments."""
    repository: str
    age: int
    purge: bool


@dataclasses.dataclass(frozen=True)
class Tag:
    """A single tag from a quay.io repository."""
    name: str
    reversion: bool
    start_ts: int
    manifest_digest: str
    is_manifest_list: bool
    size: int
    last_modified: str

    @property
    def last_modified_datetime(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.last_modified, '%a, %d %b %Y %H:%M:%S %z')

    @property
    def age(self) -> datetime.timedelta:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0) - self.last_modified_datetime


if __name__ == '__main__':
    main()
