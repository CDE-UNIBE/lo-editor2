"""
/***************************************************************************
lo-editor
A QGIS plugin to add and edit spatial information to land deals on the Land
Observatory platform.
                             -------------------
begin                : 2012-04-05 Holy Thursday
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

# Import the PyQt and QGIS libraries
from ActivityRequestManager import ActivityRequestManager
from OlaInterfaceDialog import OlaInterfaceDialog
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore
from StakeholderRequestManager import StakeholderRequestManager
from qgis.core import *
from qgis.gui import *
import resources_rc

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class OlaInterface(QObject):
    
    def __init__(self, iface):
        QObject.__init__(self)

        # Save reference to the QGIS interface
        self.iface = iface
        # Reference to the QGIS map canvas
        self.canvas = iface.mapCanvas()
        

    def initGui(self):
        """
        Creates the necessary actions
        """
        # Create an action to start capturing polygons and add it to the digitize toolbar
        icon = QIcon()
        icon.addPixmap(QPixmap(_fromUtf8(":/plugins/olainterface/lo-logo.png")), QIcon.Normal, QIcon.Off)
        self.openDialogAction = QAction(icon, "Land Observatory", self.iface.mainWindow())
        self.iface.pluginToolBar().addAction(self.openDialogAction)

        # Connect to signals for button behaviour
        self.connect(self.openDialogAction, SIGNAL("triggered()"), self.openDialog)
        

    def unload(self):
        """
        Remove the plugin menu item and icon from the toolbar
        """
        self.iface.pluginToolBar().removeAction(self.openDialogAction)

    def openDialog(self):
        """
        Open the main interface dialog
        """

        dialog = OlaInterfaceDialog(self.iface)
        #activityRequestManager.setLogger(dialog.getLogger())
        #stakeholderRequestManager.setLogger(dialog.getLogger())
        dialog.show()
        dialog.exec_()