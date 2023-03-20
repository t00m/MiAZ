pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'miaz')
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

subdir('widgets')

miaz_sources = [
  '__init__.py',
  'help.py',
  'settings.py',
  'actions.py',
  'factory.py',
  'app.py',
  'icons.py',
]

install_data(miaz_sources, install_dir: moduledir)
