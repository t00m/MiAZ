project('MiAZ',
         version : '0.3.0',
    meson_version: '>= 1.5.1',
  default_options: [ 'warning_level=2',
                   ],
)

python = import('python')
i18n = import('i18n')
gnome = import('gnome')


profile = get_option('profile')
if profile == 'development'
  app_id = 'io.github.t00m.MiAZ.Devel'
  prefix = '/io/github/t00m/MiAZ/Devel'
elif profile == 'release'
  app_id = 'io.github.t00m.MiAZ'
  prefix = '/io/github/t00m/MiAZ'
endif

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'MiAZ')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('PYTHON_VERSION', python.find_installation('python3').language_version())
conf.set('APP_ID', app_id)
conf.set('APP_DSC', 'MiAZ, a Personal Document Organizer')
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
#~ conf.set('REVISION', revision)
conf.set('PROFILE', profile)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

subdir('data')
subdir('MiAZ')
subdir('po')

# `meson test` runs the unit suite, alongside the three file validations in
# data/meson.build. It stays fast: a few seconds, no display, nothing to set up.
#
# The UI tests are deliberately not registered here. They need a display and a
# throwaway HOME, take twenty minutes, and skip themselves unless MIAZ_UI_SANDBOX
# is set, so a `meson test` that ran them would either hang a plain build or
# report twenty minutes of skips. Run them with scripts/checks/run_ui_tests.sh.
pytest = find_program('pytest', 'pytest-3', required: false)
if pytest.found()
  test('unit', pytest,
       args: ['-q', meson.project_source_root() / 'tests'],
       workdir: meson.project_source_root(),
       timeout: 300,
       suite: 'unit')
else
  message('pytest not found: `meson test` will run the file validations only')
endif


gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
  glib_compile_schemas: true,
)
meson.add_install_script('build-aux/meson/postinstall.py')

