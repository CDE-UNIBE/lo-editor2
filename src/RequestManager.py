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
from PyQt4.QtCore import QRegExp
from PyQt4.QtCore import QSettings
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox
from Logger import Logger
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

class RequestManager(QObject):

    activityProtocol = None
    stakeholderProtocol = None

    logger = None

    def __init__(self, host, user, pw):
        QObject.__init__(self)

        self.activityProtocol = ActivityProtocol(host, user, pw)
        self.stakeholderProtocol = StakeholderProtocol(host, user, pw)

    def log(self, message):
        if self.logger is not None:
            self.logger.log(message)

    def setLogger(self, logger):
        self.logger = logger


    def getTagGroupsConfiguration(self, filename):
        """
        Configure in an external file the attributes that belong together to a
        taggroup. This configuration file is also used to decide which attributes
        are considered. The file needs to be in the ini format in the following
        form:
        [taggroup1]
        attribute1_name=key1
        attribute2_name=key2

        [taggroup2]
        attribute3_name=key1
        attribute4_name=key2

        etc.

        The ini format has been chosen because Qt has the in-built class QSettings
        to read that format (unlike e.g. YAML)

        """
        settings = QSettings("%s/%s" % (os.path.dirname(__file__), filename), QSettings.IniFormat)

        # Two-dimensional array with taggroups
        groups = []
        # Dictionary that maps the attribute names to LO keys
        transformMap = {}
        # The attribute column in the GIS layer that holds the Uuid
        identifierColumn = None

        # Loop all groups
        for i in settings.childGroups():
            settings.beginGroup(i)
            keys = []
            # Check if the current group defines a taggroup
            if i.contains(QRegExp('taggroup[0-9+]')):
                for j in settings.allKeys():
                    keys.append(str(j))
                    transformMap[str(j)] = str(settings.value(j).toString())
            # Check if the current group defines general settings
            elif i.contains(QRegExp('settings')):
                for j in settings.allKeys():
                    if settings.value(j) == 'activity_identifier':
                        identifierColumn = str(j)

            # End this group
            settings.endGroup()
            groups.append(keys)

        return identifierColumn, transformMap, groups


