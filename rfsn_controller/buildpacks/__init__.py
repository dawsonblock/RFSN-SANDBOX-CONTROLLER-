"""Buildpacks for multi-language repository support.

This module provides buildpack implementations for various programming
languages, enabling the RFSN Sandbox Controller to work with any public
repository regardless of language.
"""

from typing import List

from .base import (
    Buildpack,
    BuildpackType,
    BuildpackContext,
    DetectResult,
    Step,
    TestPlan,
    FailureInfo,
)
from .python_pack import PythonBuildpack
from .node_pack import NodeBuildpack
from .go_pack import GoBuildpack
from .rust_pack import RustBuildpack
from .java_pack import JavaBuildpack
from .dotnet_pack import DotnetBuildpack
from .polyrepo_pack import PolyrepoBuildpack

__all__ = [
    "Buildpack",
    "BuildpackType",
    "BuildpackContext",
    "DetectResult",
    "Step",
    "TestPlan",
    "FailureInfo",
    "PythonBuildpack",
    "NodeBuildpack",
    "GoBuildpack",
    "RustBuildpack",
    "JavaBuildpack",
    "DotnetBuildpack",
    "PolyrepoBuildpack",
    "get_buildpack",
    "get_all_buildpacks",
]


def get_buildpack(buildpack_type: BuildpackType) -> Buildpack:
    """Get a buildpack instance by type.

    Args:
        buildpack_type: The type of buildpack to get.

    Returns:
        A buildpack instance.

    Raises:
        ValueError: If the buildpack type is unknown.
    """
    buildpacks = {
        BuildpackType.PYTHON: PythonBuildpack,
        BuildpackType.NODE: NodeBuildpack,
        BuildpackType.GO: GoBuildpack,
        BuildpackType.RUST: RustBuildpack,
        BuildpackType.JAVA: JavaBuildpack,
        BuildpackType.DOTNET: DotnetBuildpack,
        BuildpackType.POLYREPO: PolyrepoBuildpack,
    }

    buildpack_class = buildpacks.get(buildpack_type)
    if buildpack_class is None:
        raise ValueError(f"Unknown buildpack type: {buildpack_type}")

    return buildpack_class()


def get_all_buildpacks() -> List[Buildpack]:
    """Get all available buildpack instances ordered by detection priority.

    Returns:
        List of all buildpack instances in priority order.
    """
    # Order by commonality for early termination optimization
    return [
        PythonBuildpack(),  # Most common
        NodeBuildpack(),    # Second most common
        JavaBuildpack(),    # Common in enterprise
        GoBuildpack(),      # Growing popularity
        RustBuildpack(),    # Less common
        DotnetBuildpack(),  # Enterprise
        PolyrepoBuildpack(),  # Last, expensive to detect
    ]
