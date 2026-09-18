#!/usr/bin/python3

"""The registry is installed early enough to be useful.

MiAZActions and MiAZImportDoc both ask the factory for a menu item with an
accelerator while the application is still building its services. If the
registry is installed after the factory, those accelerators are set without
ever being claimed, and the registry is a liar from the first frame.
"""

from MiAZ.frontend.desktop import app as appmod


def source_order(name):
    """Where a service name is first registered in app.py, by line number."""
    path = appmod.__file__
    with open(path, encoding='utf-8') as source:
        for number, line in enumerate(source, start=1):
            if f"set_service('{name}'" in line:
                return number
    raise AssertionError(f"app.py never registers a '{name}' service")


def source_line(name):
    """The source line where a service name is first registered."""
    path = appmod.__file__
    with open(path, encoding='utf-8') as source:
        for _number, line in enumerate(source, start=1):
            if f"set_service('{name}'" in line:
                return line.strip()
    raise AssertionError(f"app.py never registers a '{name}' service")


def test_the_registry_is_installed_before_the_factory():
    assert source_order('shortcuts') < source_order('factory')


def test_the_registry_is_installed_before_the_services_that_claim_keys():
    for name in ('actions', 'importdoc'):
        assert source_order('shortcuts') < source_order(name), (
            f"'{name}' claims an accelerator, so it must be built after "
            "the registry")


def test_the_registry_installation_calls_register_core():
    """The core accelerator table must be loaded at startup, before any plugin
    can load, so a plugin can never take a key out from under the application."""
    line = source_line('shortcuts')
    assert '.register_core()' in line, (
        "shortcuts service registration must chain .register_core() to load "
        "the core accelerator table at startup")
