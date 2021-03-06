# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from dataclasses import dataclass
from typing import Optional, Tuple

from pants.backend.python.lint.flake8.subsystem import Flake8
from pants.backend.python.lint.python_lint_target import PythonLintTarget
from pants.backend.python.rules import download_pex_bin, pex
from pants.backend.python.rules.pex import (
    CreatePex,
    Pex,
    PexInterpreterConstraints,
    PexRequirements,
)
from pants.backend.python.subsystems import python_native_code, subprocess_environment
from pants.backend.python.subsystems.subprocess_environment import SubprocessEncodingEnvironment
from pants.engine.fs import Digest, DirectoriesToMerge, PathGlobs, Snapshot
from pants.engine.isolated_process import ExecuteProcessRequest, FallibleExecuteProcessResult
from pants.engine.legacy.structs import PythonTargetAdaptor, TargetAdaptorWithOrigin
from pants.engine.rules import UnionRule, rule, subsystem_rule
from pants.engine.selectors import Get
from pants.option.global_options import GlobMatchErrorBehavior
from pants.python.python_setup import PythonSetup
from pants.rules.core import find_target_source_files, strip_source_roots
from pants.rules.core.find_target_source_files import (
    FindTargetSourceFilesRequest,
    TargetSourceFiles,
)
from pants.rules.core.lint import LintResult


@dataclass(frozen=True)
class Flake8Target:
    adaptor_with_origin: TargetAdaptorWithOrigin


def generate_args(*, source_files: TargetSourceFiles, flake8: Flake8) -> Tuple[str, ...]:
    args = []
    if flake8.options.config is not None:
        args.append(f"--config={flake8.options.config}")
    args.extend(flake8.options.args)
    args.extend(sorted(source_files.snapshot.files))
    return tuple(args)


@rule(name="Lint using Flake8")
async def lint(
    flake8_target: Flake8Target,
    flake8: Flake8,
    python_setup: PythonSetup,
    subprocess_encoding_environment: SubprocessEncodingEnvironment,
) -> LintResult:
    if flake8.options.skip:
        return LintResult.noop()

    adaptor_with_origin = flake8_target.adaptor_with_origin
    adaptor = adaptor_with_origin.adaptor

    # NB: Flake8 output depends upon which Python interpreter version it's run with. We ensure that
    # each target runs with its own interpreter constraints. See
    # http://flake8.pycqa.org/en/latest/user/invocation.html.
    interpreter_constraints = PexInterpreterConstraints.create_from_adaptors(
        adaptors=[adaptor] if isinstance(adaptor, PythonTargetAdaptor) else [],
        python_setup=python_setup,
    )
    requirements_pex = await Get[Pex](
        CreatePex(
            output_filename="flake8.pex",
            requirements=PexRequirements(requirements=tuple(flake8.get_requirement_specs())),
            interpreter_constraints=interpreter_constraints,
            entry_point=flake8.get_entry_point(),
        )
    )

    config_path: Optional[str] = flake8.options.config
    config_snapshot = await Get[Snapshot](
        PathGlobs(
            globs=tuple([config_path] if config_path else []),
            glob_match_error_behavior=GlobMatchErrorBehavior.error,
            description_of_origin="the option `--flake8-config`",
        )
    )

    merged_input_files = await Get[Digest](
        DirectoriesToMerge(
            directories=(
                adaptor.sources.snapshot.directory_digest,
                requirements_pex.directory_digest,
                config_snapshot.directory_digest,
            )
        ),
    )

    source_files = await Get[TargetSourceFiles](FindTargetSourceFilesRequest(adaptor_with_origin))

    request = requirements_pex.create_execute_request(
        python_setup=python_setup,
        subprocess_encoding_environment=subprocess_encoding_environment,
        pex_path=f"./flake8.pex",
        pex_args=generate_args(source_files=source_files, flake8=flake8),
        input_files=merged_input_files,
        description=f"Run Flake8 for {adaptor.address.reference()}",
    )
    result = await Get[FallibleExecuteProcessResult](ExecuteProcessRequest, request)
    return LintResult.from_fallible_execute_process_result(result)


def rules():
    return [
        lint,
        subsystem_rule(Flake8),
        UnionRule(PythonLintTarget, Flake8Target),
        *download_pex_bin.rules(),
        *find_target_source_files.rules(),
        *pex.rules(),
        *python_native_code.rules(),
        *strip_source_roots.rules(),
        *subprocess_environment.rules(),
    ]
