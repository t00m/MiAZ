subdir('resources')

desktop_file = i18n.merge_file(
  input: 'com.github.t00m.MiAZ.desktop.in',
  output: 'com.github.t00m.MiAZ.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# desktop_utils = find_program('desktop-file-validate', required: false)
# if desktop_utils.found()
#   test('Validate MiAZ Desktop file', desktop_utils,
#     args: [desktop_file]
#   )
# endif

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate MiAZ desktop file', desktop_utils, args: [desktop_file.full_path()])
endif

appstream_file = i18n.merge_file(
  input: 'com.github.t00m.MiAZ.metainfo.xml.in',
  output: 'com.github.t00m.MiAZ.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate appstream file', appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file],
    workdir: meson.current_build_dir()
  )
endif

install_data('com.github.t00m.MiAZ.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

install_data(
  'com.github.t00m.MiAZ.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data(
    join_paths('resources/icons/scalable', 'com.github.t00m.MiAZ.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/scalable/apps')
)
