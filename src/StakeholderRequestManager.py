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

from PyQt4.QtCore import QObject
from PyQt4.QtCore import QRegExp
from PyQt4.QtCore import QSettings
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox
from RequestManager import RequestManager
from models import Activity
from models import Stakeholder
from models import Tag
from models import TagGroup
import os
from protocols import ActivityProtocol
from protocols import StakeholderProtocol
from qgis.core import QGis
from qgis.core import QgsFeature
from qgis.core import QgsField
from qgis.core import QgsGeometry
from qgis.core import QgsMapLayer
from qgis.core import QgsMapLayerRegistry
from qgis.core import QgsPoint
from qgis.core import QgsVectorLayer
import simplejson as json

class StakeholderRequestManager(RequestManager):

    configFile = "landmatrix.stakeholder.ini"

    def __init__(self, host, user, pw):
        RequestManager.__init__(self, host, user, pw)

        self.stakeholderProtocol = StakeholderProtocol(host, user, pw)


    def getStakeholders(self):
        # Connect to the stylePosted signal emitted by the GeoServer object
        self.connect(self.stakeholderProtocol, SIGNAL("readSignal( bool, int, str )"), self.getStakeholdersFinished)

        url = self.stakeholderProtocol.read(queryable="Name,Country", Name__ilike='Heng', Country__ilike='cambodia')
        self.log(url)

    def getStakeholdersFinished(self, success, statusCode, response):

        # It's necessary to disconnect this signal again
        self.disconnect(self.stakeholderProtocol, SIGNAL("readSignal( bool, int, str )"), self.getStakeholdersFinished)

        if success:
            # Parse the result
            stakeholders = self.parseStakeholdersResponse(response)

            # Get the first Uuid of the list
            if len(stakeholders) >= 1:
                self.log(stakeholders[0].id().toString())

    def parseStakeholdersResponse(self, jsonBody):

        stakeholders = []

        data = json.loads(str(jsonBody))
        for stakeholder in data['data']:

            s = Stakeholder(id=stakeholder['id'], version=stakeholder['version'])

            for taggroup in stakeholder['taggroups']:
                tg = TagGroup(id=taggroup['id'])
                mainTag = taggroup['main_tag']
                tg.setMainTag(Tag(id=mainTag['id'], key=mainTag['key'], value=mainTag['value']))

                for tag in taggroup['tags']:
                    t = Tag(id=tag['id'], key=tag['key'], value=tag['value'])
                    tg.addTag(t)

                s.addTagGroup(tg)

            stakeholders.append(s)

        return stakeholders

    def addStakeholders(self):
        self.connect(self.stakeholderProtocol, SIGNAL("created( bool, int, str"), self.addStakeholdersFinished)

        # Dummy stakeholder
        s = Stakeholder()
        tag = Tag(key="Name", value="Adrian Weber Investment")
        tagGroup = TagGroup()
        tagGroup.setMainTag(tag)
        tagGroup.addTag(tag)
        tagGroup.addTag(Tag(key="Country", value="Swaziland"))
        s.addTagGroup(tagGroup)

        msg, rawBody = self.stakeholderProtocol.add(s)
        self.log(msg)
        self.log(rawBody)

    def addStakeholdersFinished(self, success, statusCode, response):

        # Disconnect this signal
        self.disconnect(self.stakeholderProtocol, SIGNAL("created( bool, int, str"), self.addStakeholdersFinished)

        self.log(statusCode)

    def addStakeholdersFromLayer(self):
        """
        Import all stakeholders from the active layer to the Land Observatory
        platform.
        It is not (yet) tested if a stakeholder already exists or not.
        """

        # Connect to the protocol to get noticed as soon as the stakeholder has
        # been created
        self.connect(self.stakeholderProtocol, SIGNAL("created( bool, int, str"), self.addStakeholdersFinished)

        # Get the dict maps the attribute names from the landmatrix input Shapefile to the
        # fields defined in the global definition yaml
        identifierColumn, transformMap, groups = self.getTagGroupsConfiguration("landmatrix.stakeholder.ini")

        # Get the active layer and its data provider
        layer = self.iface.activeLayer()
        provider = layer.dataProvider()

        # The current feature
        feature = QgsFeature()

        # List of attribute indexes to select
        attributeIndexes = []
        # Dict that maps the field index to the fields defined in the global YAML
        fieldIndexMap = {}
        for (i, field) in provider.fields().iteritems():
            if str(field.name()) in transformMap:
                attributeIndexes.append(i)
                fieldIndexMap[i] = transformMap[str(field.name())]

        # Start data retreival: fetch geometry and necessary attributes for each feature
        provider.select(attributeIndexes)

        stakeholders = []

        # retreive every feature with its geometry and attributes
        while provider.nextFeature(feature):

            tagGroups = list(TagGroup() for i in range(len(groups)))

            # fetch map of attributes
            attrs = feature.attributeMap()

            # attrs is a dictionary: key = field index, value = QgsFeatureAttribute
            # show all attributes and their values
            for (k, attr) in attrs.iteritems():
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

            s = Stakeholder()
            for tg in tagGroups:
                if len(tg.tags) > 0:
                    s.addTagGroup(tg)

            stakeholders.append(s)

        msg, rawBody = self.stakeholderProtocol.add(stakeholders)
        self.log(msg)
        self.log(rawBody)

        # Disconnect the signal
        self.disconnect(self.stakeholderProtocol, SIGNAL("created( bool, int, str"), self.addStakeholdersFinished)

    def addStakeholdersFromLayerFinished(self, success, statusCode, response):

        if success:
            pass
