import os
import xml.etree.ElementTree as ET
import tkinter.filedialog
import csv
import pandas as pd
#from pandas import ExcelWriter
#import xlsxwriter
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

ET.register_namespace('', 'http://soap.sforce.com/2006/04/metadata')
nsp = '{http://soap.sforce.com/2006/04/metadata}'

fieldToPermissionsForOutput = {'Headers':['Label','Type','Description']}
objectToPermissionsForOutput = {'Headers':[]}
userPermissionsForOutput = {'Headers':[]}
objectFieldDetailMap = {} # {object: {field: [label, type, description]}}
permSubFolders = ['/profiles','/permissionsets',]


def read_object_file(file_path):
    objectName = file_path.rsplit('/', 1)[-1][:-7]
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


def write_output_permission_file():
    wb = openpyxl.Workbook()
    wsf = wb.active
    wsf.title = 'Field Permissions'
    for r in dataframe_to_rows(pd.DataFrame.from_dict(data=fieldToPermissionsForOutput, orient='index'), index=True, header=False):
        wsf.append(r)
    wsf.delete_rows(1,1)
    wso = wb.create_sheet("Object Permissions")
    for r in dataframe_to_rows(pd.DataFrame.from_dict(data=objectToPermissionsForOutput, orient='index'), index=True, header=False):
        wso.append(r)
    wso.delete_rows(1,1)
    wsu = wb.create_sheet("User Permissions")
    for r in dataframe_to_rows(pd.DataFrame.from_dict(data=userPermissionsForOutput, orient='index'), index=True, header=False):
        wsu.append(r)
    wsu.delete_rows(1,1)
    #freeze column a and row 1 and make bold
    wb.save("DataDictionaryResults2.xlsx")
    """writer = pd.ExcelWriter('DataDictionaryResults.xlsx')
    add_sheet_to_writer(writer, fieldToPermissionsForOutput, 'Field Permissions')
    add_sheet_to_writer(writer, objectToPermissionsForOutput, 'Object Permissions')
    add_sheet_to_writer(writer, userPermissionsForOutput, 'User Permissions')
    workbook = writer.book
    header_format = workbook.add_format({
        'bold': True})
    format_worksheet(writer, 'Field Permissions', header_format)
    format_worksheet(writer, 'Object Permissions', header_format)
    format_worksheet(writer, 'User Permissions', header_format)
    writer.save()


def add_sheet_to_writer(writer, datainput, sheet_name):
    dfData = pd.DataFrame.from_dict(data=datainput, orient='index')
    dfData.to_excel(writer, index=True, header=False, sheet_name=sheet_name)


def format_worksheet(writer, worksheet_name, format):
    worksheet = writer.sheets[worksheet_name]
    # reformat here column
    worksheet.set_column('A:A', None, format)
    worksheet.set_row(0, None, format)
    worksheet.freeze_panes(1, 1)"""


# Begin execution
tkinter.Tk().withdraw()
src_folder_path = tkinter.filedialog.askdirectory(title = 'Select the src folder')

for file_name in os.listdir(src_folder_path+'/objects'):
    read_object_file(src_folder_path+'/objects/'+file_name)

for folder in permSubFolders:
    for file_name in os.listdir(src_folder_path+folder):
        read_permission_file(src_folder_path+folder+'/'+file_name, file_name)

write_output_permission_file()
