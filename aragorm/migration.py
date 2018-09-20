#!/usr/bin/env python

import datetime
import importlib.util
import os
import sys
from typing import List, Dict
from types import ModuleType

import click

from aragorm.migrations.template import TEMPLATE
from aragorm.migrations.table import Migration


MIGRATIONS_FOLDER = os.path.join(os.getcwd(), 'migrations')
MIGRATION_MODULES: Dict[str, ModuleType] = {}


def _create_migrations_folder() -> bool:
    """
    Creates the folder that migrations live in. Returns True/False depending
    on whether it was created or not.
    """
    if os.path.exists(MIGRATIONS_FOLDER):
        return False
    else:
        os.mkdir(MIGRATIONS_FOLDER)
        for filename in ('__init__.py', 'config.py'):
            with open(os.path.join(MIGRATIONS_FOLDER, filename), 'w'):
                pass
        return True


def _create_new_migration() -> None:
    """
    Creates a new migration file on disk.
    """
    _id = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    path = os.path.join(MIGRATIONS_FOLDER, f'{_id}.py')
    with open(path, 'w') as f:
        f.write(TEMPLATE.format(migration_id=_id))


###############################################################################

@click.command()
def new():
    """
    Creates a new file like migrations/0001_add_user_table.py
    """
    print('Creating new migration ...')
    _create_migrations_folder()
    _create_new_migration()


###############################################################################

def _create_migration_table() -> bool:
    """
    Creates the migration table in the database. Returns True/False depending
    on whether it was created or not.
    """
    if not Migration.table_exists().run_sync():
        Migration.create().run_sync()
        return True
    return False


def _get_migrations_which_ran() -> List[str]:
    """
    Returns the names of migrations which have already run, by inspecing the
    database.
    """
    return [i['name'] for i in Migration.select('name').run_sync()]


def _get_migration_modules() -> None:
    """
    """
    folder_contents = os.listdir(MIGRATIONS_FOLDER)
    excluded = ('__init__.py', 'config.py', '__pycache__')
    migration_names = [
        i.split('.py')[0] for i in folder_contents if i not in excluded
    ]
    modules = [importlib.import_module(name) for name in migration_names]
    global MIGRATION_MODULES
    for m in modules:
        _id = getattr(m, 'ID', None)
        if _id:
            MIGRATION_MODULES[_id] = m


def _get_migration_ids() -> List[str]:
    return list(MIGRATION_MODULES.keys())


def _get_config() -> dict:
    """
    A config file is required for the database credentials.
    """
    sys.path.insert(0, MIGRATIONS_FOLDER)

    config_file = os.path.join(MIGRATIONS_FOLDER, 'config.py')
    if not os.path.exists(config_file):
        raise Exception(f"Can't find config.py in {MIGRATIONS_FOLDER}")

    config = importlib.import_module('config')

    db = getattr(config, 'DB', None)
    if not db:
        raise Exception('config.py is missing a DB dictionary.')
    return db


@click.command()
def run():
    """
    Runs any migrations which haven't been run yet, or up to a specific
    migration.
    """
    print('Running migrations ...')
    sys.path.insert(0, os.getcwd())

    Migration.Meta.db = _get_config()

    _create_migration_table()

    already_ran = _get_migrations_which_ran()
    print(f'Already ran = {already_ran}')

    # TODO - stop using globals ...
    _get_migration_modules()
    ids = _get_migration_ids()
    print(f'Migration ids = {ids}')

    for _id in (set(ids) - set(already_ran)):
        MIGRATION_MODULES[_id].forwards()
        print(f'Ran {_id}')
        Migration.insert().add(
            Migration(name=_id)
        ).run_sync()


###############################################################################

@click.command()
@click.argument('migration_name')
def undo(migration_name: str):
    """
    Undo migrations up to a specific migrations.

    - make sure the migration name is valid
    - work out which to undo, and in which order
    - ask for confirmation
    - apply the undo operations one by one
    """
    # Get the list from disk ...
    sys.path.insert(0, os.getcwd())
    _get_config()  # Just required for path manipulation - needs changing
    _get_migration_modules()

    migration_ids = _get_migration_ids()

    if migration_name not in migration_ids:
        print(f'Unrecognized migration name - must be one of {migration_ids}')

    _continue = input('About to undo the migrations - press y to continue.')
    if _continue == 'y':
        print('Undoing migrations')
        print(migration_name)

        # TODO ... also need to check if the ones on disk have been run or not
        # A better approach might be to get the list of ids from the db first
        # ...
        _sorted = sorted(list(MIGRATION_MODULES.keys()))
        _sorted = _sorted[_sorted.index(migration_name):]
        _sorted.reverse()

        for s in _sorted:
            MIGRATION_MODULES[s].backwards()  # noqa
    else:
        print('Not proceeding.')


###############################################################################

@click.group()
def cli():
    pass


cli.add_command(new)
cli.add_command(run)
cli.add_command(undo)


###############################################################################


if __name__ == '__main__':
    cli()
