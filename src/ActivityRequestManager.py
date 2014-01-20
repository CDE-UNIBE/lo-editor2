"""
/***************************************************************************
lo-editor
A QGIS plugin to add and edit spatial information to land deals on the Land
Observatory platform.
                             -------------------
begin                : 2012-07-02
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

import os

from PyQt4.QtCore import QObject
from PyQt4.QtCore import QRegExp
from PyQt4.QtCore import QSettings
from PyQt4.QtCore import QUuid
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QMessageBox
from RequestManager import RequestManager
from models import Activity
from models import QPlainUuid
from models import Stakeholder
from models import Tag
from models import TagGroup
from protocols import ActivityProtocol
from protocols import StakeholderProtocol
from qgis.core import QGis
from qgis.core import QgsApplication
from qgis.core import QgsFeature
from qgis.core import QgsField
from qgis.core import QgsGeometry
from qgis.core import QgsMapLayer
from qgis.core import QgsMapLayerRegistry
from qgis.core import QgsPoint
from qgis.core import QgsVectorLayer
import simplejson as json

class ActivityRequestManager(RequestManager):

    configFile = "landmatrix.activity.ini"

    created = pyqtSignal( bool, int, str )

    def __init__(self, host, user, pw):
        RequestManager.__init__(self, host, user, pw)

        self.activityProtocol = ActivityProtocol(host, user, pw)
        self.activityLayer = None

    def getActivities(self, extent, dialog):

        # Connect to the stylePosted signal emitted by the GeoServer object
        self.connect(self.activityProtocol, SIGNAL("readSignal( bool, int, QString )"), dialog.getActivitiesFinished)
        #self.readSignal.connect(dialog.getActivitiesFinished)

        url = self.activityProtocol.read(extent)
        self.log(url)

    def getActivityById(self, id, dialog):
        # Connect to the stylePosted signal emitted by the GeoServer object
        self.connect(self.activityProtocol, SIGNAL("readSignal( bool, int, QString )"), dialog.getActivityByIdFinished)

        url = self.activityProtocol.readById(id)
        self.log(url)

    def postActivity(self, diffObject, dialog):

        self.connect(self.activityProtocol, SIGNAL("updated( bool, int, QString )"), dialog.postActivityFinished)

        url = self.activityProtocol.update(diffObject)
        self.log(url)

    def addActivitiesFromLayer(self):
        """
        """

        def _createNewActivity(id=None, otherActivity=None):

            # Connect to the protocol signal
            self.connect(self.activityProtocol, SIGNAL("created( bool, int, QString )"), _createNewActivityFinished)

            # Create a new Uuid
            if id is not None:
                uid = QPlainUuid(id)
            else:
                uid = QPlainUuid(QUuid.createUuid())

            tagGroups = list(TagGroup() for i in range(len(groups)))

            # attrs is a dictionary: key = field index, value = QgsFeatureAttribute
            # show all attributes and their values
            self.log("Attribute list:")
            for (k, attr) in attrs.iteritems():
                if k is not identifierColumnIndex:
                    self.log("%s: %s" % (fieldIndexMap[k], attr.toString()))

                    # First search the correct taggroup to append
                    attributeName = provider.fields()[k].name()
                    currentTagGroup = 0
                    for g in groups:
                        if attributeName in g:
                            break
                        else:
                            currentTagGroup += 1

                    if attr is not None and attr.toString() != '':
                        tag = Tag(key=fieldIndexMap[k], value=attr.toString())
                        tagGroups[currentTagGroup].addTag(tag)
                        if tagGroups[currentTagGroup].mainTag() is None:
                            tagGroups[currentTagGroup].setMainTag(tag)

            a = Activity(id=uid)
            a.setGeometry(feature.geometry())
            for tg in tagGroups:
                if len(tg.tags) > 0:
                    a.addTagGroup(tg)

            wrapperObj = {}

            wrapperObj['activities'] = [a.createDiff(otherActivity)]

            self.activityProtocol.add(json.dumps(wrapperObj, sort_keys=True, indent=4 * ' '))


        def _createNewActivityFinished(success, statusCode, response):

            # Connect to the protocol signal
            self.disconnect(self.activityProtocol, SIGNAL("created( bool, int, QString )"), _createNewActivityFinished)

            # The newly returned activity should be parsed and the ID needs to
            # be written to the QgsFeature

            self.log("Server returned status code %i and response:\n%s" % (statusCode, response))

        def _checkActivityExists(uid):

            self.connect(self.activityProtocol, SIGNAL("readSignal( bool, int, QString )"), _checkActivityExistsFinished)

            self.activityProtocol.readById(uid.toString())
            self.log("Check if activity exists:")

        def _checkActivityExistsFinished(success, statusCode, response):

            self.disconnect(self.activityProtocol, SIGNAL("readSignal( bool, int, QString )"), _checkActivityExistsFinished)

            self.log("Server returned status code %i and response:\n%s" % (statusCode, response))

            activities = self.parseActivitiesResponse(response)
            if len(activities) == 0:
                self.log("Activity does not yet exist")
                _createNewActivity(uid)

            #else:
                #   _createNewActivity(uid, activities[0])


        # Get the dict that maps the attribute names from the landmatrix input Shapefile to the
        # fields defined in the global definition yaml
        identifierColumn, transformMap, groups = self.getTagGroupsConfiguration("landmatrix.activity.ini")

        # Get the active layer and its data provider
        layer = self.iface.activeLayer()
        provider = layer.dataProvider()

        # The current feature
        feature = QgsFeature()

        # List of attribute indexes to select
        attributeIndexes = []
        # Dict that maps the field index to the fields defined in the global YAML
        fieldIndexMap = {}

        # Find the index of the uuid column
        identifierColumnIndex = None

        for (i, field) in provider.fields().iteritems():
            if str(field.name()) in transformMap:
                attributeIndexes.append(i)
                fieldIndexMap[i] = transformMap[str(field.name())]
            elif field.name() == str(identifierColumn):
                identifierColumnIndex = i


        # Start data retreival: fetch geometry and necessary attributes for each feature
        provider.select(attributeIndexes + [identifierColumnIndex])

        # retreive every feature with its geometry and attributes
        while provider.nextFeature(feature):

            
            # fetch map of attributes
            attrs = feature.attributeMap()

            # Get the identifier value
            identifierValue = attrs[identifierColumnIndex].toString()

            # If the identifier is empty or None, create a new activity.
            # This should only be necessary at the initial imports
            if identifierValue is None or str(identifierValue) == str(''):
                _createNewActivity()

            #if str(idenitfierValue).contains(QRegExp('a0c78834-fd98-4d4d-b8b5-0754b50f2510'))
            else:
                uid = QPlainUuid(identifierValue)
                _checkActivityExists(uid)

    def addActivitiesFromLayerFinished(self, success, statusCode, reason):
        QMessageBox.warning(self.iface.mainWindow(), reason, "Server returned %i." % statusCode)
        pass



