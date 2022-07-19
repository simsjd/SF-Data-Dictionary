import os
import xml.etree.ElementTree as ET
import tkinter.filedialog
import csv
from datetime import datetime

ET.register_namespace('', 'http://soap.sforce.com/2006/04/metadata')
nsp = '{http://soap.sforce.com/2006/04/metadata}'

fieldToPermissionsForOutput = {'Headers':['Label','Type','Description']}
objectToPermissionsForOutput = {'Headers':[]}
userPermissionsForOutput = {'Headers':[]}
objectFieldDetailMap = {} # {object: {field: [label, type, description]}}
permSubFolders = ['/profiles','/permissionsets']


def read_object_file_metadata(file_path):
    objectName = file_path.rsplit('/', 1)[-1][:-7]F
    objectFieldDetailMap[objectName] = {}
    tree = ET.parse(file_path)
    root = tree.getroot()
    for elem in root.findall(nsp+'fields'):
        fieldName = elem.find(nsp+'fullName').text
        if elem.find(nsp+'label') is not None:
            objectFieldDetailMap[objectName][fieldName] = [elem.find(nsp+'label').text]
        else:
            objectFieldDetailMap[objectName][fieldName] = ['-']
        add_additional_field_information(elem, objectName, fieldName, 'type')
        add_additional_field_information(elem, objectName, fieldName, 'description')


def read_object_folder_source(file_path):
    objectName = file_path.rsplit('/', 1)[-1]
    objectFieldDetailMap[objectName] = {}
    try:
        for field_name in os.listdir(file_path+'/fields'):
            tree = ET.parse(file_path+'/fields/'+field_name)
            root = tree.getroot()
            fieldName = root.find(nsp+'fullName').text
            objectFieldDetailMap[objectName][fieldName] = []
            add_additional_field_information(root, objectName, fieldName, 'label')
            add_additional_field_information(root, objectName, fieldName, 'type')
            add_additional_field_information(root, objectName, fieldName, 'description')
    except FileNotFoundError as e:
        print(e)
        print('No fields found for '+objectName+'.')
        del objectFieldDetailMap[objectName]


def add_additional_field_information(elem, objectName, fieldName, elemText):
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
                fieldToPermissionsForOutput[elem_text] = [fieldData[0],fieldData[1],fieldData[2]]
            except KeyError as e:
                print(e)
                print('Skipped over the key since data was not found.')
                fieldToPermissionsForOutput[elem_text] = ['-','-','-']
            if (len(fieldToPermissionsForOutput['Headers']) > 4):
                counter = 4
                while counter < len(fieldToPermissionsForOutput['Headers']):
                    fieldToPermissionsForOutput[elem_text].append('-')
                    counter += 1

        if elem.find(nsp+'editable').text == 'true':
            fieldToPermissionsForOutput[elem_text].append('Edit')
        elif elem.find(nsp+'readable').text == 'true':
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
            objectToPermissionsForOutput[elem_text] = []
            if (len(objectToPermissionsForOutput['Headers']) > 1):
                counter = 1
                while counter < len(objectToPermissionsForOutput['Headers']):
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

    userPermKeys = set(userPermissionsForOutput.keys())
    userPermKeys.discard('Headers')
    userPermissionsForOutput['Headers'].append(file_name)
    for elem in root.findall(nsp+'userPermissions'):
        elem_text = elem.find(nsp+'name').text
        userPermKeys.discard(elem_text)
        if elem_text not in userPermissionsForOutput:
            userPermissionsForOutput[elem_text] = []
            if (len(userPermissionsForOutput['Headers']) > 1):
                counter = 1
                while counter < len(userPermissionsForOutput['Headers']):
                    userPermissionsForOutput[elem_text].append('-')
                    counter += 1

        if elem.find(nsp+'enabled').text == 'true':
            userPermissionsForOutput[elem_text].append('True')
        else:
            userPermissionsForOutput[elem_text].append('-')
    for elem in userPermKeys:
        userPermissionsForOutput[elem].append('-')


def write_output_files():
    write_output_file('FieldPermissions', fieldToPermissionsForOutput)
    write_output_file('ObjectPermissions', objectToPermissionsForOutput)
    write_output_file('UserPermissions', userPermissionsForOutput)


def write_output_file(name, dataInput):
    #TODO Possible rewrite the permission maps so I can use csv.DictWriter. Need to see if that
    # would be faster.
    dt_string = datetime.now.strftime('%d%m%Y-%H%M%S')
    fileName = dt_string + '_' + name + '.csv'
    with open(fileName, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(['Spam'] * 5 + ['Baked Beans'])
        csvwriter.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])


    df = pd.DataFrame.from_dict(data=dataInput, orient='index')
    for r in dataframe_to_rows(df, index=True, header=False):
        worksheet.append(r)
    worksheet.delete_rows(1,1)
    worksheet['A1'].value = 'API Name'


# Begin execution
tkinter.Tk().withdraw()
folder_path = tkinter.filedialog.askdirectory(title = 'Select the "src" folder for metadata format or the "force-app" folder for source format')

if folder_path.endswith("src"):
    for file_name in os.listdir(folder_path+'/objects'):
        read_object_file_metadata(folder_path+'/objects/'+file_name)

    for folder in permSubFolders:
        for file_name in os.listdir(folder_path+folder):
            read_permission_file(folder_path+folder+'/'+file_name, file_name)

    write_output_files()

elif folder_path.endswith("force-app"):
    for object_folder in os.listdir(folder_path+'/main/default/objects'):
        read_object_folder_source(folder_path+'/main/default/objects/'+object_folder)
 
    for folder in permSubFolders:
        for file_name in os.listdir(folder_path+'/main/default/'+folder):
            read_permission_file(folder_path+'/main/default/'+folder+'/'+file_name, file_name)

    write_output_files()

else:
    print('Please select either the "src" folder if the files are in metadata format or the "force-app" folder if the files are in the source (DX) format.')

#TODO if success close the window, if error leave open
