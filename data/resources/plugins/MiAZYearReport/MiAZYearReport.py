#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: MiAZYearReport.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Printable yearly summary of the active repository, rendered as a
#              self-contained, print-friendly HTML page and published to the WWW
#              root so it shows up in the integrated MiAZ Browser dropdown.
#
# What the report shows (per year):
#   - Counts by sender (SentBy)
#   - Top concepts
#   - Biggest purpose ("biggest expense purpose"); document count is the proxy,
#     since the seven-field filename scheme carries no monetary amount
#   - Document velocity (per-month distribution, average, busiest month, and the
#     year-over-year change in total)
#
# Output (one file per year, plus index.html = most recent year):
#   $HOME/.MiAZ/var/www/html/MiAZYearReport/{index,YYYY}.html
#
# Triggers (debounced rebuild):
#   workspace-loaded             initial build + menu install
#   util.filename-added          rebuild
#   util.filename-deleted        rebuild
#   util.filename-renamed        rebuild
"""

import os
import html
import shutil
import threading
from collections import Counter
from datetime import datetime
from gettext import gettext as _

from gi.repository import GLib

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin


plugin_info = {
    'Module':       'MiAZYearReport',
    'Name':         'MiAZYearReport',
    'Loader':       'Python3',
    'Description':  _('Printable yearly summary report'),
    'Authors':      'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':    'Copyright © 2026 Tomás Vírseda',
    'Website':      'https://github.com/t00m/MiAZ',
    'Help':         'https://github.com/t00m/MiAZ/README.adoc',
    'Version':      '0.1.0',
    'Category':     'Analytics and Reporting',
    'Subcategory':  'Custom Reports',
}

PLUGIN_DIR_NAME = 'MiAZYearReport'
REBUILD_DEBOUNCE_MS = 1500
TOP_N = 12

# Seven-field filename scheme: date-country-group-sentby-purpose-concept-sentto
FIELD_DATE = 0
FIELD_SENTBY = 3
FIELD_PURPOSE = 4
FIELD_CONCEPT = 5
FIELD_SENTTO = 6

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

CSS = """
:root{--fg:#1c1c1c;--muted:#6b6b6b;--line:#e4e4e7;--accent:#2563eb;
--bar:#e6effd;--barfill:#3b82f6;--card:#f7f8fa;--lead:#eff6ff;}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{font-family:-apple-system,"Cantarell","Segoe UI",Roboto,sans-serif;
color:var(--fg);background:#fff;line-height:1.45;}
.wrap{max-width:920px;margin:0 auto;padding:24px;}
.toolbar{display:flex;justify-content:flex-end;margin-bottom:10px;}
button.print{background:var(--accent);color:#fff;border:none;border-radius:8px;
padding:8px 16px;font-size:14px;cursor:pointer;}
button.print:hover{filter:brightness(1.05);}
header.report{display:flex;justify-content:space-between;align-items:flex-end;
border-bottom:3px solid var(--accent);padding-bottom:12px;}
header.report h1{font-size:28px;margin:0;}
header.report .sub{color:var(--muted);font-size:13px;text-align:right;}
.yearnav{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 22px;}
.yearnav a{padding:4px 12px;border:1px solid var(--line);border-radius:14px;
text-decoration:none;color:var(--fg);font-size:13px;}
.yearnav a.active{background:var(--accent);color:#fff;border-color:var(--accent);}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:26px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;}
.card .label{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);}
.card .value{font-size:24px;font-weight:700;margin-top:4px;word-break:break-word;}
.card .hint{font-size:12px;color:var(--muted);margin-top:3px;}
section{margin-bottom:28px;page-break-inside:avoid;}
section h2{font-size:18px;border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:12px;}
section .lead-note{color:var(--muted);font-size:12px;margin:-6px 0 12px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:middle;}
th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em;}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
.barcell{width:42%;}
.bar{position:relative;background:var(--bar);border-radius:4px;height:16px;min-width:2px;}
.bar>span{position:absolute;left:0;top:0;bottom:0;background:var(--barfill);border-radius:4px;}
tr.lead td{background:var(--lead);font-weight:600;}
.velocity{display:grid;grid-template-columns:42px 1fr 44px;gap:7px 10px;align-items:center;}
.velocity .m{color:var(--muted);font-size:12px;}
.velocity .c{text-align:right;font-variant-numeric:tabular-nums;font-size:12px;}
.headline{color:var(--muted);font-size:13px;margin:0 0 14px;}
footer.report{margin-top:30px;border-top:1px solid var(--line);padding-top:10px;
color:var(--muted);font-size:12px;display:flex;justify-content:space-between;}
.empty{padding:70px 20px;text-align:center;color:var(--muted);}
@media print{
  .no-print{display:none !important;}
  .wrap{max-width:none;padding:0;}
  body{font-size:12px;}
  section,.card,tr{page-break-inside:avoid;}
  *{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }
}
@page{size:A4;margin:14mm;}
"""


class MiAZYearReportPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZYearReportPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.util = self.app.get_service('util')
        self.repo = self.app.get_service('repo')
        self.factory = self.app.get_service('factory')

        self._rebuild_timeout_id = 0
        self._signal_handlers = []
        self.workspace = self.app.get_widget('workspace')

        self._connect_signals()

        if self.workspace is not None and self.workspace.is_loaded():
            self._on_workspace_loaded()
        elif self.workspace is not None:
            handler = self.workspace.connect('workspace-loaded', lambda *_a: self._on_workspace_loaded())
            self._signal_handlers.append((self.workspace, handler))

    def do_deactivate(self):
        if self._rebuild_timeout_id:
            GLib.source_remove(self._rebuild_timeout_id)
            self._rebuild_timeout_id = 0
        for obj, handler in self._signal_handlers:
            try:
                obj.disconnect(handler)
            except Exception:
                pass
        self._signal_handlers = []
        # The published site under LPATH/WWW is removed centrally by the plugin
        # manager (unload_plugin -> _remove_plugin_www) when the plugin is
        # disabled or uninstalled, so no per-plugin cleanup is needed here.
        self.plugin.set_started(False)

    # Setup

    def _connect_signals(self):
        for sig in ('filename-added', 'filename-deleted', 'filename-renamed'):
            handler = self.util.connect(sig, self._on_repo_changed)
            self._signal_handlers.append((self.util, handler))

    def _on_workspace_loaded(self):
        if not self.plugin.started():
            menuitem = self.factory.create_menuitem(
                name=self.plugin.get_menu_item_name(),
                label=_('Open year report'),
                callback=self._on_menu_clicked,
            )
            self.plugin.install_menu_entry(menuitem)
            self.plugin.set_started(True)
        self._schedule_rebuild()

    def _on_menu_clicked(self, *_args):
        # The report lives in the Browser tab; bring that tab forward.
        if self.workspace is not None:
            try:
                self.workspace.show_stack_page('workspace-browser')
            except Exception as error:
                self.log.debug(f"MiAZYearReport: could not show Browser page: {error}")

    def _on_repo_changed(self, *_args):
        self._schedule_rebuild()

    # Paths

    def _target_dir(self):
        env = self.app.get_env()
        if env is None:
            return None
        return os.path.join(env['LPATH']['WWW'], PLUGIN_DIR_NAME)

    # Build (debounced, off the GTK main loop)

    def _schedule_rebuild(self):
        if self._rebuild_timeout_id:
            GLib.source_remove(self._rebuild_timeout_id)
        self._rebuild_timeout_id = GLib.timeout_add(REBUILD_DEBOUNCE_MS, self._kick_rebuild)

    def _kick_rebuild(self):
        self._rebuild_timeout_id = 0
        threading.Thread(target=self._rebuild_worker, name='MiAZYearReport-build', daemon=True).start()
        return False

    def _rebuild_worker(self):
        try:
            years = self._collect()
            pages = self._render_all(years)
            self._write_pages(pages)
        except Exception as error:
            self.log.error(f"MiAZYearReport build failed: {error}")

    def _write_pages(self, pages):
        target = self._target_dir()
        if not target:
            return
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        for name, content in pages.items():
            with open(os.path.join(target, name), 'w', encoding='utf-8') as fh:
                fh.write(content)
        self.log.debug(f"MiAZYearReport: wrote {len(pages)} page(s) to {target}")

    # Data collection

    def _used_map(self, config_name):
        config = self.app.get_config(config_name)
        if config is None:
            return {}
        try:
            return config.load_used()
        except Exception:
            return {}

    def _collect(self):
        """Return {year: stats} aggregated from the repository filenames."""
        years = {}
        docs_dir = self.repo.docs
        if not docs_dir or not os.path.isdir(docs_dir):
            return years

        for filepath in self.util.get_files(docs_dir):
            filename = os.path.basename(filepath)
            if filename.startswith('.'):
                continue
            stem = filename.rsplit('.', 1)[0]
            if not self.util.filename_is_normalized(stem):
                continue
            fields = self.util.get_fields(filename)
            if len(fields) < 7:
                continue
            date = fields[FIELD_DATE]
            if len(date) != 8 or not date.isdigit():
                continue

            year = date[:4]
            stats = years.get(year)
            if stats is None:
                stats = {
                    'total': 0,
                    'sender': Counter(),
                    'concept': Counter(),
                    'purpose': Counter(),
                    'months': [0] * 12,
                }
                years[year] = stats

            stats['total'] += 1
            if fields[FIELD_SENTBY]:
                stats['sender'][fields[FIELD_SENTBY]] += 1
            if fields[FIELD_CONCEPT]:
                stats['concept'][fields[FIELD_CONCEPT]] += 1
            if fields[FIELD_PURPOSE]:
                stats['purpose'][fields[FIELD_PURPOSE]] += 1
            try:
                month_index = int(date[4:6]) - 1
            except ValueError:
                month_index = -1
            if 0 <= month_index < 12:
                stats['months'][month_index] += 1

        return years

    # Rendering

    def _render_all(self, years):
        env = self.app.get_env()
        app_name = env['APP']['name'] if env else 'MiAZ'
        version = env['APP'].get('VERSION', '') if env else ''
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current') if appconf is not None else None
        repo_name = repo_id.replace('_', ' ') if repo_id else app_name
        generated = datetime.now().strftime('%Y-%m-%d %H:%M')

        meta = {
            'app_name': app_name,
            'version': version,
            'repo_name': repo_name,
            'generated': generated,
            'sender_map': self._used_map('SentBy'),
            'purpose_map': self._used_map('Purpose'),
        }

        pages = {}
        if not years:
            pages['index.html'] = self._render_empty(meta)
            return pages

        year_list = sorted(years.keys(), reverse=True)
        for year in year_list:
            pages[f"{year}.html"] = self._render_page(year, years, year_list, meta)
        # The dropdown opens index.html; point it at the most recent year.
        pages['index.html'] = pages[f"{year_list[0]}.html"]
        return pages

    def _doc(self, title, body):
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{html.escape(title)}</title>\n"
            f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
            f"{body}\n</div>\n</body>\n</html>\n"
        )

    def _render_empty(self, meta):
        body = (
            f"<header class=\"report\"><div><h1>{_('Year report')}</h1></div>"
            f"<div class=\"sub\">{html.escape(meta['repo_name'])}</div></header>"
            f"<div class=\"empty\">{_('No normalized documents to report yet.')}</div>"
            f"<footer class=\"report\"><span>{html.escape(meta['app_name'])} {html.escape(meta['version'])}</span>"
            f"<span>{html.escape(meta['generated'])}</span></footer>"
        )
        return self._doc(_('Year report'), body)

    @staticmethod
    def _bar(pct):
        return f"<div class=\"bar\"><span style=\"width:{pct:.1f}%\"></span></div>"

    def _render_page(self, year, years, year_list, meta):
        stats = years[year]
        total = stats['total']
        sender_map = meta['sender_map']
        purpose_map = meta['purpose_map']

        # Headline numbers ---------------------------------------------------
        distinct_senders = len(stats['sender'])
        busiest_index = max(range(12), key=lambda i: stats['months'][i]) if total else 0
        busiest_count = stats['months'][busiest_index] if total else 0
        busiest = f"{MONTH_NAMES[busiest_index]} ({busiest_count})" if busiest_count else '—'

        if stats['purpose']:
            lead_pid, lead_pcount = stats['purpose'].most_common(1)[0]
            lead_purpose = purpose_map.get(lead_pid, lead_pid) or lead_pid
        else:
            lead_purpose, lead_pcount = '—', 0

        prev = years.get(str(int(year) - 1))
        if prev and prev['total']:
            diff = total - prev['total']
            pct = diff / prev['total'] * 100
            sign = '+' if diff >= 0 else '−'
            yoy = f"{sign}{abs(diff)} vs {int(year) - 1} ({pct:+.0f}%)"
        elif prev:
            yoy = f"vs {int(year) - 1}: n/a"
        else:
            yoy = _('no prior year')

        active_months = sum(1 for c in stats['months'] if c > 0)
        avg_month = total / active_months if active_months else 0

        # Year navigation ----------------------------------------------------
        nav = '<nav class="yearnav no-print">'
        for y in year_list:
            cls = 'active' if y == year else ''
            nav += f'<a class="{cls}" href="{y}.html">{y}</a>'
        nav += '</nav>'

        # Summary cards ------------------------------------------------------
        cards = (
            '<div class="cards">'
            f'<div class="card"><div class="label">{_("Documents")}</div>'
            f'<div class="value">{total}</div><div class="hint">{html.escape(yoy)}</div></div>'
            f'<div class="card"><div class="label">{_("Distinct senders")}</div>'
            f'<div class="value">{distinct_senders}</div></div>'
            f'<div class="card"><div class="label">{_("Busiest month")}</div>'
            f'<div class="value">{html.escape(busiest)}</div></div>'
            f'<div class="card"><div class="label">{_("Leading purpose")}</div>'
            f'<div class="value">{html.escape(str(lead_purpose))}</div>'
            f'<div class="hint">{lead_pcount} {_("documents")}</div></div>'
            '</div>'
        )

        sections = [
            self._section_senders(stats, sender_map),
            self._section_concepts(stats),
            self._section_purposes(stats, purpose_map),
            self._section_velocity(stats, avg_month, busiest, yoy),
        ]

        body = (
            '<div class="toolbar no-print">'
            f'<button class="print" onclick="window.print()">{_("Print / Save as PDF")}</button></div>'
            f'<header class="report"><div><h1>{_("Year report")} {year}</h1></div>'
            f'<div class="sub">{html.escape(meta["repo_name"])}</div></header>'
            f'{nav}{cards}{"".join(sections)}'
            f'<footer class="report"><span>{html.escape(meta["app_name"])} {html.escape(meta["version"])}</span>'
            f'<span>{_("Generated")} {html.escape(meta["generated"])}</span></footer>'
        )
        return self._doc(f"{_('Year report')} {year} · {meta['repo_name']}", body)

    def _section_senders(self, stats, sender_map):
        if not stats['sender']:
            return ''
        top = stats['sender'].most_common(TOP_N)
        maxc = top[0][1]
        rows = ''
        for rank, (sid, count) in enumerate(top, 1):
            name = sender_map.get(sid, sid) or sid
            rows += (
                f'<tr><td class="num">{rank}</td><td>{html.escape(str(name))}</td>'
                f'<td class="barcell">{self._bar(count / maxc * 100)}</td>'
                f'<td class="num">{count}</td></tr>'
            )
        return (
            f'<section><h2>{_("Counts by sender")}</h2>'
            f'<table><thead><tr><th class="num">#</th><th>{_("Sender")}</th>'
            f'<th></th><th class="num">{_("Documents")}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></section>'
        )

    def _section_concepts(self, stats):
        if not stats['concept']:
            return ''
        top = stats['concept'].most_common(TOP_N)
        maxc = top[0][1]
        rows = ''
        for rank, (concept, count) in enumerate(top, 1):
            rows += (
                f'<tr><td class="num">{rank}</td><td>{html.escape(concept)}</td>'
                f'<td class="barcell">{self._bar(count / maxc * 100)}</td>'
                f'<td class="num">{count}</td></tr>'
            )
        return (
            f'<section><h2>{_("Top concepts")}</h2>'
            f'<table><thead><tr><th class="num">#</th><th>{_("Concept")}</th>'
            f'<th></th><th class="num">{_("Documents")}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></section>'
        )

    def _section_purposes(self, stats, purpose_map):
        if not stats['purpose']:
            return ''
        ordered = stats['purpose'].most_common()
        maxc = ordered[0][1]
        rows = ''
        for index, (pid, count) in enumerate(ordered):
            name = purpose_map.get(pid, pid) or pid
            cls = ' class="lead"' if index == 0 else ''
            rows += (
                f'<tr{cls}><td>{html.escape(str(name))}</td>'
                f'<td class="barcell">{self._bar(count / maxc * 100)}</td>'
                f'<td class="num">{count}</td></tr>'
            )
        return (
            f'<section><h2>{_("Biggest purpose")}</h2>'
            f'<p class="lead-note">{_("Ranked by document count (the filename scheme carries no amount).")}</p>'
            f'<table><thead><tr><th>{_("Purpose")}</th>'
            f'<th></th><th class="num">{_("Documents")}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></section>'
        )

    def _section_velocity(self, stats, avg_month, busiest, yoy):
        maxc = max(stats['months']) or 1
        cells = ''
        for index, name in enumerate(MONTH_NAMES):
            count = stats['months'][index]
            cells += (
                f'<div class="m">{name}</div>{self._bar(count / maxc * 100)}'
                f'<div class="c">{count}</div>'
            )
        headline = _('Average {avg:.1f} documents per active month · busiest {busy} · {yoy}').format(
            avg=avg_month, busy=busiest, yoy=yoy)
        return (
            f'<section><h2>{_("Document velocity")}</h2>'
            f'<p class="headline">{html.escape(headline)}</p>'
            f'<div class="velocity">{cells}</div></section>'
        )
