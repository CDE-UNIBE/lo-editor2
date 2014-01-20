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

from ActivityRequestManager import ActivityRequestManager
from Logger import Logger
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebView
from Ui_ErrorMessage import Ui_Dialog as Ui_ErrorMessage
from Ui_OlaInterfaceDialog import Ui_OlaInterfaceDialog
from models import Activity
from qgis.core import *
from protocols import SettingsProtocol
import simplejson as json

class OlaInterfaceDialog(QDialog):

    readSettingsFinishedSignal = pyqtSignal( bool, int, str )

    def __init__(self, iface, ** kwargs):
        QDialog.__init__(self)

        self.iface = iface

        # Set up the user interface from Designer.
        self.ui = Ui_OlaInterfaceDialog()
        self.ui.setupUi(self)
        self.logger = self.getLogger()
        self.treeWidget = self.findChildren(QTreeWidget, 'taggroupTreeWidget')[0]

        self.settings = QSettings("Land Observatory", "Land Observatory Polygon Editor")

    def log(self, message):
        if self.logger is not None:
            self.logger.log(message)

    def getLogger(self):
        self.loggingTextEdit = self.findChildren(QPlainTextEdit, "loggingTextEdit")[0]
        return Logger(self.loggingTextEdit)

    def getActivityByIdFinished(self, success, statusCode, response):

        # Disconnect events
        self.activityRequestManager.disconnect(self.activityRequestManager.activityProtocol, SIGNAL("readSignal( bool, int, str )"), self.getActivityByIdFinished)

        keys = []
        for i in self.settings.value("mainkeys"):
            keys.append(str(i))

        try:
            data = json.loads(str(response))

            self.treeWidget.clear()

            self.currentActivity = Activity(id=data['data'][0]['id'], version=data['data'][0]['version'])

            layers = []

            for taggroup in data['data'][0]['taggroups']:

                try:
                    tgItem = QTreeWidgetItem(self.treeWidget.invisibleRootItem())
                    tgItem.setText(0, "%s: %s" % (taggroup['main_tag']['key'], taggroup['main_tag']['value']));

                    idItem = QTreeWidgetItem(tgItem)
                    idItem.setText(0, "id: %s" % (taggroup['tg_id']))
                    
                    tagNr = 0
                    for tag in taggroup['tags']:
                        tItem = QTreeWidgetItem(tgItem)
                        tItem.setText(tagNr, "%s: %s" % (tag['key'], tag['value']))
                        tagNr += 1

                    if taggroup['main_tag']['key'] in keys:

                        # Create a memory layer per taggroup
                        l = QgsVectorLayer("MultiPolygon?crs=epsg:4326&index=yes", "%s: %s" % (taggroup['main_tag']['key'], taggroup['main_tag']['value']), "memory")
                        provider = l.dataProvider()
                        # update layer's extent when new features have been added
                        # because change of extent in provider is not propagated to the layer
                        l.updateExtents()

                        #pr = taggroupLayer.dataProvider()
                        self.connect(l, SIGNAL("layerModified( bool )"), self._layer_modified)

                        if 'geometry' in taggroup:

                            if taggroup['geometry']['type'].lower() == "MultiPolygon".lower():

                                polygon_list = []

                                for polygon in taggroup['geometry']['coordinates']:

                                    polyline_list = []

                                    for polyline in polygon:

                                        point_list = []

                                        for point in polyline:
                                            point_list.append(QgsPoint(point[0], point[1]))

                                        polyline_list.append(point_list)

                                    polygon_list.append(polyline_list)

                                multiPolygon = QgsGeometry.fromMultiPolygon(polygon_list)
                                feature = QgsFeature()
                                feature.setGeometry(multiPolygon)
                                feature.setAttributes({})
                                provider.addFeatures([feature])

                        # Set custom property to this layer
                        l.setCustomProperty("lo", True)
                        l.setCustomProperty("id", taggroup['tg_id'])
                        layers.append(l)
                except:
                    # A KeyError is thrown if the main_tag of the current taggroup is null
                    pass

            QgsMapLayerRegistry.instance().addMapLayers(layers)
        except:
            pass

    @pyqtSlot()
    def getActivitiesFinished(self, success, statusCode, response):

        self.activityRequestManager.disconnect(self.activityRequestManager.activityProtocol, SIGNAL("readSignal( bool, int, QString )"), self.getActivitiesFinished)

        if not success:
            dialog = QDialog()
            dialog.ui = Ui_ErrorMessage()
            dialog.ui.setupUi(dialog)
            dialog.setModal(True)
            browser = dialog.findChildren(QWebView, "webView")[0]
            browser.setHtml(response)
            dialog.show()
            dialog.exec_()
            return None

        # Create a memory layer
        self.activityLayer = QgsVectorLayer("Point?crs=epsg:4326&field=id:string(80)&field=version:integer&index=yes", "Land deals representation points", "memory")
        pr = self.activityLayer.dataProvider()

        activities = self._parse_activities_response(response)

        pr.addFeatures([a.asFeature() for a in activities])

        # update layer's extent when new features have been added
        # because change of extent in provider is not propagated to the layer
        self.activityLayer.updateExtents()

        self.activityLayer.setCustomProperty('edited', False)
        self.connect(self.activityLayer, SIGNAL("layerModified( bool )"), self._activity_layer_modified)

        QgsMapLayerRegistry.instance().addMapLayer(self.activityLayer)

        sw = self.findChildren(QStackedWidget, "stackedWidget")[0]
        sw.setCurrentIndex(1)

    def _read_settings_finished(self, success, status, data):

        if success:
            self.logger.log(data)

            s = json.loads(str(data))

            self.settings.setValue("mainkeys", s['mainkeys'])

    # See http://pyqt.sourceforge.net/Docs/PyQt4/new_style_signals_slots.html
    # for this style of connecting to signals
    @pyqtSlot()
    def on_closeButton_clicked(self):
        self.close()

    @pyqtSlot()
    def on_startEditingActivityButton_clicked(self):

        host = self.findChildren(QLineEdit, "hostLineEdit")[0].text()
        user = self.findChildren(QLineEdit, "userLineEdit")[0].text()
        password = self.findChildren(QLineEdit, "passwordLineEdit")[0].text()

        self.activityRequestManager = ActivityRequestManager(host, user, password)
        self.activityRequestManager.setLogger(self.getLogger())

        selectedFeatures = self.iface.activeLayer().selectedFeatures()
        if len(selectedFeatures) == 0:
            QMessageBox.warning(self, "No activity selected", "Select an Activity")
            return
        if len(selectedFeatures) > 1:
            QMessageBox.warning(self, "Too many activities selected", "Select exactly one Activity")
            return

        feature = selectedFeatures[0]
        attributes = feature.attributes()
        uuid = attributes[0][1]

        self.activityRequestManager.getActivityById(uuid, self)

        sw = self.findChildren(QStackedWidget, "stackedWidget")[0]
        sw.setCurrentIndex(2)

    @pyqtSlot()
    def on_submitActivityButton_clicked(self):

        diffObject = {}
        diffObject['activities'] = []
        activity = {"id": str(self.currentActivity.id().toString()), "version": self.currentActivity.version()}

        if self.activityLayer.customProperty('edited', False):

            provider = self.activityLayer.dataProvider()

            feature = QgsFeature()

            # start data retreival: fetch geometry and all attributes for each feature
            provider.select([0])

            # retreive every feature with its geometry and attributes
            while provider.nextFeature(feature):

                if feature.attributes()[0].toString() == self.currentActivity.id().toString():

                    p = feature.geometry().asPoint()

                    activity['geometry'] = {
                    "type": "Point",
                    "coordinates": [ p.x(), p.y() ]
                    }

                    break

        activity['taggroups'] = []

        for id in QgsMapLayerRegistry.instance().mapLayers():
            qgsLayer = QgsMapLayerRegistry.instance().mapLayer(id)
            if qgsLayer.customProperty("lo", False):
                id = qgsLayer.customProperty("id")

                # Add also key tags to satisfy the protocol
                taggroup = {"tg_id": id, "op": "add", "tags": []}

                #provider = qgsLayer.dataProvider()

                #feature = QgsFeature()
                #allAttrs = provider.attributeIndexes()

                # start data retreival: fetch geometry and all attributes for each feature
                #provider.select(allAttrs)

                polygon_list = []

                # retreive every feature with its geometry and attributes
                for feature in qgsLayer.getFeatures():

                    # fetch geometry
                    geometry = feature.geometry()

                    if geometry.wkbType() == QGis.WKBPolygon:
                        polygon = geometry.asPolygon()
                        polygon_list.append(polygon)

                    if geometry.wkbType() == QGis.WKBPolygon25D:
                        polygon = geometry.asPolygon()
                        polygon_list.append(polygon)

                    if geometry.wkbType() == QGis.WKBMultiPolygon:
                        multiPolygon = geometry.asMultiPolygon()
                        for polygon in multiPolygon:
                            polygon_list.append(polygon)

                    if geometry.wkbType() == QGis.WKBMultiPolygon25D:
                        multiPolygon = geometry.asMultiPolygon()
                        for polygon in multiPolygon:
                            polygon_list.append(polygon)

                multiPolygon = QgsGeometry().fromMultiPolygon(polygon_list)
                if multiPolygon is not None:
                    # Carefully! Method exportToGeoJSON is not exposed to the Python bindings!
                    #taggroup['geometry'] = json.loads(unicode(multiPolygon.exportToGeoJSON()))

                    if multiPolygon.wkbType() == QGis.WKBMultiPolygon:
                        json_geometry = {"type": "MultiPolygon"}
                        json_geometry['coordinates'] = []
                        for polygon in multiPolygon.asMultiPolygon():
                            json_polygon = []
                            for polyline in polygon:
                                json_polyline = []
                                for point in polyline:
                                    json_polyline.append([point.x(), point.y()])
                                json_polygon.append(json_polyline)
                            json_geometry['coordinates'].append(json_polygon)
                        
                        taggroup['geometry'] = json_geometry
                        activity['taggroups'].append(taggroup)

        diffObject['activities'].append(activity)
        self.log(json.dumps(diffObject))

        # Get connection details
        host = self.findChildren(QLineEdit, "hostLineEdit")[0].text()
        user = self.findChildren(QLineEdit, "userLineEdit")[0].text()
        password = self.findChildren(QLineEdit, "passwordLineEdit")[0].text()

        self.activityRequestManager = ActivityRequestManager(host, user, password)
        self.activityRequestManager.setLogger(self.getLogger())

        self.activityRequestManager.postActivity(diffObject, self)

    def postActivityFinished(self, success, statusCode, response):

        if success:

            json_response = json.loads(str(response))
            msg = json_response['msg']

            QMessageBox(QMessageBox.Information, "Success", msg, QMessageBox.Ok, self).show()
        else:
            dialog = QDialog()
            dialog.ui = Ui_ErrorMessage()
            dialog.ui.setupUi(dialog)
            dialog.setModal(True)
            browser = dialog.findChildren(QWebView, "webView")[0]
            browser.setHtml(response)
            dialog.show()
            dialog.exec_()
        return None

    @pyqtSlot()
    def on_getActivitiesButton_clicked(self):

        host = self.findChildren(QLineEdit, "hostLineEdit")[0].text()
        user = self.findChildren(QLineEdit, "userLineEdit")[0].text()
        password = self.findChildren(QLineEdit, "passwordLineEdit")[0].text()

        self.activityRequestManager = ActivityRequestManager(host, user, password)
        self.activityRequestManager.setLogger(self.getLogger())

        self.activityRequestManager.getActivities(self.iface.mapCanvas().extent(), self)

        # Read the settings from the server
        self.settingsProtocol = SettingsProtocol(host, user, password)
        #self.connect(self.settingsProtocol, SIGNAL("readSignal( bool, int, str )"), self._read_settings_finished)
        self.readSettingsFinishedSignal.connect(self._read_settings_finished)
        url = self.settingsProtocol.read()
        self.logger.log(url)

    @pyqtSlot()
    def on_back1Button_clicked(self):

        # Get all taggroup layers
        layersToRemove = self._get_taggroup_layers()

        # Get layer with deals
        try:
            layersToRemove.append(self.activityLayer.id())
        except RuntimeError:
            pass

        # Remove all these layers
        QgsMapLayerRegistry.instance().removeMapLayers(layersToRemove)

        # Go back to first widget
        sw = self.findChildren(QStackedWidget, "stackedWidget")[0]
        sw.setCurrentIndex(0)

    @pyqtSlot()
    def on_back2Button_clicked(self):

        # Remove all layers from the map
        QgsMapLayerRegistry.instance().removeMapLayers(self._get_taggroup_layers())

        # Remove all items in the tree widget
        self.treeWidget.clear()

        # Go back to first widget
        sw = self.findChildren(QStackedWidget, "stackedWidget")[0]
        sw.setCurrentIndex(1)

    @pyqtSlot()
    def on_clearLogButton_clicked(self):
        self.logger.reset()
        

    def _get_taggroup_layers(self):
        layers = []
        for id in QgsMapLayerRegistry.instance().mapLayers():
            qgsLayer = QgsMapLayerRegistry.instance().mapLayer(id)
            if qgsLayer.customProperty("lo", False):
                layers.append(id)

        return layers

    def _parse_activities_response(self, jsonBody):
        """

        """

        activities = []

        data = json.loads(str(jsonBody))
        for activity in data['data']:
            # Create a new activity
            a = Activity(id=activity['id'], version=activity['version'])
            # Get the point coords and set the geometry
            coords = activity['geometry']['coordinates']
            a.setGeometry(QgsGeometry.fromPoint(QgsPoint(coords[0], coords[1])))

            # Append it to the list
            activities.append(a)

        return activities

    def _layer_modified(self, onlyGeometry, * args, ** kwargs):
        pass

    def _activity_layer_modified(self, onlyGeometry, * args, ** kwargs):

        if onlyGeometry:
            self.activityLayer.setCustomProperty("edited", True)