
"""
# File: repository.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Repository documents module
"""

import os
import json

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem
from MiAZ.backend.util import atomic_json_save
from MiAZ.backend.config import MiAZConfigStore

# The repository layout this version writes and understands. Bump it when the
# layout changes in a way an older MiAZ would read wrongly, and validate()
# will refuse anything newer rather than open it and assume.
REPO_FORMAT = 1


class MiAZRepository(GObject.GObject):
    __gtype_name__ = 'MiAZRepository'
    __gsignals__ = {
        'repository-switched': (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Repository')
        self.config = self.app.get_config_dict()
        self._errmsg = None
        self._conf_cache = None
        self._active_id = None
        # Whether use() pointed this instance somewhere. Distinct from
        # _active_id being None, which is also what a bare path leaves behind.
        self._active_pinned = False
        self._store = None
        self.log.info("Repository class initialized")

    @property
    def docs(self):
        """Repository documents directory"""
        return self.get('dir_docs')

    @property
    def conf(self):
        """Repository configuration directory"""
        return self.get('dir_conf')

    def validate(self, path: str) -> bool:
        if not path:
            return False
        valid = False
        try:
            conf_dir = os.path.join(path, '.conf')
            conf_file = os.path.join(conf_dir, 'repo.json')
            self.log.debug(f"Validating repository '{conf_file}'")
            if os.path.exists(conf_dir):
                if os.path.exists(conf_file):
                    with open(conf_file, 'r', encoding='utf-8') as fin:
                        try:
                            valid = self._format_is_known(json.load(fin))
                        except Exception as error:
                            self.log.error(error)
            self.log.debug(f"Repository {conf_file} valid? {valid}")
        except Exception as error:
            self.log.error(error)
        return valid

    def _format_is_known(self, repoconf) -> bool:
        """Whether this MiAZ can be trusted with that repository layout.

        A repository written before this check has no FORMAT key. Those are
        the current layout, so a missing key reads as REPO_FORMAT rather than
        as a reason to refuse a repository that worked yesterday. Only a
        format from a later version is refused, and only forwards: guarding
        backwards would break every repository that exists.
        """
        fmt = repoconf.get('FORMAT', REPO_FORMAT)
        if isinstance(fmt, bool) or not isinstance(fmt, int):
            self.log.error(f"Repository format {fmt!r} is not a version number")
            return False
        if fmt > REPO_FORMAT:
            self.log.error(
                f"Repository format {fmt} is newer than this MiAZ understands "
                f"(format {REPO_FORMAT}). Upgrade MiAZ to open it.")
            return False
        return True

    def reset(self):
        """Invalidate the conf cache so the next access triggers a fresh setup()."""
        self._conf_cache = None
        self._active_id = None
        self._active_pinned = False

    def get_active_id(self):
        """The id of the repository being shown, or None if there is none.

        Not always the default one: a switch that does not set the default
        points this instance elsewhere while 'current' still names what MiAZ
        opens on the next start. Anything naming the repository to the user
        (window title, sidebar, settings) asks here rather than reading
        'current', which would name the one that is not on screen.
        """
        if self._active_pinned:
            return self._active_id
        return self.config['App'].get('current')

    def use(self, repo_id: str = None, path: str = None) -> bool:
        """Point this instance at a repository without changing the default.

        setup() already resolves a repository id to its directories, but get()
        always calls it with no argument, so every lookup falls back to the
        'current' repository. Callers that want another one (the command line,
        given --repo) come through here instead of writing 'current', which
        would change the repository the desktop app opens next time.

        Returns whether the repository resolved. The caller validates it.
        """
        if path:
            conf = {'dir_docs': path, 'dir_conf': os.path.join(path, '.conf')}
            repo_id = None  # a bare path carries no registered name
        else:
            if not repo_id:
                return False
            # Resolve before calling setup(): for an unknown id it returns an
            # empty path, and setup() would then take '' for a new repository
            # and init() it, creating a .conf directory wherever the process
            # happens to be running.
            if not self.config['Repository'].get_path(repo_id, used=True):
                return False
            conf = self.setup(repo_id)
        if not conf.get('dir_docs'):
            return False
        self._conf_cache = conf
        self._active_id = repo_id
        self._active_pinned = True
        return True

    def init(self, path):
        repoconf = {}
        repoconf['FORMAT'] = REPO_FORMAT
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok=True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        atomic_json_save(conf_file, repoconf)
        self.config['App'].set('source', path)
        self.log.debug(f"Repository initialized: '{conf_file}'")
        self._init_default_plugins(dir_conf)
        self._init_default_values(dir_conf)

    def _init_default_plugins(self, dir_conf):
        """Write the default system-plugin enabled list for a brand-new repository."""
        default_plugins = {
            "MiAZProjectMgt": "Project management",
        }
        enabled_file = os.path.join(dir_conf, 'plugins-used.json')
        if not os.path.exists(enabled_file):
            atomic_json_save(enabled_file, default_plugins)
            self.log.debug(f"Default system plugins written to: '{enabled_file}'")

    # Filename fields whose used list starts full, mapped to the shipped file
    # the values come from. Countries are deliberately absent: that list is the
    # whole ISO set, so it is the one the setup assistant still asks about.
    DEFAULT_VALUES = (
        ('groups-used.json', 'MiAZ-groups.json'),
        ('purposes-used.json', 'MiAZ-purposes.json'),
        ('senders-used.json', 'MiAZ-people.json'),
        ('recipients-used.json', 'MiAZ-people.json'),
    )

    def _init_default_values(self, dir_conf):
        """Enable every shipped group, purpose, sender and recipient.

        These lists are short and curated, and with them all disabled a new
        repository cannot file a single document until the user has walked four
        selectors choosing from vocabulary they have not used yet. The same
        files become the available pool (MiAZConfig.setup copies them), so used
        never holds a value that is not available. Only written when the file is
        absent, so an existing repository is never touched.
        """
        conf_dir = self.app.get_env()['GPATH']['CONF']
        for used_name, default_name in self.DEFAULT_VALUES:
            used_file = os.path.join(dir_conf, used_name)
            if os.path.exists(used_file):
                continue
            default_file = os.path.join(conf_dir, default_name)
            try:
                with open(default_file, encoding='utf-8') as fh:
                    items = json.load(fh)
            except (OSError, ValueError) as error:
                self.log.error(f"Cannot read defaults from '{default_file}': {error}")
                continue
            atomic_json_save(used_file, items)
            self.log.debug(f"{len(items)} default values written to '{used_file}'")

    def setup(self, repo_id: str = None):
        conf = {}
        # ~ self.log.debug(f"Repo Id: {repo_id}")
        if repo_id is None:
            # Try to load the default repository
            # ~ self.log.debug("Loading current repository from config")
            repo_id = self.config['App'].get('current')
            # ~ self.log.debug(f"Config has repo: {repo_id}")
            if repo_id is None:
                self.log.warning("No repository configuration available")
        if repo_id is not None:
            repos_used = self.config['Repository'].load_used()
            # ~ self.log.debug(f"Number of repositories in use: {len(repos_used)}")
            if len(repos_used) > 0:
                try:
                    repo_path = self.config['Repository'].get_path(repo_id, used=True)
                    conf['dir_docs'] = repo_path
                    conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
                    if not os.path.isdir(repo_path):
                        # The directory is gone: renamed, deleted, or on a
                        # drive that is not mounted. init() would recreate it
                        # empty (os.makedirs makes the whole path) and MiAZ
                        # would open an empty repository with empty
                        # configuration where the documents used to be. A
                        # repository is only ever created on purpose, and the
                        # flows that do it check the folder exists first.
                        self.set_error(f"Repository '{repo_id}' directory not found: {repo_path}")
                        self.log.error(self.get_error())
                    elif not os.path.exists(conf['dir_conf']):
                        self.init(conf['dir_docs'])
                except Exception as error:
                    self.set_error(error)
        return conf

    def load(self, path=None):
        # The cache is not cleared here. Invalidating is the caller's job
        # (reset(), which every caller already calls before validating), and
        # clearing it at this point threw away a repository chosen with use():
        # the next get() resolved 'current' again and loaded the wrong one.
        repo_dir_conf = self.get('dir_conf')
        # One store per repository. Disposing the previous one drops its cached
        # copies, so the repository being loaded is read from disk rather than
        # from whatever the last one left behind.
        if self._store is not None:
            self._store.dispose()
        self._store = MiAZConfigStore(self.app, repo_dir_conf)
        self.config.update(self._store.as_dict())
        self._reconcile_people_available()
        self.log.debug(f"Repository configuration loaded correctly from: {repo_dir_conf}")
        self.emit('repository-switched')

    def get_config_store(self):
        """The MiAZConfigStore of the active repository, or None."""
        return self._store

    def _reconcile_people_available(self):
        """Ensure every used sender and recipient is in the shared people pool.

        Senders and recipients take their available items from the same
        people-available.json. A used person missing from that pool would not
        appear as available on the other side. Add any such people here, so the
        available list stays consistent (and heals entries left orphaned by the
        earlier per-instance cache bug).
        """
        people = self.config['Person']
        available = people.load_available()
        missing = {}
        for config_name in ('SentBy', 'SentTo'):
            for key, value in self.config[config_name].load_used().items():
                if key not in available and key not in missing:
                    missing[key] = value
        if missing:
            people.add_available_batch(list(missing.items()))
            self.log.info(f"Reconciled {len(missing)} used people into the available pool")

    def get(self, key: str) -> str:
        try:
            if self._conf_cache is None:
                self._conf_cache = self.setup()
            return self._conf_cache[key]
        except KeyError:
            self.log.warning(f"Repository Configuration Key '{key}' not found")
            return None

    def get_error(self):
        return self._errmsg

    def set_error(self, msg):
        """Last repository error"""
        self._errmsg = msg

    def simulate_rename(self, source_path: str, new_fields: list) -> MiAZItem:
        """Return a MiAZItem representing the document after renaming, without moving it."""
        util = self.app.get_service('util')
        name, ext = util.filename_details(source_path)
        new_name = "-".join(new_fields)
        new_filename = f"{new_name}.{ext}"

        item = MiAZItem(
            id=new_filename,
            date=new_fields[0],
            country=new_fields[1],
            group=new_fields[2],
            sentby_id=new_fields[3],
            purpose=new_fields[4],
            title=new_fields[5],
            sentto_id=new_fields[6],
            extension=ext
        )
        item.valid = util.filename_validate(new_filename)
        return item

    def simulate_import(self, source_path: str) -> MiAZItem:
        """Return a MiAZItem representing how a file would look if imported now."""
        util = self.app.get_service('util')
        target_filename = util.filename_normalize(source_path)
        fields = util.get_fields(target_filename)
        return self.simulate_rename(target_filename, fields)
