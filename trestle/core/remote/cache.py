# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2020 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Trestle cache operations library.

Allows for using uris to reference external directories and then expand.
"""

import pathlib
import shutil
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from trestle.core import const
from trestle.core.base_model import OscalBaseModel
from trestle.core.err import TrestleError
from trestle.utils import log

logger = log.get_logger()


class FetcherBase(ABC):
    """FetcherBase - base class for fetching remote oscal objects."""

    def __init__(
        self,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = True,
        cache_only: bool = False
    ) -> None:
        """Intialize fetcher base.

        Refresh: whether or not the cache should be refreshed
        """
        logger.debug('Initializing FetcherBase')
        self._inst_cache_path: pathlib.Path
        self._uri = uri
        self._refresh = refresh
        self._fail_hard = fail_hard
        self._cache_only = cache_only
        self._trestle_cache_path = trestle_root / const.TRESTLE_CONFIG_DIR / 'cache'

        # ensure trestle cache directory exists.
        self._trestle_cache_path.mkdir(exist_ok=True)

    @abstractmethod
    def _update_cache(self) -> None:
        """Fetch a object from a remote source.

        This contains the underlying logic to update the cache.
        """

    def get_raw(self) -> Dict[str, Any]:
        """Get the raw dictionary representing the underlying object."""
        self._update_cache()
        # Results are now in the cache.
        pass

    def get_oscal(self, model_type: Type[OscalBaseModel]) -> OscalBaseModel:
        """Retrieve the cached file as a particular OSCAL model."""
        pass

    def in_cache(self) -> bool:
        """Return whether object is contained within the cache or not."""
        return self._inst_cache_path.exists()


class LocalFetcher(FetcherBase):
    """Fetcher for local content."""

    def __init__(
        self,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = True,
        cache_only: bool = False
    ) -> None:
        """Initialize local fetcher."""
        super.__init__(uri, refresh, fail_hard, cache_only)
        # Normalize uri to a root file.
        if 'file:///' == uri[0:8]:
            uri = uri[7:]
        path = pathlib.Path(uri).absolute()
        self._abs_path = path
        localhost_cached_dir = self._trestle_cache_path / 'localhost'
        localhost_cached_dir.mkdir(exist_ok=True)
        self._inst_cache_path = localhost_cached_dir / path

    def _update_cache(self) -> None:
        # Step one discover whether
        if self._cache_only:
            # Don't update if cache only.
            return
        if not self._inst_cache_path.exists() or self._refresh:
            try:
                shutil.copy(self._abs_path, self._inst_cache_path)
            except Exception as e:
                logger.error(f'Unable to update cache for {self._uri}')
                logger.debug(e)
                raise TrestleError(f'Cache update failure for {self._uri}')


class HTTPSFetcher(FetcherBase):
    """Fetcher for https content."""

    # Use request: https://requests.readthedocs.io/en/master/
    def __init__(
        self,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = False,
        cache_only: bool = False
    ) -> None:
        """Initialize HTTPS fetcher."""
        super.__init__(uri, refresh, fail_hard, cache_only)

    def _update_cache(self) -> None:
        pass


class SFTPFetcher(FetcherBase):
    """Fetcher for https content."""

    # STFP method: https://stackoverflow.com/questions/7563496/open-a-remote-file-using-paramiko-in-python-slow#7563551
    # For SFTP fetch into memory.
    def __init__(
        self,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = False,
        cache_only: bool = False
    ) -> None:
        """Initialize STFP fetcher."""
        super.__init__(uri, refresh, fail_hard, cache_only)

    def _update_cache(self) -> None:
        pass


class GithubFetcher(HTTPSFetcher):
    """Github fetcher which supports both github and GHE URLs."""

    def __init__(
        self,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = False,
        cache_only: bool = False
    ) -> None:
        """Initialize github specific fetcher."""
        super.__init__(uri, refresh, fail_hard, cache_only)

    def _update_cache(self) -> None:
        pass


class FetcherFactory(object):
    """Factory method for creating a fetcher."""

    def __init__(self) -> None:
        """Initialize fetcher factory."""
        pass

    @classmethod
    def get_fetcher(
        cls,
        trestle_root: pathlib.Path,
        uri: str,
        refresh: bool = False,
        fail_hard: bool = False,
        cache_only: bool = False
    ) -> FetcherBase:
        """Return an instaciated fetcher object based on the uri."""
        # Basic correctness test
        if len(uri) <= 9 or '/' not in uri:
            raise TrestleError(f'Unable to fetch uri as it appears to be invalid {uri}')

        if uri[0] == '/' or 'file:///' == uri[0:8]:
            # Note assumption here is that relative paths are only supported within
            # trestle directories. This simplification is to ensure
            return LocalFetcher(uri, refresh, fail_hard, cache_only)
        elif 'stfp://' == uri[0:7]:
            return SFTPFetcher(uri, refresh, fail_hard, cache_only)
        elif 'https://' == uri[0:8]:
            # Test for github uri assumption - must be first after basic auth (if it exists)
            cleaned = uri[8:]
            # tests for special scenarios
            if cleaned.split('@')[-1][0:7] == 'github.':
                return GithubFetcher(uri, refresh, fail_hard, cache_only)
            else:
                return HTTPSFetcher(uri, refresh, fail_hard, cache_only)
        else:
            raise TrestleError(f'Unable to fetch uri: {uri} as the uri did not match a suppported format.')