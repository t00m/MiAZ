pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'miaz')
gnome = import('gnome')

gnome.compile_resources('miaz',
  'miaz.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

# conf = configuration_data()
# conf.set('PYTHON', python.find_installation('python3').path())
# conf.set('VERSION', meson.project_version())
# conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
# conf.set('pkgdatadir', pkgdatadir)
configure_file(
  input: 'constants.py.in',
  output: 'constants.py',
  configuration: configuration_data({
    'APP_ID': APPLICATION_ID,
    'RELEASE_VER': meson.project_version(),
    'VERSION': meson.project_version() ,
    'BUILD_TYPE': get_option('buildtype'),
    'PKGDATA_DIR': PKGDATA_DIR,
    'LOCALE_DIR': conf.get('LOCALE_DIR'),
    'APP_ROOT':  APPLICATION_ROOT,
  }),
  install: true,
  install_dir: PY_INSTALLDIR.get_install_dir() / meson.project_name(),
)

configure_file(
  input: 'miaz.in',
  output: 'miaz',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr--r--'
)

launcher = join_paths(meson.project_build_root(), 'MiAZ', meson.project_name())

run_target('run',
  command: [launcher]
)

miaz_sources = [
  '__init__.py',
  'main.py',
]

install_data(miaz_sources, install_dir: moduledir)
