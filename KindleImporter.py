#-*- coding:utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')  # helps with odd formatting
import os
import sqlite3
import time
import re
import aqt
from aqt import mw
from aqt.qt import *
import aqt.importing
import anki
from anki.db import DB
from anki import importing
from anki.importing.csvfile import TextImporter
from anki.importing.apkg import AnkiPackageImporter
from anki.importing.anki2 import Anki2Importer
from anki.importing.supermemo_xml import SupermemoXmlImporter
from anki.importing.mnemo import MnemosyneImporter
from anki.importing.pauker import PaukerImporter
from anki.importing.noteimp import NoteImporter, ForeignNote, ForeignCard
from anki.stdmodels import addBasicModel, addClozeModel
from anki.lang import ngettext, currentLang, _
from anki.hooks import addHook, runHook, wrap
from aqt.utils import shortcut, showInfo, showText, tooltip


if currentLang == 'zh_CN':
    tags = [u'单词', u'单词原型', u'例句', u'书籍', u'创建时间']
    import_mode = u'导入单词字段相同但其他字段不同的生词'
else:
    tags = [u'Word', u'Stem', u'Usage', u'Book', u'Create Time']


class KindleDbImporter(TextImporter):
    needDelimiter = False
    needMapper = True

    # def __init__

    def openFile(self):
        db = DB(self.file)
        notes = {}
        note = None
        self.data = list()
        # showInfo('begin execute sql')
        results = db.execute(
            "select ws.id, ws.word, ws.stem, ws.lang, datetime(ws.timestamp*0.001, 'unixepoch', 'localtime'), lus.usage, bi.title, bi.authors from words as ws left join lookups as lus on ws.id=lus.word_key left join book_info as bi on lus.book_key=bi.id")
        self.fileobj = 1   # make sure file open ok
        # showInfo(str(len(results)))
        self.data = []
        for item in results:
            item = list(item)
            for i, each in enumerate(item):
                if not each:
                    item[i] = ""
            id, word, stem, create_time, useage, book_title, book_authors = item[
                0], item[1], item[2], item[4], item[5], item[6], item[7]
            self.data.append([word, stem, useage.replace(
                word, u'<b>%s</b>' % word), u'%s ---- %s' % (book_title, book_authors), create_time])

        self.numFields = len(tags)
        self.initMapping()

    def foreignNotes(self):
        self.open()
        self.tagsToAdd = tags
        notes = []
        for d in self.data:
            note = ForeignNote()
            note.fields.extend(d)
            notes.append(note)
        return notes


def customImportMode(self):
    self.frm.importMode.insertItem(
        4, u'Import when first field matches existing note but other fields does not match.')


def showMapping(self, keepMapping=False, hook=None):
    if hook:
        hook()
    if not keepMapping:
        self.mapping = self.importer.mapping
    self.frm.mappingGroup.show()
    assert self.importer.fields()
    # set up the mapping grid
    if self.mapwidget:
        self.mapbox.removeWidget(self.mapwidget)
        self.mapwidget.deleteLater()
    self.mapwidget = QWidget()
    self.mapbox.addWidget(self.mapwidget)
    self.grid = QGridLayout(self.mapwidget)
    self.mapwidget.setLayout(self.grid)
    self.grid.setContentsMargins(3, 3, 3, 3)
    self.grid.setSpacing(6)
    fields = self.importer.fields()
    for num in range(len(self.mapping)):
        i = 0
        text = _("Field <b>%d</b> of file is:") % (num + 1)
        self.grid.addWidget(QLabel(text), num, i)
        i += 1
        # , tags[num]
        if isinstance(self.importer, KindleDbImporter):
            text = _(tags[num])
            self.grid.addWidget(QLabel(text), num, i)
            i += 1
        if self.mapping[num] == "_tags":
            text = _("mapped to <b>Tags</b>")
        elif self.mapping[num]:
            text = _("mapped to <b>%s</b>") % self.mapping[num]
        else:
            text = _("<ignored>")
        self.grid.addWidget(QLabel(text), num, i)
        i += 1
        button = QPushButton(_("Change"))
        self.grid.addWidget(button, num, i)
        button.clicked.connect(lambda _, s=self, n=num: s.changeMappingNum(n))

aqt.importing.ImportDialog.setupMappingFrame = wrap(
    aqt.importing.ImportDialog.setupMappingFrame, customImportMode)
aqt.importing.ImportDialog.showMapping = showMapping


def my_importFile(mw, file):
    if mw.custom == 'kindle db':
        file += '.kindle'


def custom(self):
    self.import_src = 'kindle db'

aqt.main.AnkiQt.custom = custom


# def __my_init__(self, mw, importer):
#     ''' hide the autodetect button to avoid misleading '''
#     QDialog.__init__(self, mw, Qt.Window)
#     self.mw = mw
#     self.importer = importer
#     self.frm = aqt.forms.importing.Ui_ImportDialog()
#     self.frm.setupUi(self)
#     self.frm.buttonBox.button(QDialogButtonBox.Help).clicked.connect(
#         self.helpRequested)
#     self.setupMappingFrame()
#     self.setupOptions()
#     self.modelChanged()
#     self.frm.autoDetect.setVisible(self.importer.needDelimiter)
#     addHook("currentModelChanged", self.modelChanged)
#     self.frm.autoDetect.clicked.connect(self.onDelimiter)
#     self.updateDelimiterButtonText()
#     self.frm.allowHTML.setChecked(
#         self.mw.pm.profile.get('allowHTML', True))
#     self.frm.importMode.setCurrentIndex(
#         self.mw.pm.profile.get('importMode', 1))
#     # import button
#     b = QPushButton(_("Import"))
#     self.frm.buttonBox.addButton(b, QDialogButtonBox.AcceptRole)
#     if importer is KindleDbImporter:
#         self.frm.autoDetect.setVisible(False)
#     self.exec_()

# aqt.importing.ImportDialog.__init__ = __my_init__

# 原始importFile函数根据后缀名选择第一个符合条件的导入器，db后缀与原有mnemosyne导入器一致
# 如果要修改原始的importFile函数，只能在函数中间代码中加，不能应用monkey patch
# 所以这里或者全部重写importFile
# 或者修改kindle db文件在选择列表中的位置，但这样的话无法导入mnemosyne的db文件
# 或者导入前更改kindle db的后缀名
importing.Importers = (
    (_("Text separated by tabs or semicolons (*)"), TextImporter),
    (_("Packaged Anki Deck (*.apkg *.zip)"), AnkiPackageImporter),
    (_("Kindle vocab (*.db)"), KindleDbImporter),
    (_("Mnemosyne 2.0 Deck (*.db)"), MnemosyneImporter),
    (_("Supermemo XML export (*.xml)"), SupermemoXmlImporter),
    (_("Pauker 1.8 Lesson (*.pau.gz)"), PaukerImporter),
)
