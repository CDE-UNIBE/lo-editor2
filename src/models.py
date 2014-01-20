"""
/***************************************************************************
lo-editor
A QGIS plugin to add and edit spatial information to land deals on the Land
Observatory platform.
                             -------------------
begin                : 2012-06-28 Semi-final Germany vs. Italy
copyright            : (C) 2012 by Adrian Weber
email                : adrian.weber@cde.unibe.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import QObject
from PyQt4.QtCore import QUuid
from PyQt4.QtCore import QVariant
from PyQt4.QtCore import pyqtProperty
from qgis.core import QgsFeature
import simplejson as json

class QPlainUuid(QUuid):
    """
    A subclass of QUuid that returns the plain uuid (i.e. without brackets) in
    method toString
    """

    def __init__(self, string):
        QUuid.__init__(self, string)

    def toString(self):
        """
        Return the uuid as String but without brackets
        """
        return super(QPlainUuid, self).toString().replace('{', '').replace('}', '')

class Tag(QObject):

    def __init__(self, ** kwargs):
        QObject.__init__(self)
        try:
            self.id = int(kwargs['id'])
        except KeyError:
            self.id = None

        try:
            self.key = unicode(kwargs['key'])
        except KeyError:
            self.key = None

        try:
            self.value = unicode(kwargs['value'])
        except KeyError:
            self.value = None

    def setId(self, id):
        self.id = int(id)

    def getId(self):
        return self.id

    def setKey(self, key):
        self.key = str(key)

    def getKey(self):
        return self.key

    def setValue(self, value):
        self.value = str(value)

    def getValue(self):
        return self.value

    def asDict(self):
        d = {}
        d['key'] = self.key
        d['value'] = self.value
        if self.id is not None:
            d['id'] = self.id

        return d

    def createDiff(self, otherTag):
        if otherTag is None:
            d = {}
            d['op'] = 'add'
            d['key'] = self.key
            d['value'] = self.value

            return d

    def __repr__(self):
        return "<Tag key: %s, value: %s, id: %s>" % (self.key, self.value, self.id)

class TagGroup(QObject):

    def __init__(self, ** kwargs):
        QObject.__init__(self)
        try:
            self.id = int(kwargs['id'])
        except KeyError:
            self.id = None

        self.tags = []
        self._mainTag = None

    def addTag(self, tag):
        self.tags.append(tag)

    def getTags(self):
        return self.tags

    def setId(self, id):
        self.id = int(id)

    def getId(self):
        return self.id

    def mainTag(self):
        return self._mainTag

    def setMainTag(self, value):
        self._mainTag = value

    def asDict(self):
        d = {}
        d['tags'] = [t.asDict() for t in self.tags]
        if self.id is not None:
            d['id'] = self.id
        if self.mainTag() is not None:
            d['main_tag'] = self.mainTag().asDict()

        return d

    def createDiff(self, otherTagGroup):
        if otherTagGroup is None:
            d = {}
            d['op'] = 'add'
            d['tags'] = [t.createDiff(None) for t in self.tags]
            #if self.mainTag() is not None:
            d['main_tag'] = self.mainTag().createDiff(None)

            return d

    def __repr__(self):
        repr = "<TagGroup id: %s" % self.id
        for t in self.tags:
            repr = "%s\n%s" % (repr, t)
        repr = "%s\n%s" % (repr, self.mainTag())
        repr = "%s\n>" % repr
        return repr

class Activity(QObject):

    def __init__(self, ** kwargs):
        QObject.__init__(self)

        try:
            self._id = QPlainUuid(kwargs['id'])
        except KeyError:
            self._id = None

        try:
            self._version = int(kwargs['version'])
        except KeyError:
            self._version = None

        self._tagGroups = []

    def asFeature(self):
        feature = QgsFeature()
        feature.setGeometry(self._geometry)

        # The Uuid as trimmed string
        id = self._id.toString()
        #feature.setAttributeMap({
        #                        0: QVariant(id),
        #                        1: QVariant(self._version)
        #                        })
        feature.setAttributes([(0, id), (1, self._version)])
        return feature


    def setVersion(self, version):
        self._version = int(version)

    def version(self):
        return self._version

    def setGeometry(self, geometry):
        self._geometry = geometry

    def setId(self, uuid):
        self._id = QPlainUuid(uuid)

    def id(self):
        return self._id

    def tagGroups(self):
        return self._tagGroups

    def addTagGroup(self, tagGroup):
        self._tagGroups.append(tagGroup)

    def createDiff(self, otherActivity):
        # If otherActivity is None a new stakeholder is created
        a = {}
        a['id'] = str(self._id.toString())
        coordinates = [self._geometry.asPoint().x(), self._geometry.asPoint().y()]
        a['geometry'] = {'type': 'Point', 'coordinates': coordinates}
        if otherActivity is None:
            a['taggroups'] = [tg.createDiff(None) for tg in self._tagGroups]

        return a

class Stakeholder(QObject):

    def __init__(self, ** kwargs):
        QObject.__init__(self)

        try:
            self._id = QPlainUuid(kwargs['id'])
        except KeyError:
            self._id = None

        try:
            self._version = int(kwargs['version'])
        except KeyError:
            self._version = None

        self.tagGroups = []

    def addTagGroup(self, tagGroup):
        self.tagGroups.append(tagGroup)

    def getTagGroups(self):
        return self.tagGroups

    def version(self):
        return self.version

    def setVersion(self, value):
        self._version = value

    def id(self):
        return self._id

    def setId(self, value):
        self._id = value

    def asDict(self):
        d = {}
        d['taggroups'] = [tg.asDict() for tg in self.tagGroups]
        if self.id is not None:
            d['id'] = self.id.toString()

        return d

    def createDiff(self, otherStakeholder):
        # If otherStakeholder is None a new stakeholder is created
        if otherStakeholder is None:
            d = {}
            d['taggroups'] = [tg.createDiff(None) for tg in self.tagGroups]

            return d

    def __repr__(self):

        repr = "<Stakeholder"
        try:
            repr = "%s %s" % (repr, self.id.toString())
        except AttributeError:
            pass
        repr = "%s\n" % repr

        for tg in self.tagGroups:
            repr = "%s%s" % (repr, tg)

        repr = "%s\n>" % repr

        return repr