"""Which command installs git on the distribution we are running on.

No gettext here: these are shell commands, and a translated command does not
run.
"""

OS_RELEASE = '/etc/os-release'

# An os-release ID (or an ID_LIKE token), and the command that installs git.
# The package is called git everywhere, so only the package manager changes.
INSTALL_COMMANDS = (
    ('fedora', 'sudo dnf install git'),
    ('rhel', 'sudo dnf install git'),
    ('centos', 'sudo dnf install git'),
    ('almalinux', 'sudo dnf install git'),
    ('rocky', 'sudo dnf install git'),
    ('debian', 'sudo apt install git'),
    ('ubuntu', 'sudo apt install git'),
    ('linuxmint', 'sudo apt install git'),
    ('pop', 'sudo apt install git'),
    ('arch', 'sudo pacman -S git'),
    ('manjaro', 'sudo pacman -S git'),
    ('endeavouros', 'sudo pacman -S git'),
    ('opensuse', 'sudo zypper install git'),
    ('sles', 'sudo zypper install git'),
    ('suse', 'sudo zypper install git'),
    ('alpine', 'sudo apk add git'),
    ('gentoo', 'sudo emerge dev-vcs/git'),
    ('void', 'sudo xbps-install -S git'),
)


def read_os_release(path: str = OS_RELEASE) -> dict:
    """The key and value pairs of an os-release file, empty when there is none."""
    values = {}
    try:
        with open(path, encoding='utf-8') as osrelease:
            for line in osrelease:
                key, separator, value = line.strip().partition('=')
                if separator:
                    values[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def install_command(path: str = OS_RELEASE):
    """The command that installs git here, or None for a distribution we do
    not know.

    ID is tried before ID_LIKE, so a derivative that names itself is answered
    with its own command and an unknown one falls back to the family it
    declares. The prefix match is for openSUSE, which calls itself
    opensuse-leap or opensuse-tumbleweed and never just opensuse.
    """
    values = read_os_release(path)
    candidates = [values.get('ID', '')]
    candidates.extend(values.get('ID_LIKE', '').split())
    for candidate in candidates:
        candidate = candidate.strip().lower()
        if not candidate:
            continue
        for name, command in INSTALL_COMMANDS:
            if candidate == name or candidate.startswith(f'{name}-'):
                return command
    return None
