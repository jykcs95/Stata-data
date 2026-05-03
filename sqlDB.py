import pandas as pd
import gamry_parser as parser

import sqlite3
import glob
from pathlib import Path

#Converts dta files to csv files
def dtaParser(file):
    #store the name of the file for later use
    file_name = file.rsplit(".",1)[0]

    #Call the gamry parser to read the dta files and get all the curve points
    gp = parser.GamryParser()
    gp.load(file)
    curve_count = gp.get_curve_count()

    #store all headers
    header = gp.get_header()

    #Get the correct query for each title where first index contains query and second index contains the type
    title = header["TITLE"]
    queryType = titleQuery(title)
    
    #Send all the data in to reading functino to find the corresponding output using the query
    for i in range(curve_count):
        curve_count = gp.get_curve_data(i)
        path = reading(curve_count, queryType[0], file_name, queryType[1])
    
    createHeader(path, header, file_name)

#Finding the right query and return the tag as well  
def titleQuery(title):
    query = ""
    match title.lower():
        case "chronoamperometry scan":
            query = "SELECT T, Vf, Im FROM 'my_table'"
            tag = "CA"
        case "cyclic voltammetry":
            query = "SELECT T, VF, Im FROM 'my_table'"
            tag = "CV"
    return [query,tag]

#Creating header using the "ignore the grid" way
def createHeader(csvFile, header, fileName):
    #open the csvfile
    with open(csvFile,'r') as f:
        existing_content= f.read()

    #Get the right header for corresponding title
    match header["TITLE"].lower():
        case "chronoamperometry scan":
            extra_data= ["File Name", fileName]
        case "cyclic voltammetry":
            extra_data= ["File Name", fileName,"SCAN RATE", header["SCANRATE"]]    
    new_line = ",".join(map(str,extra_data)) + "\n"
    
    #rewrite the header with the existing content to the csv file
    with open(csvFile,'w') as f:
        f.write(new_line)
        f.write(existing_content)

#Using SQL queries to read and alter the csv file to create a new file that contains a table with all the requested information
def reading(df, sqlQuery, outFile, outType):
    #connect to sqlite3 in order to use sql query
    conn = sqlite3.connect(":memory:")
    
    df.to_sql("my_table", conn, index=False)

    #SQL query to pull the necessary data from the csv  file
    query = sqlQuery

    result_df =  pd.read_sql_query(query, conn)

    #storing the output into a new folder in the directory
    file_path = Path(f"results_{outType}/output_{outFile}.csv")
    #create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    #add on to the file instead of rewriting it
    result_df.to_csv(file_path, mode="a",index = False)

    conn.close()

    return file_path

#It's going to go through the header file and search for its title and date
def searchHeader(headerFile):
    df = pd.read_csv(headerFile)
    title = df.at[0,"TITLE"]
    date = df.at[0,"DATE"]
    return {"title":title, "date":date}

def getDTA():
    return glob.glob("*.dta")


if __name__ == "__main__":

    dta_files = getDTA()
    for file in dta_files:
        dtaParser(file)
