import os
import xml.etree.ElementTree as ET
import tkinter.filedialog
import csv
#new
import pandas as pd
#import xlwt
#from xlwt.Workbook import *
from pandas import ExcelWriter
import pandas.io.formats.excel

#import xlsxwriter
#new end

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
        if elem.find(nsp+'type') is not None:
            objectFieldDetailMap[objectName][fieldName].append(elem.find(nsp+'type').text)
        else:
            objectFieldDetailMap[objectName][fieldName].append('-')
        if elem.find(nsp+'description') is not None:
            objectFieldDetailMap[objectName][fieldName].append(elem.find(nsp+'description').text)
        else:
            objectFieldDetailMap[objectName][fieldName].append('-')


def read_permission_file(file_path, file_name):
    #TODO eventually use the <label> tag value instead of file file name
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
    ftpData = pd.DataFrame.from_dict(data=fieldToPermissionsForOutput, orient="index")
    otpData = pd.DataFrame.from_dict(data=objectToPermissionsForOutput, orient="index")
    upData = pd.DataFrame.from_dict(data=userPermissionsForOutput, orient="index")
    writer = pd.ExcelWriter('DataDictionaryResults.xlsx')
    pandas.io.formats.excel.header_style = None
    ftpData.to_excel(writer, index=True, header=False, sheet_name='Field Permissions')
    otpData.to_excel(writer, index=False, header=False, sheet_name='Object Permissions')
    upData.to_excel(writer, index=True, header=False, sheet_name='User Permissions')
    workbook = writer.book
    header_format = workbook.add_format({
        'bold': True})
    ftpWorksheet = writer.sheets['Field Permissions']
    ftpWorksheet.set_column('A:A', None, header_format)
    ftpWorksheet.set_row(0, None, header_format)
    ftpWorksheet.freeze_panes(1, 1)
    otpWorksheet = writer.sheets['Object Permissions']
    otpWorksheet.set_column('A:A', None, header_format)
    otpWorksheet.set_row(0, None, header_format)
    otpWorksheet.freeze_panes(1, 1)
    upWorksheet = writer.sheets['User Permissions']
    upWorksheet.set_column('A:A', None, header_format)
    upWorksheet.set_row(0, None, header_format)
    upWorksheet.freeze_panes(1, 1)
    writer.save()
"""
This is the old version of the output that would write to csv files
    with open('fieldpermissionsoutput.csv', mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator = '\n')
        for key, value in fieldToPermissionsForOutput.items():
            row = [key]
            row.extend(value)
            output_writer.writerow(row)

    with open('objectpermissionsoutput.csv', mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator = '\n')
        for key, value in objectToPermissionsForOutput.items():
            row = [key]
            row.extend(value)
            output_writer.writerow(row)

    with open('userpermissionsoutput.csv', mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator = '\n')
        for key, value in userPermissionsForOutput.items():
            row = [key]
            row.extend(value)
            output_writer.writerow(row)
"""

# Begin execution
tkinter.Tk().withdraw()
src_folder_path = tkinter.filedialog.askdirectory(title = 'Select the src folder')

for file_name in os.listdir(src_folder_path+'/objects'):
    read_object_file(src_folder_path+'/objects/'+file_name)

for folder in permSubFolders:
    for file_name in os.listdir(src_folder_path+folder):
        read_permission_file(src_folder_path+folder+'/'+file_name, file_name)

write_output_permission_file()
