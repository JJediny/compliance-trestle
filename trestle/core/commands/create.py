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
"""Trestle Create Command."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Type

from ilcli import Command  # type: ignore

import trestle.oscal
from trestle.core import generators
from trestle.core.base_model import OscalBaseModel
from trestle.core.models.actions import CreatePathAction, WriteFileAction
from trestle.core.models.elements import Element
from trestle.core.models.file_content_type import FileContentType
from trestle.core.models.plans import Plan
from trestle.oscal import assessment_plan
from trestle.oscal import assessment_results
from trestle.oscal import catalog
from trestle.oscal import component
from trestle.oscal import poam
from trestle.oscal import profile
from trestle.oscal import ssp
from trestle.oscal import target
from trestle.utils import fs
from trestle.utils import log

logger = log.get_logger()


class CatalogCmd(Command):
    """Create a sample catalog in the trestle directory structure, given an OSCAL schema."""

    name = 'catalog'

    def _run(self, args: argparse.Namespace) -> int:
        """Create a sample catalog in the trestle directory structure, given an OSCAL schema."""
        logger.info(f'Creating catalog titled: {args.name}')
        return CreateCmd.create_object(self.name, catalog.Catalog, args)


class ProfileCmd(Command):
    """Create a sample profile."""

    name = 'profile'

    def _run(self, args: argparse.Namespace) -> int:
        logger.info(f'Creating profile titled: {args.name}')
        return CreateCmd.create_object(self.name, profile.Profile, args)


class TargetDefinitionCmd(Command):
    """Create a sample target definition."""

    name = 'target-definition'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, target.TargetDefinition, args)


class ComponentDefinitionCmd(Command):
    """Create a sample component definition."""

    name = 'component-definition'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, component.ComponentDefinition, args)


class SystemSecurityPlanCmd(Command):
    """Create a sample system security plan."""

    name = 'system-security-plan'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, ssp.SystemSecurityPlan, args)


class AssessmentPlanCmd(Command):
    """Create a sample assessment plan."""

    name = 'assessment-plan'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, assessment_plan.AssessmentPlan, args)


class AssessmentResultCmd(Command):
    """Create a sample assessment result."""

    name = 'assessment-results'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, assessment_results.AssessmentResults, args)


class PlanOfActionAndMilestonesCmd(Command):
    """Create a sample plan of action and milestones."""

    name = 'plan-of-action-and-milestones'

    def _run(self, args: argparse.Namespace) -> int:
        return CreateCmd.create_object(self.name, poam.PlanOfActionAndMilestones, args)


class CreateCmd(Command):
    """Create a sample OSCAL model in trestle project."""

    name = 'create'

    subcommands = [
        CatalogCmd,
        ProfileCmd,
        TargetDefinitionCmd,
        ComponentDefinitionCmd,
        SystemSecurityPlanCmd,
        AssessmentPlanCmd,
        AssessmentResultCmd,
        PlanOfActionAndMilestonesCmd
    ]

    def _init_arguments(self) -> None:
        self.add_argument('-n', '--name', help='Name of the model.', required=True)
        self.add_argument(
            '-x', '--extension', help='Type of file output.', choices=['json', 'yaml', 'yml'], default='json'
        )

    @classmethod
    def create_object(cls, model_alias: str, object_type: Type[OscalBaseModel], args: argparse.Namespace) -> int:
        """Create a top level OSCAL object within the trestle directory, leveraging functionality in add."""
        trestle_root = fs.get_trestle_project_root(Path.cwd())
        if not trestle_root:
            logger.error(f'Current working directory {Path.cwd()} is not with a trestle project.')
            return 1
        plural_path: str
        # Cater to POAM
        if model_alias[-1] == 's':
            plural_path = model_alias
        else:
            plural_path = model_alias + 's'

        desired_model_dir = trestle_root / plural_path / args.name

        desired_model_path = desired_model_dir / (model_alias + '.' + args.extension)

        if desired_model_path.exists():
            logger.error(f'OSCAL file to be created here: {desired_model_path} exists.')
            logger.error('Aborting trestle create.')
            return 1

        # Create sample model.
        sample_model = generators.generate_sample_model(object_type)
        # Presuming top level level model not sure how to do the typing for this.
        sample_model.metadata.title = f'Generic {model_alias} created by trestle.'  # type: ignore
        sample_model.metadata.last_modified = datetime.now().astimezone()
        sample_model.metadata.oscal_version = trestle.oscal.OSCAL_VERSION
        sample_model.metadata.version = '0.0.0'

        top_element = Element(sample_model, model_alias)

        create_action = CreatePathAction(desired_model_path.absolute(), True)
        write_action = WriteFileAction(
            desired_model_path.absolute(), top_element, FileContentType.to_content_type(desired_model_path.suffix)
        )

        # create a plan to write the directory and file.
        try:
            create_plan = Plan()
            create_plan.add_action(create_action)
            create_plan.add_action(write_action)
            create_plan.simulate()
            create_plan.execute()
            return 0
        except Exception as e:
            logger.error('Unknown error executing trestle create operations. Rolling back.')
            logger.debug(e)
            return 1
