# -*- coding: utf-8 -*-
## creates the auto generated entity-classes
#
#

from shotgun_api3.shotgun import Shotgun
from pprint import pprint, pformat

from shotgun_replica import connectors, config, cleanSysName

import os
from shotgun_replica.utilities import debug
import psycopg2

FIELDDEFINITIONSMODULE = "_fieldDefinitions"

def _createClassCode( entities, entitycode, fieldDefs, entityname ):
    classCode = ""

    indent = len( entityname ) + 3

    fieldDefinitions = pformat( fieldDefs, indent = 4, width = 80 ).split( "\n" )
    newCode = "\n".join( [ ( " " * indent ) + line for line in fieldDefinitions ] )[indent:]

    fieldDefCode = "%s = %s\n\n" % ( entityname,
                                     newCode )

    fieldsstring = "    # shotgun field definitions\n    shotgun_fields = %s.%s" % ( FIELDDEFINITIONSMODULE,
                                                                                     entityname )
    classString = """class %s(_ShotgunEntity):
    \"\"\"
    internal shotgun name: %s
    original shotgun name: %s
    \"\"\"
    
    _type = "%s"

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
            "image",
            "time",
            "duration",
            "text",
            "tag_list",
            "status_list",
            "list",
            "checkbox",
            "url",
            "uuid",
            "color",
            "serializable"]:
            doc = fieldDefs[field]["description"]["value"]
            if doc != "":
                classString += "    ## %s\n    %s = None\n\n" % ( doc, field, )
            else:
                classString += "    ## undocumented field\n    %s = None\n\n" % ( field, )
        elif fieldDefs[field]["data_type"]["value"] in ["pivot_column",
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
    return ( classCode, fieldDefCode )

def _getDBFields( entityType, entityName ):

    conn = connectors.getDBConnection()
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
        debug.debug( query )
        createCur.execute( query )

    for column in [ "__retired", "id", "__local_id", "sg_link" ]:

        query = "CREATE INDEX %s ON \"%s\" (\"%s\")" % ( "%s_%s_idx" % ( entityType.lower(), column.lower() ),
                                                         entityType,
                                                         column )
        try:
            debug.debug( query )
            createCur.execute( query )
        except psycopg2.ProgrammingError:
            debug.debug( "%s of %s does not exist or index already available" % ( column, entityType ) )

    if entityName != entityType:
        query = "COMMENT ON TABLE \"%s\" IS 'Entity name: %s'" % ( entityType, entityName );
    else:
        query = "COMMENT ON TABLE \"%s\" IS ''" % ( entityType );

    createCur.execute( query )

    queryCur.close()
    createCur.close()

    return allFields


def _createDBFields( entitycode, fieldDefs, entityname ):

    conn = connectors.getDBConnection()
    createCur = conn.cursor()

    dbFields = _getDBFields( entitycode, entityname )
    if not dbFields.has_key( "__retired" ):
        query = "ALTER TABLE \"%s\" ADD COLUMN \"__retired\" BOOLEAN DEFAULT 'f'" % entitycode
        createCur.execute( query )

    for attribute in fieldDefs.keys():
        datatype = fieldDefs[attribute]["data_type"]["value"]
        postgresType = connectors.getPgType( datatype )
        if postgresType == None:
            debug.debug( "field %s.%s (%s) not handled" % ( entitycode, attribute, datatype ) )
            continue
        elif ( dbFields.has_key( attribute ) and dbFields[attribute] == postgresType ):
            pass
        elif ( dbFields.has_key( attribute ) and dbFields[attribute] != postgresType ):
            debug.debug( "changing type %s to %s" % ( dbFields[attribute], postgresType ) )
            query = "ALTER TABLE \"" + entitycode + "\" ALTER COLUMN \""
            query += str( attribute )
            query += "\" TYPE "
            query += postgresType
            debug.debug( query )
            createCur.execute( query )
        else:
            query = "ALTER TABLE \"" + entitycode + "\" ADD COLUMN \""
            query += str( attribute )
            query += "\" "
            query += postgresType
            debug.debug( query )
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

\"""@package shotgun_replica.entities
Shotgun Entities

THIS FILE IS AUTO GENERATED

DO NOT EDIT IT DIRECTLY
change create_shotgun_classes.py instead 
\"""

from shotgun_replica._entity_mgmt import _ShotgunEntity
from shotgun_replica import %s

""" % FIELDDEFINITIONSMODULE

    fieldDefModuleString = """# -*- coding: utf-8 -*-

\""" 
THIS FILE IS AUTO GENERATED

DO NOT EDIT IT DIRECTLY
change create_shotgun_classes.py instead 
\"""

"""

    classes = entities.keys()
    classes.sort()

    for entitycode in classes:

        print "processing %s\n" % entitycode
        fieldDefs = sg1.schema_field_read( entitycode )

        try:
            theclass = connectors.getClassOfType( entitycode )
            localFieldDefs = theclass.shotgun_fields
        except ImportError:
            localFieldDefs = None
        except AttributeError:
            localFieldDefs = None

        if fieldDefs != localFieldDefs:
            debug.error( "%s fielddefs differ from shotgun to local" % entitycode )

        entityname = cleanSysName( entities[entitycode]["name"]["value"] )
        if entitycode.endswith( "Connection" ):
            entityname = entitycode

        ( classCode, fieldDefCode ) = _createClassCode( entities, entitycode, fieldDefs, entityname )
        moduleString += classCode
        fieldDefModuleString += fieldDefCode

        _createDBFields( entitycode, fieldDefs, entityname )

    packageDir = os.path.dirname( __file__ )
    entityFilename = os.path.join( packageDir,
                                   'entities.py' )
    entity_file = open( entityFilename, 'w' )
    entity_file.write( moduleString )
    entity_file.close()

    fieldDefFilename = os.path.join( packageDir,
                                   '%s.py' % FIELDDEFINITIONSMODULE )
    fieldDef_file = open( fieldDefFilename, 'w' )
    fieldDef_file.write( fieldDefModuleString )
    fieldDef_file.close()

if __name__ == "__main__":
    main()
