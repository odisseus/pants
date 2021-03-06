# Copyright 2018 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from pants.task.target_restriction_mixins import (
    DeprecatedSkipAndDeprecatedTransitiveGoalOptionsRegistrar,
    HasSkipAndTransitiveGoalOptionsMixin,
)


class LintTaskMixin(HasSkipAndTransitiveGoalOptionsMixin):
    """A mixin to combine with lint tasks."""

    goal_options_registrar_cls = DeprecatedSkipAndDeprecatedTransitiveGoalOptionsRegistrar
    target_filtering_enabled = True
