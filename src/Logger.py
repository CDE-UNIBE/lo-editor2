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

class Logger(QObject):

    qTextEdit = None

    def __init__(self, qTextEdit):
        QObject.__init__(self)
        self.qTextEdit = qTextEdit

    def log(self, message):
        if message is not None:
            self.qTextEdit.appendPlainText(message)

    def reset(self):
        self.qTextEdit.setPlainText("")