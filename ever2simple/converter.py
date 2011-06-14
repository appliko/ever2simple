import json
import os
import sys
from csv import DictWriter
from cStringIO import StringIO
from dateutil.parser import parse
from html2text import _html2text
from lxml import etree


class EverConverter(object):
    """Evernote conversion runner
    """

    fieldnames = ['createdate', 'modifydate', 'content', 'tags']
    date_fmt = '%h %d %Y %H:%M:%S'

    def __init__(self, enex_filename, simple_filename=None, fmt='json'):
        self.enex_filename = os.path.expanduser(enex_filename)
        self.stdout = False
        if simple_filename is None:
            self.stdout = True
        self.simple_filename = simple_filename
        self.fmt = fmt

    def _load_xml(self, enex_file):
        try:
            xml_tree = etree.parse(enex_file)
        except (etree.XMLSyntaxError, ), e:
            print 'Could not parse XML'
            print e
            sys.exit(1)
        return xml_tree

    def prepare_notes(self, xml_tree):
        notes = []
        raw_notes = xml_tree.xpath('//note')
        for note in raw_notes:
            note_dict = {}
            title = note.xpath('title')[0].text
            # Use dateutil to figure out these dates
            # 20110610T182917Z
            created_string = parse(note.xpath('created')[0].text)
            updated_string = parse(note.xpath('updated')[0].text)
            note_dict['createdate'] = created_string.strftime(self.date_fmt)
            note_dict['modifydate'] = updated_string.strftime(self.date_fmt)
            tags = [tag.text for tag in note.xpath('tag')]
            if self.fmt == 'csv':
                tags = " ".join(tags)
            note_dict['tags'] = tags
            note_dict['content'] = ''
            content = note.xpath('content')
            if content:
                converted_text = self._convert_html_markdown(
                    title, content[0].text)
                if self.fmt == 'csv':
                    # XXX: dict writer can't handle unicode
                    converted_text = converted_text.encode('ascii', 'ignore')
                note_dict['content'] = converted_text
            notes.append(note_dict)
        return notes

    def convert(self):
        if not os.path.exists(self.enex_filename):
            print "File does not exist: %s" % self.enex_filename
            sys.exit(1)
        # TODO: use with here, but pyflakes barfs on it
        enex_file = open(self.enex_filename)
        xml_tree = self._load_xml(enex_file)
        enex_file.close()
        notes = self.prepare_notes(xml_tree)
        if self.fmt == 'csv':
            self._convert_csv(notes)
        if self.fmt == 'json':
            self._convert_json(notes)

    def _convert_html_markdown(self, title, text):
        html2plain = _html2text(None, "")
        html2plain.feed("<h1>%s</h1>" % title)
        html2plain.feed(text)
        return html2plain.close()

    def _convert_csv(self, notes):
        if self.simple_filename is None:
            simple_file = StringIO()
        else:
            simple_file = open(self.simple_filename, 'w')
        writer = DictWriter(simple_file, self.fieldnames)
        writer.writerows(notes)
        if self.stdout:
            simple_file.seek(0)
            # XXX: this is only for the StringIO right now
            print simple_file.getvalue()
        simple_file.close()

    def _convert_json(self, notes):
        if self.simple_filename is None:
            print json.dumps(notes)
        else:
            json.dump(notes, self.simple_filename)
