#~ subdir('conf')
#~ subdir('icons')

install_subdir('conf', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))
install_subdir('icons', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))
install_subdir('plugins', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))

# plugins-requirements.json, the aggregate index written by
# scripts/devel/collect_plugin_requirements.py, is deliberately not installed.
# Nothing reads it: the app collects requirements from each plugin's own
# requirements.txt (services/extlibs.py through venv.requirements_for). It is
# also gitignored, so the rpm, which builds from 'git archive HEAD', could
# never ship it while the deb, which installs from the working tree, always
# did. Installing it made the two packages disagree over a file no one used.
