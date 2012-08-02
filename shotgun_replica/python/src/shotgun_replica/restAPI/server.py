"""
RESTful interface to database
"""

import web
import json

from shotgun_replica import connectors, factories
import urlparse
import logging
import sys

def intOrNone( value ):
    if value == None:
        return None
    else:
        return int( value )

class Handler( object ):
    def GET( self, entityType, localID, remoteID ):
        """
        retrieve an object
        """

        if localID:
            entity = self._getEntity( entityType, localID, remoteID )

            if entity:
                return json.dumps( entity.getShotgunDict() )
            else:
                return web.notfound()
        else:

            userData = web.input()

            filters = []
            filterValues = []
            for attribute in userData.keys():
                filters.append( "%s=%s" % ( attribute, "%s" ) )
                filterValues.append( userData[attribute] )

            entities = factories.getObjects( entityType, " AND ".join( filters ), filterValues )
            json_entities = []

            for entity in entities:
                json_entities.append( entity.getShortDict() )

            return json.dumps( json_entities )

    def DELETE( self, entityType, localID, remoteID ):
        """
        delete an object
        """
        entity = self._getEntity( entityType, localID, remoteID )

        if entity:
            return entity.delete()
        else:
            return web.notfound()

    def PUT( self, entityType, localID, remoteID ):
        """
        update an object
        """
        entity = self._getEntity( entityType, localID, remoteID )

        if not entity:
            return web.notfound()

        newData = self._parseInput()

        entity = updateEntity( entity, newData )

        return json.dumps( entity.getDict() )

    def POST( self, entityType, localID, remoteID ):
        """
        create an object
        """
        entityClass = connectors.getClassOfType( entityType )
        if not entityClass: raise web.notfound()

        data = self._parseInput()

        entity = createEntity( entityClass, data )
        return json.dumps( entity.getDict() )

    def _getEntity( self, entityType, localID, remoteID ):
        entityClass = connectors.getClassOfType( entityType )
        if not entityClass:
            raise web.notfound()

        entity = factories.getObject( entityType,
                                      remote_id = intOrNone( remoteID ),
                                      local_id = intOrNone( localID ) )
        return entity

    def _parseInput( self ):
        userData = dict( urlparse.parse_qsl( web.data() ) )
        data = json.loads( userData["data"] )
        return data

def updateEntity( entity, dataDict ):
    entity.loadFromDict( dataDict )
    entity.save()
    return entity

def createEntity( entityClass, dataDict ):
    entity = entityClass()
    return updateEntity( entity, dataDict )

def startServer():
    urls = ( 
        '/(\w*)\/?(.+)?\/?(.+)?', 'Handler'
    )
    logging.basicConfig( level = logging.DEBUG,
                         stream = sys.stdout )
    global app
    app = web.application( urls, globals() )
    app.run()

def stopServer():
    app.stop()

if __name__ == "__main__":
    startServer()