subdir('resources')

desktop_file = i18n.merge_file(
  input: 'io.github.t00m.MiAZ.desktop.in',
  output: 'io.github.t00m.MiAZ.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate MiAZ desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

appstream_file = i18n.merge_file(
  input: 'io.github.t00m.MiAZ.metainfo.xml.in',
  output: 'io.github.t00m.MiAZ.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# Validate MetaInfo file
metainfo_file = 'io.github.t00m.miaz.metainfo.xml'
ascli_exe = find_program('appstreamcli', required: false)
if ascli_exe.found()
  test('validate metainfo file',
        ascli_exe,
        args: ['validate',
               '--no-net',
               '--pedantic',
               metainfo_file]
  )
endif

# Localize a MetaInfo file and install it
i18n = import('i18n')

# NOTE: Remember to add the XML file to POTFILES.in!
metainfo_file = 'io.github.t00m.miaz.metainfo.xml'
i18n.merge_file(
    input:  metainfo_file,
    output: 'io.github.t00m.miaz.metainfo.xml',
    type: 'xml',
    po_dir: join_paths (meson.source_root(), 'po'),
    install: true,
    install_dir: join_paths (get_option ('datadir'), 'metainfo')
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate appstream file', appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file],
    workdir: meson.current_build_dir()
  )
endif

install_data('io.github.t00m.MiAZ.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

install_data(
  'io.github.t00m.MiAZ.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data(
  'io.github.t00m.MiAZ-symbolic.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/symbolic/apps')
)

# Subpackages
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name(), 'resources')
install_subdir('docs', install_dir: pkgdatadir)
