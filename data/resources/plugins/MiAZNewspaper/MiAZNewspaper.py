#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: MiAZNewspaper.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Show the Workspace documents as a newspaper, "The MiAZ Times".
"""

# The edition is built from the documents currently visible in the Workspace.
# It is published as an HTML site under the WWW root, so the MiAZ Browser lists
# it in its dropdown. Stories link to 'miazdoc:<filename>', which the Browser
# opens with the system handler. The front page shows every visible document.
# The "Open as Newspaper" menu shows a single selected document as an article.

import os
import html
import shutil
import threading
import urllib.parse
from datetime import datetime
from gettext import gettext as _

from gi.repository import GLib

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin


plugin_info = {
    'Module':       'MiAZNewspaper',
    'Name':         'MiAZNewspaper',
    'Loader':       'Python3',
    'Description':  _('MiAZ Newspaper'),
    'Authors':      'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':    'Copyright © 2026 Tomás Vírseda',
    'Website':      'https://github.com/t00m/MiAZ',
    'Help':         'https://github.com/t00m/MiAZ/README.adoc',
    'Version':      '0.1.0',
    'Category':     'Data Management',
    'Subcategory':  'Visualization',
    'Dependencies': 'HelloWorld',
}

PLUGIN_DIR_NAME = 'MiAZNewspaper'
REBUILD_DEBOUNCE_MS = 800


def esc(value):
    # HTML-escape a field value. Concepts and names are user data.
    return html.escape(value or '')


def href(filename):
    # Link a story to its document via the Browser 'miazdoc:' scheme, URL-encoded.
    return 'miazdoc:' + urllib.parse.quote(filename or '')


def roman(number):
    # Roman numeral for the edition year. The caller handles the plain fallback.
    if not number:
        return ''
    table = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'),
             (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'),
             (5, 'V'), (4, 'IV'), (1, 'I')]
    out = ''
    for value, sign in table:
        while number >= value:
            out += sign
            number -= value
    return out


class MiAZNewspaperPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZNewspaperPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.util = self.app.get_service('util')
        self.repo = self.app.get_service('repo')
        self.factory = self.app.get_service('factory')

        self._mode = 'front'
        self._rebuild_timeout_id = 0
        self._signal_handlers = []
        self.workspace = self.app.get_widget('workspace')

        if self.workspace is not None and self.workspace.is_loaded():
            self._on_workspace_loaded()
        elif self.workspace is not None:
            handler = self.workspace.connect(
                'workspace-loaded', lambda *_a: self._on_workspace_loaded())
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

    def _plugin_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    def _static_dir(self):
        return os.path.join(self._plugin_dir(), 'static')

    def _target_dir(self):
        env = self.app.get_env()
        if env is None:
            return None
        return os.path.join(env['LPATH']['WWW'], PLUGIN_DIR_NAME)

    def _on_workspace_loaded(self):
        if not self.plugin.started():
            menuitem = self.factory.create_menuitem(
                name=self.plugin.get_menu_item_name(),
                label=_('Open as Newspaper'),
                callback=self._on_menu_clicked,
            )
            self.plugin.install_menu_entry(menuitem)
            # Reprint only when the view changes: filter, sort or content reload.
            # Selection is not a trigger; clicking a document must not reprint.
            for signal in ('workspace-view-filtered',
                           'workspace-view-updated'):
                handler = self.workspace.connect(signal, self._schedule_rebuild)
                self._signal_handlers.append((self.workspace, handler))
            self.plugin.set_started(True)

        # First print is always the front page of the current view.
        self._render(honor_selection=False)

    def _on_menu_clicked(self, *_args):
        # Reprint honouring the selection, then bring the Browser tab forward.
        self._render(honor_selection=True)
        if self.workspace is not None:
            try:
                self.workspace.show_stack_page('workspace-browser')
            except Exception as error:
                self.log.debug(f"MiAZNewspaper: could not show Browser page: {error}")

    def _schedule_rebuild(self, *_args):
        # Debounce bursts of filter and reload events into one reprint.
        if self._rebuild_timeout_id:
            GLib.source_remove(self._rebuild_timeout_id)
        self._rebuild_timeout_id = GLib.timeout_add(
            REBUILD_DEBOUNCE_MS, self._rebuild_tick)

    def _rebuild_tick(self):
        self._rebuild_timeout_id = 0
        # A view change always reprints the front page, never an article.
        self._render(honor_selection=False)
        return False

    # Data

    def _visible_items(self):
        # Documents currently shown in the Workspace, in display order.
        view = self.workspace.get_workspace_view()
        model = view.filter_model
        items = []
        for i in range(model.get_n_items()):
            item = model.get_item(i)
            if item is not None:
                items.append(item)
        return items

    @staticmethod
    def _doc(item):
        # Map a MiAZItem to a dict of resolved and raw field values.
        return {
            'filename': item.id,
            'date': item.date or '',
            'country': item.country or '',
            'country_dsc': item.country_dsc or item.country or '',
            'group': item.group or '',
            'group_dsc': item.group_dsc or item.group or '',
            'purpose': item.purpose or '',
            'purpose_dsc': item.purpose_dsc or item.purpose or '',
            'sentby': item.sentby_id or '',
            'sentby_dsc': item.sentby_dsc or item.sentby_id or '',
            'sentto': item.sentto_id or '',
            'sentto_dsc': item.sentto_dsc or item.sentto_id or '',
            'concept': item.subtitle or '',
            'extension': item.extension or '',
        }

    def _render(self, *_args, honor_selection=False):
        # Build the edition from the current view, publish it off the main loop.
        # honor_selection True (menu action) shows one selected doc as an article.
        # View-change reprints pass False, so selection never alters the edition.
        items = self._visible_items()
        selected = []
        if honor_selection:
            try:
                selected = self.workspace.get_selected_items() or []
            except Exception:
                selected = []

        if len(selected) == 1:
            self._mode = 'article'
            payload = ('article', self._doc(selected[0]))
        else:
            self._mode = 'front'
            payload = ('front', [self._doc(item) for item in items])

        threading.Thread(target=self._publish_worker, args=payload,
                         name='MiAZNewspaper-publish', daemon=True).start()

    def _publish_worker(self, mode, data):
        try:
            if mode == 'article':
                body = self._build_article(data)
            else:
                body = self._build_front_page(data)
            self._publish(body)
        except Exception as error:
            self.log.error(f"MiAZNewspaper build failed: {error}")

    def _publish(self, html_body):
        # Write index.html, CSS and fonts into the WWW page directory.
        # Rebuild the dir from scratch so the Browser monitor sees the change.
        target = self._target_dir()
        if not target:
            return
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(os.path.join(target, 'static'), exist_ok=True)
        os.makedirs(os.path.join(target, 'fonts'), exist_ok=True)

        # index.html links 'static/newspaper.css'; the CSS links '../fonts/*'.
        css_src = os.path.join(self._static_dir(), 'newspaper.css')
        if os.path.isfile(css_src):
            shutil.copy2(css_src, os.path.join(target, 'static', 'newspaper.css'))

        fonts_src = os.path.join(self._static_dir(), 'fonts')
        if os.path.isdir(fonts_src):
            for name in os.listdir(fonts_src):
                if name.endswith('.woff2'):
                    shutil.copy2(os.path.join(fonts_src, name),
                                 os.path.join(target, 'fonts', name))

        with open(os.path.join(target, 'index.html'), 'w', encoding='utf-8') as fh:
            fh.write(html_body)
        self.log.debug(f"MiAZNewspaper: published edition to {target}")

    # Dates / prose

    @staticmethod
    def _dt(yyyymmdd):
        try:
            return datetime.strptime(yyyymmdd, '%Y%m%d')
        except (ValueError, TypeError):
            return None

    def _long_date(self, yyyymmdd):
        dt = self._dt(yyyymmdd)
        return dt.strftime('%A, %d %B %Y') if dt else ''

    def _article_date(self, yyyymmdd):
        dt = self._dt(yyyymmdd)
        return dt.strftime('%d %B %Y') if dt else (yyyymmdd or '')

    def _short_date(self, yyyymmdd):
        dt = self._dt(yyyymmdd)
        return dt.strftime('%d %b') if dt else (yyyymmdd or '')

    def _verb(self, purpose_code):
        verbs = {'INV': _('issues'), 'REQ': _('requests'), 'STM': _('issues'),
                 'INF': _('posts'), 'CON': _('files'), 'TKT': _('issues')}
        return verbs.get((purpose_code or '').upper(), _('files'))

    def _deck(self, doc):
        group = esc(doc['group_dsc'])
        decks = {
            'INV': _('A new invoice has been filed to the {group} ledger and now awaits your review.'),
            'REQ': _('A request has been recorded and filed to the {group} section.'),
            'STM': _('A statement has arrived and joined the {group} record.'),
            'INF': _('An informative note has been posted to the {group} section.'),
            'CON': _('A contract has been filed to the {group} section.'),
            'TKT': _('A ticket has been issued and filed to the {group} section.'),
        }
        code = (doc['purpose'] or '').upper()
        if code in decks:
            return decks[code].format(group=group)
        return _('A {purpose} has been filed to the {group} section.').format(
            purpose=esc((doc['purpose_dsc'] or _('document')).lower()), group=group)

    def _summary(self, doc):
        sentence = _('{sender} {verb} {concept}, filed {date}.').format(
            sender=esc(doc['sentby_dsc']),
            verb=self._verb(doc['purpose']),
            concept=esc(doc['concept'].lower()),
            date=esc(self._short_date(doc['date'])))
        dateline = '<span class="dateline">%s —</span>' % esc(doc['country_dsc'])
        return f'{dateline} {sentence}'

    def _lede(self, doc):
        # Two sentences naming section, sender, recipient, date and concept.
        p1 = _('The {group} section of the archive receives {concept} from {sender}, dated {date}, addressed to {recipient}.').format(
            group=esc(doc['group_dsc']),
            concept=esc(doc['concept'].lower()) or _('a new filing'),
            sender=esc(doc['sentby_dsc']),
            date=esc(self._article_date(doc['date'])),
            recipient=esc(doc['sentto_dsc']))
        p2 = _('Classified as {a_purpose}, the document joins the permanent record, where it can be retrieved, renamed, or assigned to a project at any time.').format(
            a_purpose=esc((doc['purpose_dsc'] or _('a filing')).lower()))
        return p1, p2

    # Builders

    def _shell(self, title, inner):
        return (
            '<!DOCTYPE html><html lang="en"><head>'
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(title)}</title>'
            '<link rel="stylesheet" href="static/newspaper.css">'
            f'</head><body><div class="sheet">{inner}</div></body></html>'
        )

    def _build_front_page(self, docs):
        t = self._i18n()
        count = len(docs)
        groups = {}
        for doc in docs:
            label = doc['group_dsc'] or doc['group'] or _('Unfiled')
            groups[label] = groups.get(label, 0) + 1
        section_count = len(groups)

        dated = [d for d in docs if self._dt(d['date'])]
        edition_dt = max((self._dt(d['date']) for d in dated), default=None)
        if edition_dt is not None:
            edition_date = edition_dt.strftime('%A, %d %B %Y')
            year_num = edition_dt.year
        else:
            now = datetime.now()
            edition_date = now.strftime('%A, %d %B %Y')
            year_num = now.year
        year = roman(year_num) or str(year_num)

        masthead = (
            '<header class="masthead">'
            '<div class="masthead__top">'
            f'<span>{esc(edition_date)}</span><span>★</span>'
            f'<span>{count} {esc(t["documents"])} · {section_count} {esc(t["sections"])}</span>'
            '</div>'
            '<h1 class="masthead__title">The MiAZ Times</h1>'
            '<hr class="masthead__rule">'
            '<div class="masthead__folio">'
            f'<span>Vol. {esc(year)} · No. {count}</span>'
            f'<span class="masthead__motto">{esc(t["motto"])}</span>'
            f'<span>{esc(t["generated_by"])}</span>'
            '</div>'
            '<hr class="masthead__bar"><hr class="masthead__bar">'
            '</header>'
        )

        colophon = (
            '<footer class="colophon"><p><strong>The MiAZ Times</strong> '
            f'<span>{esc(t["colophon"])}</span></p></footer>'
        )

        if count == 0:
            notice = f'<h3 class="section-banner">{esc(t["no_documents"])}</h3>'
            return self._shell('The MiAZ Times', masthead + notice + colophon)

        # Lead = most recent document; the rest stream in workspace order.
        lead = max(docs, key=lambda d: d['date'] or '')
        stream_docs = [d for d in docs if d is not lead]

        lead_html = self._build_lead(lead)
        stream_html = ''.join(self._build_story(d) for d in stream_docs)

        index_rows = ''.join(
            f'<li><span class="name">{esc(name)}</span>'
            f'<span class="dots"></span><span class="count">{cnt}</span></li>'
            for name, cnt in sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
        )

        recent = sorted(docs, key=lambda d: d['date'] or '', reverse=True)[:3]
        recent_rows = ''.join(
            '<li>'
            f'<div class="brief__head">{esc(d["concept"]) or esc(d["filename"])}</div>'
            f'<div class="brief__sub">{esc(d["group_dsc"])} · {esc(self._short_date(d["date"]))}</div>'
            '</li>'
            for d in recent
        )

        edition = (
            '<div class="edition"><main>'
            f'<h3 class="section-banner">{esc(t["latest_filings"])}</h3>'
            f'<div class="stream">{stream_html}</div>'
            '</main>'
            '<aside class="rail">'
            f'<div class="box"><div class="box__title">{esc(t["in_this_edition"])}</div>'
            f'<ul class="index-list">{index_rows}</ul></div>'
            f'<div class="box"><div class="box__title">{esc(t["off_the_press"])}</div>'
            f'<ul class="brief">{recent_rows}</ul></div>'
            '</aside></div>'
        )

        return self._shell('The MiAZ Times',
                           masthead + lead_html + edition + colophon)

    def _build_lead(self, doc):
        t = self._i18n()
        link = href(doc['filename'])
        p1, p2 = self._lede(doc)
        return (
            f'<article class="lead" data-doc="{esc(doc["filename"])}">'
            '<div class="lead__kicker">'
            f'<span class="group">{esc(doc["group_dsc"])}</span> · {esc(doc["purpose_dsc"])}'
            '</div>'
            f'<h2 class="lead__headline">{esc(doc["concept"]) or esc(doc["filename"])}</h2>'
            f'<p class="lead__deck">{self._deck(doc)}</p>'
            '<div class="lead__byline">'
            f'<span>{_("From")} {esc(doc["sentby_dsc"])}</span>'
            '<span class="sep">·</span>'
            f'<span class="to">{_("to")} {esc(doc["sentto_dsc"])}</span>'
            '</div>'
            '<div class="lead__body">'
            f'<div class="lead__col"><p><span class="dateline">{esc(doc["country_dsc"])} —</span> {p1}</p></div>'
            f'<div class="lead__col"><p>{p2}</p></div>'
            '</div>'
            f'<a class="story__read" href="{link}">{esc(t["read_document"])}</a>'
            '</article>'
        )

    def _build_story(self, doc):
        link = href(doc['filename'])
        return (
            f'<a class="story" href="{link}">'
            '<div class="story__kicker">'
            f'<span class="group">{esc(doc["group_dsc"])}</span> · {esc(doc["purpose_dsc"])}'
            '</div>'
            f'<h4 class="story__headline">{esc(doc["concept"]) or esc(doc["filename"])}</h4>'
            f'<p class="story__summary">{self._summary(doc)}</p>'
            '<div class="story__meta">'
            f'<span>{esc(doc["sentby_dsc"])}</span>'
            f'<span class="to">→ {esc(doc["sentto_dsc"])}</span>'
            '</div>'
            '</a>'
        )

    def _build_article(self, doc):
        t = self._i18n()
        link = href(doc['filename'])
        p1, p2 = self._lede(doc)
        p3 = _('As with every entry in The MiAZ Times, this report is composed entirely from the document’s seven filing fields and links directly to the original held in your repository.')

        def fact(code, label, value):
            suffix = f' ({code})' if code else ''
            return f'<dt>{esc(label)}</dt><dd>{esc(value)}{esc(suffix)}</dd>'

        factbox = (
            '<div class="factbox">'
            f'<div class="factbox__title">{esc(t["on_the_record"])}</div><dl>'
            + f'<dt>{esc(t["f_date"])}</dt><dd>{esc(self._article_date(doc["date"]))}</dd>'
            + fact(doc['country'], t['f_country'], doc['country_dsc'])
            + fact(doc['group'], t['f_group'], doc['group_dsc'])
            + fact(doc['purpose'], t['f_purpose'], doc['purpose_dsc'])
            + f'<dt>{esc(t["f_sentby"])}</dt><dd>{esc(doc["sentby_dsc"])}</dd>'
            + f'<dt>{esc(t["f_concept"])}</dt><dd>{esc(doc["concept"])}</dd>'
            + f'<dt>{esc(t["f_sentto"])}</dt><dd>{esc(doc["sentto_dsc"])}</dd>'
            + '</dl></div>'
        )

        body = (
            '<header class="masthead">'
            '<h1 class="masthead__title" style="font-size:clamp(2.2rem,7vw,3.6rem);margin:0.2rem 0">The MiAZ Times</h1>'
            '<hr class="masthead__bar"><hr class="masthead__bar"></header>'
            f'<article class="article" data-doc="{esc(doc["filename"])}">'
            '<div class="article__breadcrumb">'
            f'<span>{esc(doc["group_dsc"])}</span> &nbsp;·&nbsp; '
            f'<span>{esc(doc["country_dsc"])}</span> &nbsp;·&nbsp; '
            f'<span>{esc(self._article_date(doc["date"]))}</span>'
            '</div>'
            f'<div class="article__kicker">{esc(doc["purpose_dsc"])}</div>'
            f'<h2 class="article__headline">{esc(doc["concept"]) or esc(doc["filename"])}</h2>'
            f'<p class="article__deck">{self._deck(doc)}</p>'
            '<div class="article__byline">'
            f'<span>{_("From")} {esc(doc["sentby_dsc"])}</span> &nbsp;&nbsp; '
            f'<span class="to">{_("to")} {esc(doc["sentto_dsc"])}</span>'
            '</div>'
            '<div class="article__body"><aside class="article__rail">'
            + factbox +
            '<div class="docpreview">'
            f'<span>{esc(t["preview_label"])}</span>'
            f'<a class="btn-open" href="{link}">{esc(t["open_document"])}</a>'
            '</div></aside>'
            '<div class="article__prose">'
            f'<p><span class="dateline">{esc(doc["country_dsc"])} —</span> {p1}</p>'
            f'<p>{p2}</p>'
            f'<p>{esc(p3)}</p>'
            '</div></div></article>'
            '<footer class="colophon"><p><strong>The MiAZ Times</strong> '
            f'<span>{esc(t["colophon_article"])}</span></p></footer>'
        )
        return self._shell('The MiAZ Times — Article', body)

    def _i18n(self):
        return {
            'documents': _('Documents'),
            'sections': _('Sections'),
            'motto': _('“Every paper in its place.”'),
            'generated_by': _('Generated by MiAZ'),
            'read_document': _('Read the document →'),
            'latest_filings': _('Latest Filings'),
            'in_this_edition': _('In This Edition'),
            'off_the_press': _('Off the Press'),
            'colophon': _('is set from your document repository and printed by the MiAZNewspaper plugin. Every story links to its file in the archive.'),
            'colophon_article': _('— composed from the filing record. Open the document to read the original.'),
            'on_the_record': _('On the Record'),
            'open_document': _('Open document'),
            'preview_label': _('Document preview'),
            'no_documents': _('No documents in this edition.'),
            'f_date': _('Date'),
            'f_country': _('Country'),
            'f_group': _('Group'),
            'f_purpose': _('Purpose'),
            'f_sentby': _('Sent by'),
            'f_concept': _('Concept'),
            'f_sentto': _('Sent to'),
        }
