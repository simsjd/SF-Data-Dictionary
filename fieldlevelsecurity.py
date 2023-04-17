import os
import xml.etree.ElementTree as ET
import tkinter.filedialog
import csv
import re
import sys
from datetime import datetime

ET.register_namespace('', 'http://soap.sforce.com/2006/04/metadata')
nsp = '{http://soap.sforce.com/2006/04/metadata}'

fieldToPermissionsForOutput = {'Headers':['Object API Name','Field API Name','Field Label','Type','Description','Inline Help Text']}
objectToPermissionsForOutput = {'Headers':['API Name','Label']}
userPermissionsForOutput = {'Headers':['API Name']}
visualforcePagePermissionsForOutput = {'Headers':['API Name']}
apexClassPermissionsForOutput = {'Headers':['API Name']}
objectFieldDetailMap = {} # {object: {Details: [Name], field: [label, type, description, etc]}}
permSubFolders = ['profiles','permissionsets']


def read_object_file_metadata(file_path):
    objectName = file_path.rsplit('/', 1)[-1][:-7]
    objectFieldDetailMap[objectName] = {}
    objectFieldDetailMap[objectName]['Details'] = []
    tree = ET.parse(file_path)
    root = tree.getroot()
    objectFieldDetailMap[objectName]['Details'] = [getObjectLabel(root, objectName)]
    for elem in root.findall(nsp+'fields'):
        fieldName = elem.find(nsp+'fullName').text
        objectFieldDetailMap[objectName][fieldName] = []
        add_field_information(elem, objectName, fieldName, 'label')
        add_field_information(elem, objectName, fieldName, 'type')
        add_field_information(elem, objectName, fieldName, 'description')
        add_field_information(elem, objectName, fieldName, 'inlineHelpText')


def read_object_folder_source(file_path):
    objectName = file_path.rsplit('/', 1)[-1]
    objectFieldDetailMap[objectName] = {}
    tree = ET.parse(file_path+'/'+objectName+'.object-meta.xml')
    root = tree.getroot()
    objectFieldDetailMap[objectName]['Details'] = [getObjectLabel(root, objectName)]
    try:
        for field_name in os.listdir(file_path+'/fields'):
            tree = ET.parse(file_path+'/fields/'+field_name)
            root = tree.getroot()
            fieldName = root.find(nsp+'fullName').text
            objectFieldDetailMap[objectName][fieldName] = []
            add_field_information(root, objectName, fieldName, 'label')
            add_field_information(root, objectName, fieldName, 'type')
            add_field_information(root, objectName, fieldName, 'description')
            add_field_information(root, objectName, fieldName, 'inlineHelpText')
    except FileNotFoundError as e:
        print('No fields found for '+objectName+'.')


def getObjectLabel(root, objectName):
    if root is not None and root.find(nsp+'label') is not None:
        objectLabel = root.find(nsp+'label').text
        return objectLabel
    elif objectName.endswith('__c') or objectName.endswith('__mdt'):
        return objectName.replace('__c','').replace('__mdt','').replace('_',' ')
    else:
        return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', objectName)


def add_field_information(elem, objectName, fieldName, elemText):
    if elem.find(nsp+elemText) is not None:
        objectFieldDetailMap[objectName][fieldName].append(elem.find(nsp+elemText).text)
    else:
        objectFieldDetailMap[objectName][fieldName].append('-')


def read_permission_file(file_path, file_name):
    tree = ET.parse(file_path)
    root = tree.getroot()

    fieldKeys = set(fieldToPermissionsForOutput.keys())
    fieldKeys.discard('Headers')
    fieldToPermissionsForOutput['Headers'].append(file_name)
    for elem in root.findall(nsp+'fieldPermissions'):
        elem_text = elem.find(nsp+'field').text
        fieldKeys.discard(elem_text)
        if elem_text not in fieldToPermissionsForOutput:
            objFieldList = elem_text.rsplit('.')
            try:
                fieldData = objectFieldDetailMap[objFieldList[0]][objFieldList[1]]
                fieldToPermissionsForOutput[elem_text] = [fieldData[0],fieldData[1],fieldData[2],fieldData[3]]
            except KeyError as e:
                fieldToPermissionsForOutput[elem_text] = ['-','-','-','-']
            counter = 6
            while counter < len(fieldToPermissionsForOutput['Headers'])-1:
                fieldToPermissionsForOutput[elem_text].append('-')
                counter += 1
        editTag = elem.find(nsp+'editable')
        readTag = elem.find(nsp+'readable')
        if editTag is not None and editTag.text == 'true':
            fieldToPermissionsForOutput[elem_text].append('Edit')
        elif readTag is not None and readTag.text == 'true':
            fieldToPermissionsForOutput[elem_text].append('Read')
        else:
            fieldToPermissionsForOutput[elem_text].append('-')
    for elem in fieldKeys:
        fieldToPermissionsForOutput[elem].append('-')

    objectKeys = set(objectToPermissionsForOutput.keys())
    objectKeys.discard('Headers')
    objectToPermissionsForOutput['Headers'].append(file_name)
    for elem in root.findall(nsp+'objectPermissions'):
        elem_text = elem.find(nsp+'object').text
        objectKeys.discard(elem_text)
        if elem_text not in objectToPermissionsForOutput:
            try:
                objectLabel = objectFieldDetailMap[elem_text]['Details'][0]
                objectToPermissionsForOutput[elem_text] = [objectLabel]
            except KeyError as e:
                objectToPermissionsForOutput[elem_text] = [getObjectLabel(None, elem_text)]
            counter = 2
            while counter < len(objectToPermissionsForOutput['Headers'])-1:
                objectToPermissionsForOutput[elem_text].append('-')
                counter += 1

        if elem.find(nsp+'modifyAllRecords').text == 'true':
            objectToPermissionsForOutput[elem_text].append('ModifyAll')
        else:
            access_string = ''
            if elem.find(nsp+'allowCreate').text == 'true':
                access_string = access_string +'C '
            if elem.find(nsp+'allowRead').text == 'true':
                access_string = access_string +'R '
            if elem.find(nsp+'allowEdit').text == 'true':
                access_string = access_string +'U '
            if elem.find(nsp+'allowDelete').text == 'true':
                access_string = access_string +'D '
            if elem.find(nsp+'viewAllRecords').text == 'true':
                access_string = access_string +'VA'
            if len(access_string) > 0:
                objectToPermissionsForOutput[elem_text].append(access_string.strip())
            else:
                objectToPermissionsForOutput[elem_text].append('-')
    for elem in objectKeys:
        objectToPermissionsForOutput[elem].append('-')

    retrieve_permissions(root, userPermissionsForOutput, 'userPermissions', 'name')
    retrieve_permissions(root, visualforcePagePermissionsForOutput, 'pageAccesses', 'apexPage')
    retrieve_permissions(root, apexClassPermissionsForOutput, 'classAccesses', 'apexClass')


def retrieve_permissions(treeRoot, permissionMap, nodeType, nameNode):
    permKeys = set(permissionMap.keys())
    permKeys.discard('Headers')
    permissionMap['Headers'].append(file_name)
    for elem in treeRoot.findall(nsp+nodeType):
        elem_text = elem.find(nsp+nameNode).text
        permKeys.discard(elem_text)
        if elem_text not in permissionMap:
            permissionMap[elem_text] = []
            counter = 1
            while counter < len(permissionMap['Headers'])-1:
                permissionMap[elem_text].append('-')
                counter += 1

        if elem.find(nsp+'enabled').text == 'true':
            permissionMap[elem_text].append('True')
        else:
            permissionMap[elem_text].append('-')
    for elem in permKeys:
        permissionMap[elem].append('-')


def write_output_files():
    write_output_file('FieldPermissions', fieldToPermissionsForOutput)
    write_output_file('ObjectPermissions', objectToPermissionsForOutput)
    write_output_file('UserPermissions', userPermissionsForOutput)
    write_output_file('ClassPermissions', apexClassPermissionsForOutput)
    write_output_file('VisualforcePermissions', visualforcePagePermissionsForOutput)


def write_output_file(name, dataInput):
    #TODO Possible rewrite the permission maps so I can use csv.DictWriter. Need to see if that
    # would be faster.
    dt_string = datetime.now().strftime('%Y-%m-%dT%H%M%S')
    fileName = ''
    if len(sys.argv) > 1:
        fileName = dt_string + '_' + name + '_' + sys.argv[1] + '.csv'
    else:
        fileName = dt_string + '_' + name + '.csv'
    with open(fileName, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(dataInput.pop('Headers'))
        for key, value in dataInput.items():
            row = []
            if name == 'FieldPermissions':
                row.extend(list(key.split('.')))
            else:
                row.append(key)
            row.extend(value)
            csvwriter.writerow(row)


def set_base_folder():
    folder_path = 'SELECT'
    while folder_path != '' and not folder_path.lower().endswith('src') and not folder_path.lower().endswith('force-app'):
        print('Select the "src" folder for metadata format or the "force-app" folder for source (DX) format.')
        folder_path = tkinter.filedialog.askdirectory(title = 'Select the "src" or "force-app" folder')
    return folder_path


# Begin execution
tkinter.Tk().withdraw()
folder_path = set_base_folder()
specified_folder_path = folder_path

if folder_path.endswith("src"):
    for file_name in os.listdir(folder_path+'/objects'):
        read_object_file_metadata(folder_path+'/objects/'+file_name)
        specified_folder_path = folder_path+'/'

elif folder_path.endswith("force-app"):
    for object_folder in os.listdir(folder_path+'/main/default/objects'):
        read_object_folder_source(folder_path+'/main/default/objects/'+object_folder)
    specified_folder_path = folder_path+'/main/default/'
 
else:
    print('Select either the "src" folder if the files are in metadata format or the "force-app" folder if the files are in the source (DX) format.')
    exit()

for folder in permSubFolders:
    for file_name in os.listdir(specified_folder_path+folder):
        read_permission_file(specified_folder_path+folder+'/'+file_name, file_name)

write_output_files()