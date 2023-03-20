pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
frontenddir = join_paths(pkgdatadir, 'MiAZ/frontend')
gnome = import('gnome')
python = import('python')

subdir('console')
subdir('desktop')



conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)


miaz_sources = [
  '__init__.py',
]

install_data(miaz_sources, install_dir: frontenddir)
