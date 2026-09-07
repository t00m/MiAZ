#!/usr/bin/python3

"""Which command installs git, per distribution.

The plugin cannot work without git, and telling a user to "install git" without
saying how is half an answer. The package name is the same everywhere; only the
package manager changes, so one table keyed on os-release settles it.
"""

import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZHistory')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def write_os_release(tmp_path, body):
    path = tmp_path / 'os-release'
    path.write_text(body, encoding='utf-8')
    return str(path)


def test_a_distribution_that_names_itself_gets_its_own_command(tmp_path):
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID=fedora\nVERSION_ID="44"\n')
    assert install_command(path) == 'sudo dnf install git'


def test_quotes_around_the_id_are_not_part_of_it(tmp_path):
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID="ubuntu"\n')
    assert install_command(path) == 'sudo apt install git'


def test_a_derivative_falls_back_to_the_family_it_names(tmp_path):
    """elementary is not in the table, but the distribution says what it is."""
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID=elementary\nID_LIKE="ubuntu debian"\n')
    assert install_command(path) == 'sudo apt install git'


def test_the_id_wins_over_the_family(tmp_path):
    """Linux Mint says ID_LIKE=ubuntu, and both answers agree here, so the
    test uses a pair that does not: a hypothetical arch derivative that ships
    dnf would still be answered with its own command."""
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID=fedora\nID_LIKE=debian\n')
    assert install_command(path) == 'sudo dnf install git'


def test_the_opensuse_family_is_matched_by_prefix(tmp_path):
    """openSUSE never calls itself just opensuse."""
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID="opensuse-tumbleweed"\n')
    assert install_command(path) == 'sudo zypper install git'


def test_an_unknown_distribution_gets_no_command(tmp_path):
    from history.distro import install_command
    path = write_os_release(tmp_path, 'ID=plan9\n')
    assert install_command(path) is None


def test_a_missing_file_gets_no_command(tmp_path):
    from history.distro import install_command
    assert install_command(str(tmp_path / 'absent')) is None


def test_every_supported_distribution_is_reachable(tmp_path):
    """A table nothing exercises is a table that rots."""
    from history.distro import INSTALL_COMMANDS, install_command
    for name, command in INSTALL_COMMANDS:
        path = write_os_release(tmp_path, f'ID={name}\n')
        assert install_command(path) == command
