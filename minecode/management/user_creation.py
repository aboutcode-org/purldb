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

from scanpipe.models import APIToken


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
        parser.add_argument(
            "--generate-api-key",
            action="store_true",
            help="Generate an API key for this user and print it to the console.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        interactive = options["interactive"]
        verbosity = options["verbosity"]
        generate_api_key = options["generate_api_key"]
        self.create_user(
            username=username,
            interactive=interactive,
            verbosity=verbosity,
            generate_api_key=generate_api_key,
        )

    def create_user(self, username, interactive, verbosity, generate_api_key):
        error_msg = self._validate_username(username)
        if error_msg:
            raise CommandError(error_msg)

        password = None
        if interactive:
            password = self.get_password_from_stdin(username)

        user = self.UserModel._default_manager.create_user(username, password=password)

        if verbosity > 0:
            msg = f"User {username} created"
            self.stdout.write(msg, self.style.SUCCESS)

        if generate_api_key:
            plain_api_key = APIToken.create_token(user=user)
            self.stdout.write(f"API key: {plain_api_key}", self.style.SUCCESS)
            warning_msg = (
                "Treat your API key like a password and keep it secure. "
                "For security reasons, the key is only shown once at generation time. "
                "If you lose it, you will need to regenerate a new one."
            )
            self.stdout.write(warning_msg, self.style.WARNING)

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
