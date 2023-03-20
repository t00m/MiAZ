pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'miaz')
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)


miaz_sources = [
  '__init__.py',
  'models.py',
  'env.py',
  'projects.py',
  'util.py',
  'pluginsystem.py',
  'config.py',
  'watcher.py',
  'log.py',
]

install_data(miaz_sources, install_dir: moduledir)
