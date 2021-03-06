# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import logging

from pants.backend.jvm.targets.import_jars_mixin import ImportJarsMixin
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField
from pants.build_graph.target import Target

logger = logging.getLogger(__name__)


class UnpackedJars(ImportJarsMixin, Target):
    """A set of sources extracted from JAR files.

    :API: public
    """

    imported_target_kwargs_field = "libraries"
    imported_target_payload_field = "library_specs"

    class ExpectedLibrariesError(Exception):
        """Thrown when the target has no libraries defined."""

        pass

    def __init__(
        self,
        payload=None,
        libraries=None,
        include_patterns=None,
        exclude_patterns=None,
        intransitive=False,
        **kwargs
    ):
        """
        :param list libraries: addresses of jar_library targets that specify the jars you want to unpack
        :param list include_patterns: fileset patterns to include from the archive
        :param list exclude_patterns: fileset patterns to exclude from the archive. Exclude patterns
          are processed before include_patterns.
        :param bool intransitive: Whether to unpack all resolved dependencies of the jars, or just
          the jars themselves.
        """
        payload = payload or Payload()
        payload.add_fields(
            {
                "library_specs": PrimitiveField(libraries or ()),
                "include_patterns": PrimitiveField(include_patterns or ()),
                "exclude_patterns": PrimitiveField(exclude_patterns or ()),
                "intransitive": PrimitiveField(intransitive),
            }
        )
        super().__init__(payload=payload, **kwargs)

        if not libraries:
            raise self.ExpectedLibrariesError(
                "Expected non-empty libraries attribute for {spec}".format(spec=self.address.spec)
            )
