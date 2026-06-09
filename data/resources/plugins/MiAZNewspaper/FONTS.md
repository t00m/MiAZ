# Bundled fonts

The MiAZNewspaper plugin ships four font families under `static/fonts/`. All of
them are licensed under the **SIL Open Font License, Version 1.1 (OFL-1.1)**.
The full license text and the copyright notices are in
[`static/fonts/OFL.txt`](static/fonts/OFL.txt).

The license info travels inside each `.woff2` file too, in the name table
(copyright = nameID 0, license URL = nameID 14). The table below was read from
those files.

| Family | Files | Copyright | Reserved Font Name | License URL |
|---|---|---|---|---|
| UnifrakturCook | `UnifrakturCook-Bold.woff2` | (c) 2010 j. 'mach' wust; (c) 2009 Peter Wiegel | UnifrakturCook | http://scripts.sil.org/OFL |
| Libre Caslon Display | `LibreCaslonDisplay-Regular.woff2` | (c) 2012 The Libre Caslon Display Authors | Libre Caslon Display | http://scripts.sil.org/OFL |
| Libre Caslon Text | `LibreCaslonText-Regular.woff2`, `LibreCaslonText-Bold.woff2`, `LibreCaslonText-Italic.woff2` | (c) 2012 The Libre Caslon Text Project Authors | Libre Caslon Text | http://scripts.sil.org/OFL |
| PT Serif | `PTSerif-Regular.woff2`, `PTSerif-Bold.woff2`, `PTSerif-Italic.woff2` | (c) 2010 ParaType Ltd. | PT Serif | http://scripts.sil.org/OFL_web |

## What the license requires

OFL-1.1 lets you bundle, embed and redistribute these fonts, including with the
plugin and the newspaper pages it generates. Two conditions matter here:

- Keep `OFL.txt` and the copyright notices with the fonts when redistributing.
- Do not reuse a Reserved Font Name above for a modified version of its font.
  The names apply to the primary font name shown to users, not to the file name.

## Where the fonts come from

- UnifrakturCook: https://github.com/EbenSorkin/Unifraktur (j. 'mach' wust)
- Libre Caslon Display: https://github.com/impallari/Libre-Caslon-Display
- Libre Caslon Text: https://github.com/impallari/Libre-Caslon-Text
- PT Serif: ParaType, distributed through Google Fonts

These notices reflect what the bundled files declare about themselves. To
confirm the binaries are the unmodified upstream releases, compare them against
the sources above.
