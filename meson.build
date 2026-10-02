project('MiAZ',
         version : '0.5.0',
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

# The user help, built from help/ by KB4IT into the build directory and
# installed beside the data as <datadir>/MiAZ/help. The 'help' option decides:
#   auto      build it when kb4it is found; if the build fails (a KB4IT
#             without the apphelp DocType rules refuses the pages), warn and
#             install help/target when it was built by hand, else nothing
#   enabled   kb4it is required and a failed build fails the build
#   disabled  install no help
# With no help installed, the help window opens the published site.
fs = import('fs')
help_option = get_option('help')
help_install_dir = join_paths(get_option('datadir'), meson.project_name())
kb4it = find_program('kb4it', required: help_option)
if kb4it.found()
  custom_target('help',
    output: 'help',
    command: [python.find_installation('python3'),
              files('build-aux/meson/build_help.py'),
              '--kb4it', kb4it,
              '--help-dir', meson.project_source_root() / 'help',
              '--output', '@OUTPUT@',
              '--work', meson.current_build_dir() / 'help-work',
              '--mode', help_option.enabled() ? 'enabled' : 'auto'],
    # Every page is an input and meson has no glob; KB4IT takes under a
    # second for the whole site, so it simply runs on every build.
    build_by_default: true,
    build_always_stale: true,
    install: true,
    install_dir: help_install_dir)
elif help_option.disabled()
  message('help: disabled, the help window will use the published site')
elif fs.is_dir('help/target')
  message('help: kb4it not found, installing help/target as built by hand')
  install_subdir('help/target',
                 install_dir: help_install_dir / 'help',
                 strip_directory: true)
else
  message('help: kb4it not found, the help window will use the published site')
endif

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


# gtk_update_icon_cache is deliberately left out here: meson's version treats a
# nonzero exit as fatal and aborts the whole install, but a stale/corrupt
# ~/.local/share/icons/hicolor cache (common on a long-unused profile) makes
# gtk4-update-icon-cache fail even though every other install step succeeded.
# postinstall.py below refreshes the icon cache too, using subprocess.call, so
# a bad cache there is just a warning instead of a failed install.
gnome.post_install(
  update_desktop_database: true,
  glib_compile_schemas: true,
)
meson.add_install_script('build-aux/meson/postinstall.py')

