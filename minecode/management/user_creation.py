#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from rest_framework.authtoken.models import Token


class CreateUserCommand(BaseCommand):
    help = "Create a user and generate an API key for authentication."
    requires_migrations_checks = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)

    def add_arguments(self, parser):
        parser.add_argument("username", help="Specifies the username for the user.")
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt the user for input of any kind.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        interactive = options["interactive"]
        verbosity = options["verbosity"]
        self.create_user(username=username, interactive=interactive, verbosity=verbosity)

    def create_user(self, username, interactive, verbosity):
        error_msg = self._validate_username(username)
        if error_msg:
            raise CommandError(error_msg)

        password = None
        if interactive:
            password = self.get_password_from_stdin(username)

        user = self.UserModel._default_manager.create_user(username, password=password)
        token, _ = Token._default_manager.get_or_create(user=user)

        if verbosity >= 1:
            msg = f"User {username} created with API key: {token.key}"
            self.stdout.write(msg, self.style.SUCCESS)

        return user

    def get_password_from_stdin(self, username):
        # Validators, such as UserAttributeSimilarityValidator, depends on other user's
        # fields data for password validation.
        fake_user_data = {
            self.UserModel.USERNAME_FIELD: username,
        }

        password = None
        while password is None:
            password1 = getpass.getpass()
            password2 = getpass.getpass("Password (again): ")
            if password1 != password2:
                self.stderr.write("Error: Your passwords didn't match.")
                continue
            if password1.strip() == "":
                self.stderr.write("Error: Blank passwords aren't allowed.")
                continue
            try:
                validate_password(password2, self.UserModel(**fake_user_data))
            except exceptions.ValidationError as err:
                self.stderr.write("\n".join(err.messages))
                response = input("Bypass password validation and create user anyway? [y/N]: ")
                if response.lower() != "y":
                    continue
            password = password1

        return password

    def _validate_username(self, username):
        """Validate username. If invalid, return a string error message."""
        if self.username_field.unique:
            try:
                self.UserModel._default_manager.get_by_natural_key(username)
            except self.UserModel.DoesNotExist:
                pass
            else:
                return "Error: That username is already taken."

        try:
            self.username_field.clean(username, None)
        except exceptions.ValidationError as e:
            return "; ".join(e.messages)
