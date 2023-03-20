pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'miaz')
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('APP_ID', APP_ID)
conf.set('APP_VERSION', APP_VERSION)
conf.set('APP_ICON', APP_ICON)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

subdir('backend')
subdir('frontend')

configure_file(
  input: 'miaz.in',
  output: 'miaz',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: ['r-xr-xr-x']
)

miaz_sources = [
  '__init__.py',
  'main.py',
]

install_data(miaz_sources, install_dir: moduledir)
