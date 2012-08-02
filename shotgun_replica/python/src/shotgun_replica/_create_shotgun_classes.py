# -*- coding: utf-8 -*-

"""
creates the auto generated entity-classes
"""

from shotgun_api3.shotgun import Shotgun
from pprint import pprint, pformat

from shotgun_replica import connectors, config, cleanSysName
from shotgun_replica.conversions import getDBConnection, getPgType

import os
import logging


def _createClassCode( entities, entitycode, fieldDefs, entityname ):
    classCode = ""

    prettiedformat = pformat( fieldDefs, indent = 4, width = 80 ).split( "\n" )
    indprettiedformat = ["              " + x for x in prettiedformat]
    fieldsstring = "    shotgun_fields = %s" % ( "\n".join( indprettiedformat ) )[14:]
    classString = """class %s(_ShotgunEntity):
    \"\"\"
    internal shotgun name: %s
    original shotgun name: %s
    \"\"\"
    
    _type = "%s"
    remote_id = None
    local_id = None
%s

""" % ( entityname, entitycode, entities[entitycode]["name"]["value"], entitycode, fieldsstring )
    fieldnames = fieldDefs.keys()
    fieldnames.sort()
    for field in fieldnames:
        # don't use "pivot_column"
        if field == "id":
            continue
        elif fieldDefs[field]["data_type"]["value"] in ["number",
            "float",
            "percent",
            "entity",
            "multi_entity",
            "date_time",
            "date",
            "time",
            "duration",
            "text",
            "tag_list",
            "status_list",
            "list",
            "checkbox",
            "url",
            "uuid",
            "color"]:
            classString += "    %s = None\n" % field
        elif fieldDefs[field]["data_type"]["value"] in ["image",
            "pivot_column",
            "password",
            "summary",
            "entity_type"]: # ??? what's that
            # these types are not supported
            pass
        else:
            pprint( fieldDefs[field] )

#        classString += "\n\n        super(%s, self).__init__(*args, **kargs)" % entityname
        #                pass
        #continue
    classCode += classString + "\n\n"
    if entitycode != entityname:
        classCode += """class %s(%s):
    \"\"\"
    wrapper-class for special types
    \"\"\"
    pass

""" % ( entitycode, entityname )
    return classCode

def _getDBFields( entityType ):

    conn = getDBConnection()
    queryCur = conn.cursor()
    createCur = conn.cursor()

    queryCur.execute( """SELECT * 
                        FROM information_schema.columns 
                        WHERE table_catalog=%s AND table_name=%s
                        ORDER BY ordinal_position""",
                        ( config.DB_DATABASE, entityType ) )

    allFields = {}
    for record in queryCur:
        column_name = record[3]
        data_type = record[7]
        if data_type == "USER-DEFINED":
            #debug(queryCur.description)
            #debug(record)
            data_type = record[27]
        elif data_type == "ARRAY":
            data_type = record[27][1:] + "[]"
        allFields[column_name] = data_type

    if queryCur.rowcount == 0:
        fieldstr = "\"__local_id\" SERIAL PRIMARY KEY"
        query = "CREATE TABLE \"%s\" (%s)" % ( entityType,
                                              fieldstr )
        logging.debug( query )
        createCur.execute( query )

    queryCur.close()
    createCur.close()

    return allFields


def _createDBFields( entitycode, fieldDefs ):

    conn = getDBConnection()
    queryCur = conn.cursor()
    createCur = conn.cursor()

    dbFields = _getDBFields( entitycode )

    for attribute in fieldDefs.keys():
        datatype = fieldDefs[attribute]["data_type"]["value"]
        postgresType = getPgType( datatype )
        if postgresType == None:
            logging.debug( "field %s.%s (%s) not handled" % ( entitycode, attribute, datatype ) )
            continue
        elif ( dbFields.has_key( attribute ) and dbFields[attribute] == postgresType ):
            pass
        elif ( dbFields.has_key( attribute ) and dbFields[attribute] != postgresType ):
            logging.debug( "changing type %s to %s" % ( dbFields[attribute], postgresType ) )
            query = "ALTER TABLE \"" + entitycode + "\" ALTER COLUMN \""
            query += str( attribute )
            query += "\" TYPE "
            query += postgresType
            logging.debug( query )
            createCur.execute( query )
        else:
            query = "ALTER TABLE \"" + entitycode + "\" ADD COLUMN \""
            query += str( attribute )
            query += "\" "
            query += postgresType
            logging.debug( query )
            createCur.execute( query )

#            if attribute in ["id", "name", "code"]:
#
#                query = "CREATE INDEX %s ON \"%s\" (\"%s\")" % ("%s_%s_idx" % (entitycode.lower(), attribute.lower()),
#                                                                entitycode,
#                                                                attribute)
#                debug(query)
#                createCur.execute(query)
        #debug("field %s.%s available" % (entitycode, attribute))

def main():
    """
    to be called
    """
    sg_url = "https://devilfant.shotgunstudio.com"
    sg_test1 = {"name": "test1",
                "key": "e398654c5ec1c6f7c8f71ead33349c58bbf4a058"}

    sg1 = Shotgun( sg_url,
                  sg_test1["name"],
                  sg_test1["key"] )


    entities = sg1.schema_entity_read()

    pprint( entities )

    moduleString = """# -*- coding: utf-8 -*-

\""" 
THIS FILE IS AUTO GENERATED

DO NOT EDIT IT DIRECTLY
change create_shotgun_classes.py instead 
\"""

from shotgun_replica._entity_mgmt import _ShotgunEntity

"""

    classes = entities.keys()
    classes.sort()

    for entitycode in classes:

        print "processing %s\n" % entitycode
        fieldDefs = sg1.schema_field_read( entitycode )

        theclass = connectors.getClassOfType( entitycode )
        if theclass != None:
            localFieldDefs = theclass.shotgun_fields
        else:
            localFieldDefs = None

        if fieldDefs != localFieldDefs:
            logging.error( "%s fielddefs differ from shotgun to local" % entitycode )

        entityname = cleanSysName( entities[entitycode]["name"]["value"] )
        if entitycode.endswith( "Connection" ):
            entityname = entitycode

        moduleString += _createClassCode( entities, entitycode, fieldDefs, entityname )

        _createDBFields( entitycode, fieldDefs )

    packageDir = os.path.dirname( __file__ )
    entityFilename = os.path.join( packageDir,
                                   'entities.py' )
    entity_file = open( entityFilename, 'w' )
    entity_file.write( moduleString )
    entity_file.close()

if __name__ == "__main__":
    main()